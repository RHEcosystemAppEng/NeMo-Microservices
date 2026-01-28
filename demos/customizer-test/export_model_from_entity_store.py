#!/usr/bin/env python3
"""
Get Customized Model Information

This script retrieves customized model information from either:
1. Entity Store (if model is registered there)
2. Customizer job API (fallback - gets model location from job details)

🤖 AUTO MODE (Lazy User's Dream):
    python export_model_from_entity_store.py
    # Automatically finds and exports the last completed customization job!

Explicit Usage:
    python export_model_from_entity_store.py --model-name "anemo-rhoai/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"
    
    Or with job ID:
    python export_model_from_entity_store.py --job-id "job-12345"
    
    Or set environment variables:
    export CUSTOMIZED_MODEL_NAME="anemo-rhoai/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"
    python export_model_from_entity_store.py
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

# Load environment variables from env.donotcommit if it exists
try:
    from dotenv import load_dotenv
    env_donotcommit_path = Path(__file__).parent / "env.donotcommit"
    if env_donotcommit_path.exists():
        load_dotenv(env_donotcommit_path, override=False)
        print(f"✅ Loaded env.donotcommit from: {env_donotcommit_path}")
except ImportError:
    pass

# Configuration
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Determine if running locally (with port-forward) or in cluster
# Entity Store URL
ENTITY_STORE_URL = os.getenv("ENTITY_STORE_URL")
if not ENTITY_STORE_URL:
    ENTITY_STORE_URL = os.getenv("ENTITY_STORE_URL_LOCAL", "http://localhost:8002")
    CLUSTER_ENTITY_STORE_URL = f"http://nemoentitystore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
else:
    CLUSTER_ENTITY_STORE_URL = ENTITY_STORE_URL

# Customizer URL
CUSTOMIZER_URL = os.getenv("CUSTOMIZER_URL")
if not CUSTOMIZER_URL:
    CUSTOMIZER_URL = os.getenv("CUSTOMIZER_URL_LOCAL", "http://localhost:8003")
    CLUSTER_CUSTOMIZER_URL = f"http://nemocustomizer-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
else:
    CLUSTER_CUSTOMIZER_URL = CUSTOMIZER_URL

# DataStore URL (for checking if models exist)
DATASTORE_URL = os.getenv("DATASTORE_URL")
if not DATASTORE_URL:
    DATASTORE_URL = os.getenv("DATASTORE_URL_LOCAL", "http://localhost:8001")


def parse_model_name(model_name):
    """Parse model name into namespace, name, and version."""
    if "@" in model_name:
        namespace_part, version_part = model_name.split("@", 1)
        if "/" in namespace_part:
            model_namespace, model_name_only = namespace_part.split("/", 1)
        else:
            model_namespace = NMS_NAMESPACE
            model_name_only = namespace_part
        model_version = version_part
    else:
        if "/" in model_name:
            model_namespace, model_name_only = model_name.split("/", 1)
        else:
            model_namespace = NMS_NAMESPACE
            model_name_only = model_name
        model_version = "1.0"
    
    return model_namespace, model_name_only, model_version


def get_model_info_from_entity_store(model_name, entity_store_url=None):
    """Get model information from Entity Store."""
    if entity_store_url is None:
        entity_store_url = ENTITY_STORE_URL
    
    model_namespace, model_name_only, model_version = parse_model_name(model_name)
    model_path = f"{model_namespace}/{model_name_only}"
    
    try:
        response = requests.get(
            f"{entity_store_url}/v1/models/{model_path}",
            timeout=30
        )
        
        if response.status_code == 200:
            model_info = response.json()
            files_url = model_info.get('artifact', {}).get('files_url')
            
            print(f"✅ Found model in Entity Store!")
            print(f"   Model ID: {model_info.get('id', 'N/A')}")
            print(f"   Files URL: {files_url}")
            
            return {
                "success": True,
                "source": "entity_store",
                "model_name": model_name,
                "model_info": model_info,
                "files_url": files_url,
                "model_namespace": model_namespace,
                "model_name_only": model_name_only,
                "model_version": model_version
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Model not found in Entity Store",
                "model_name": model_name
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "model_name": model_name
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "model_name": model_name
        }


def get_model_info_from_customizer_job(job_id, customizer_url=None, allow_failed=False):
    """Get model information from Customizer job details."""
    if customizer_url is None:
        customizer_url = CUSTOMIZER_URL
    
    try:
        response = requests.get(
            f"{customizer_url}/v1/customization/jobs/{job_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            job_details = response.json()
            output_model = job_details.get('output_model')
            status = job_details.get('status')
            
            if status != 'completed' and not allow_failed:
                return {
                    "success": False,
                    "error": f"Job status is '{status}', not 'completed'",
                    "job_id": job_id
                }
            
            if status != 'completed' and allow_failed:
                print(f"   ⚠️  Job status is '{status}' (not 'completed'), but proceeding anyway")
            
            print(f"✅ Found job in Customizer!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {status}")
            print(f"   Output Model: {output_model}")
            
            # Try to construct files_url from output_model
            # Customizer stores models in DataStore, typically at hf://datasets/{namespace}/{model_name}@revision
            files_url = None
            if output_model:
                # Parse model name to construct DataStore path (include revision for EntityHandler exports)
                if "@" in output_model:
                    namespace_part, revision_part = output_model.split("@", 1)
                else:
                    namespace_part = output_model
                    revision_part = None
                
                if "/" in namespace_part:
                    model_namespace, model_name_only = namespace_part.split("/", 1)
                    files_url = f"hf://datasets/{model_namespace}/{model_name_only}"
                else:
                    files_url = f"hf://datasets/{NMS_NAMESPACE}/{namespace_part}"
                if revision_part:
                    files_url = f"{files_url}@{revision_part}"
            
            return {
                "success": True,
                "source": "customizer_job",
                "job_id": job_id,
                "job_details": job_details,
                "output_model": output_model,
                "files_url": files_url,
                "model_name": output_model
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "error": "Job not found",
                "job_id": job_id
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "job_id": job_id
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "job_id": job_id
        }


def get_last_completed_job(customizer_url=None):
    """Get the most recent completed customization job from Customizer."""
    if customizer_url is None:
        customizer_url = CUSTOMIZER_URL
    
    try:
        print(f"🔍 Querying Customizer for all jobs...")
        print(f"   Customizer URL: {customizer_url}")
        
        # Get all jobs - handle pagination
        all_jobs = []
        page = 1
        limit = 100  # Request more jobs per page
        
        while True:
            jobs_response = requests.get(
                f"{customizer_url}/v1/customization/jobs",
                params={"page": page, "limit": limit},
                timeout=30
            )
            
            if jobs_response.status_code != 200:
                if page == 1:
                    # If first page fails, return error
                    return {
                        "success": False,
                        "error": f"HTTP {jobs_response.status_code}: {jobs_response.text[:200]}"
                    }
                break
            
            jobs_data = jobs_response.json()
            jobs = jobs_data.get('data', [])
            
            if not jobs:
                break
            
            all_jobs.extend(jobs)
            
            # Check pagination info
            pagination = jobs_data.get('pagination', {})
            total_pages = pagination.get('total_pages', 1)
            current_page = pagination.get('page', page)
            
            # If we've fetched all pages, break
            if current_page >= total_pages:
                break
            
            page += 1
            # Safety limit
            if page > 20:
                print(f"   ⚠️  Reached pagination limit (20 pages), stopping")
                break
        
        jobs = all_jobs
        
        if not jobs:
            return {
                "success": False,
                "error": "No jobs found in Customizer"
            }
        
        print(f"   Found {len(jobs)} total job(s) (fetched from {page} page(s))")
        
        # Filter for completed jobs (primary method)
        completed_jobs = [job for job in jobs if job.get('status') == 'completed']
        
        # If no completed jobs, try alternative: check if output_model exists in Entity Store
        if not completed_jobs:
            print(f"   ⚠️  No jobs with status='completed' found")
            print(f"   Available statuses: {set(job.get('status') for job in jobs)}")
            print(f"   🔍 Checking if any jobs have models in Entity Store (alternative success indicator)...")
            
            # Check each job to see if its output_model exists in Entity Store
            jobs_with_models = []
            for job in jobs:
                    output_model = job.get('output_model')
                    if not output_model:
                        continue
                    
                    # Parse model name for Entity Store lookup
                    if "@" in output_model:
                        namespace_part = output_model.split("@")[0]
                    else:
                        namespace_part = output_model
                    
                    if "/" in namespace_part:
                        model_namespace, model_name_only = namespace_part.split("/", 1)
                    else:
                        model_namespace = NMS_NAMESPACE
                        model_name_only = namespace_part
                    
                    model_path = f"{model_namespace}/{model_name_only}"
                    
                    # Check Entity Store first
                    model_exists = False
                    try:
                        es_url = ENTITY_STORE_URL
                        es_response = requests.get(
                            f"{es_url}/v1/models/{model_path}",
                            timeout=5
                        )
                        if es_response.status_code == 200:
                            model_exists = True
                            print(f"      ✅ Job {job.get('id')[:20]}... has model in Entity Store")
                    except:
                        pass
                    
                    # Also check DataStore (models might be there even if not in Entity Store)
                    if not model_exists:
                        try:
                            # Try to check DataStore via HuggingFace API
                            # Model path in DataStore would be: namespace/model_name
                            ds_url = DATASTORE_URL
                            # Use HuggingFace API to check if repo exists
                            hf_response = requests.get(
                                f"{ds_url}/v1/hf/models/{model_path}",
                                timeout=5
                            )
                            if hf_response.status_code == 200:
                                model_exists = True
                                print(f"      ✅ Job {job.get('id')[:20]}... has model in DataStore")
                        except:
                            pass
                    
                    if model_exists:
                        jobs_with_models.append(job)
            
            if jobs_with_models:
                print(f"   ✅ Found {len(jobs_with_models)} job(s) with models in Entity Store")
                completed_jobs = jobs_with_models
            else:
                print(f"   ❌ No jobs found with models in Entity Store either")
                print(f"   💡 Falling back to most recent jobs (regardless of status)")
                print(f"      Note: If jobs succeeded but status wasn't updated, this will still work")
                
                # Fallback: Use most recent jobs (user said last 3-4 succeeded)
                # Sort all jobs by creation time
                def get_sort_key(job):
                    created_at = job.get('created_at') or job.get('createdAt') or job.get('start_time')
                    if created_at:
                        try:
                            from datetime import datetime
                            if isinstance(created_at, str):
                                return datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                            return float(created_at)
                        except:
                            pass
                    return job.get('id', '')
                
                sorted_all_jobs = sorted(jobs, key=get_sort_key, reverse=True)
                # Take last 4 most recent jobs
                completed_jobs = sorted_all_jobs[:4]
                print(f"   📋 Using last {len(completed_jobs)} most recent job(s) as fallback")
        
        print(f"   Found {len(completed_jobs)} successful job(s) (status='completed' or model exists in Entity Store)")
        
        # Sort by creation time (most recent first) or by ID
        # Try to sort by created_at if available, otherwise by id
        def get_sort_key(job):
            # Try created_at timestamp, or use id as fallback
            created_at = job.get('created_at') or job.get('createdAt') or job.get('start_time')
            if created_at:
                try:
                    # Try to parse as ISO timestamp
                    from datetime import datetime
                    if isinstance(created_at, str):
                        return datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                    return float(created_at)
                except:
                    pass
            # Fallback: use id (assuming newer jobs have higher IDs)
            return job.get('id', '')
        
        completed_jobs.sort(key=get_sort_key, reverse=True)
        
        # Get the most recent completed job
        latest_job = completed_jobs[0]
        job_id = latest_job.get('id')
        output_model = latest_job.get('output_model')
        status = latest_job.get('status')
        
        print(f"   ✅ Selected most recent completed job:")
        print(f"      Job ID: {job_id}")
        print(f"      Output Model: {output_model}")
        print(f"      Status: {status}")
        
        return {
            "success": True,
            "job_id": job_id,
            "output_model": output_model,
            "job_details": latest_job
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_model_info(model_name=None, job_id=None, entity_store_url=None, customizer_url=None, auto_mode=False):
    """Get model information from Entity Store or Customizer job."""
    result = None
    
    # Auto mode: find last completed job if no arguments provided
    if auto_mode and not model_name and not job_id:
        print(f"\n🤖 AUTO MODE: Finding last completed customization job...")
        auto_result = get_last_completed_job(customizer_url)
        
        if auto_result.get("success"):
            job_id = auto_result.get("job_id")
            model_name = auto_result.get("output_model")
            print(f"\n✅ Auto-detected:")
            print(f"   Job ID: {job_id}")
            print(f"   Model: {model_name}")
        else:
            print(f"\n❌ Auto mode failed: {auto_result.get('error')}")
            return {
                "success": False,
                "error": f"Auto mode failed: {auto_result.get('error')}",
                "suggestion": "Try providing --model-name or --job-id explicitly"
            }
    
    # Try Entity Store first if we have model name
    if model_name:
        print(f"\n🔍 Step 1: Looking up model in Entity Store...")
        print(f"   Model: {model_name}")
        print(f"   Entity Store URL: {entity_store_url or ENTITY_STORE_URL}")
        
        result = get_model_info_from_entity_store(model_name, entity_store_url)
        
        if result.get("success"):
            return result
        else:
            print(f"   ⚠️  Model not found in Entity Store: {result.get('error')}")
    
    # Fallback: Try Customizer job API if we have job_id
    if job_id:
        print(f"\n🔍 Step 2: Looking up job in Customizer...")
        print(f"   Job ID: {job_id}")
        print(f"   Customizer URL: {customizer_url or CUSTOMIZER_URL}")
        
        # Allow failed jobs if we're in auto mode (user said jobs succeeded)
        allow_failed = auto_mode
        result = get_model_info_from_customizer_job(job_id, customizer_url, allow_failed=allow_failed)
        
        if result.get("success"):
            return result
        else:
            print(f"   ⚠️  Job not found or not completed: {result.get('error')}")
    
    # If we have model_name but no job_id, try to find job by listing and searching
    if model_name and not job_id:
        print(f"\n🔍 Step 2: Searching for job by model name in Customizer...")
        try:
            jobs_response = requests.get(
                f"{customizer_url or CUSTOMIZER_URL}/v1/customization/jobs",
                timeout=30
            )
            if jobs_response.status_code == 200:
                jobs_data = jobs_response.json()
                jobs = jobs_data.get('data', [])
                
                # Find job with matching output_model
                for job in jobs:
                    if job.get('output_model') == model_name and job.get('status') == 'completed':
                        job_id = job.get('id')
                        print(f"   ✅ Found completed job: {job_id}")
                        result = get_model_info_from_customizer_job(job_id, customizer_url)
                        if result.get("success"):
                            return result
        except Exception as e:
            print(f"   ⚠️  Could not search jobs: {e}")
    
    # If all methods failed
    if not result:
        result = {
            "success": False,
            "error": "Could not find model in Entity Store or Customizer",
            "model_name": model_name,
            "job_id": job_id
        }
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Get customized model information from Entity Store or Customizer. "
                    "🤖 AUTO MODE: Run without arguments to automatically find and export the last completed job!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto mode - finds last completed job automatically (lazy user's dream!)
  python export_model_from_entity_store.py

  # Explicit model name
  python export_model_from_entity_store.py --model-name "anemo-rhoai/llama-3.2-1b-instruct-custom-123@1.0"

  # Explicit job ID
  python export_model_from_entity_store.py --job-id "job-12345"
        """
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=os.getenv("CUSTOMIZED_MODEL_NAME", ""),
        help="Customized model name (e.g., anemo-rhoai/llama-3.2-1b-instruct-custom-1234567890-12345@1.0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="model_info.json",
        help="Output JSON file to save model information"
    )
    parser.add_argument(
        "--job-id",
        type=str,
        default=os.getenv("CUSTOMIZATION_JOB_ID", ""),
        help="Customization job ID (alternative to --model-name)"
    )
    parser.add_argument(
        "--entity-store-url",
        type=str,
        default=ENTITY_STORE_URL,
        help=f"Entity Store URL (default: {ENTITY_STORE_URL})"
    )
    parser.add_argument(
        "--customizer-url",
        type=str,
        default=CUSTOMIZER_URL,
        help=f"Customizer URL (default: {CUSTOMIZER_URL})"
    )
    
    args = parser.parse_args()
    
    # Determine if we should use auto mode
    auto_mode = not args.model_name and not args.job_id
    
    if auto_mode:
        print("🤖 AUTO MODE: No arguments provided, will find last completed job automatically")
        print("   (Use --model-name or --job-id to specify explicitly)")
    
    print("=" * 70)
    print("Get Customized Model Information")
    print("=" * 70)
    print(f"Namespace: {NMS_NAMESPACE}")
    if args.model_name:
        print(f"Model Name: {args.model_name}")
    if args.job_id:
        print(f"Job ID: {args.job_id}")
    print("")
    
    # Check connectivity
    print("🔍 Checking service connectivity...")
    services_ok = True
    
    # Check Entity Store
    try:
        health_response = requests.get(f"{args.entity_store_url}/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ Entity Store is accessible")
        else:
            print(f"⚠️  Entity Store health check returned: {health_response.status_code}")
            services_ok = False
    except Exception as e:
        print(f"⚠️  Cannot reach Entity Store at {args.entity_store_url}")
        print(f"   Error: {e}")
        services_ok = False
    
    # Check Customizer
    try:
        health_response = requests.get(f"{args.customizer_url}/v1/health/ready", timeout=5)
        if health_response.status_code == 200:
            print("✅ Customizer is accessible")
        else:
            print(f"⚠️  Customizer health check returned: {health_response.status_code}")
            services_ok = False
    except Exception as e:
        print(f"⚠️  Cannot reach Customizer at {args.customizer_url}")
        print(f"   Error: {e}")
        services_ok = False
    
    if not services_ok:
        print(f"\n💡 Make sure port-forwards are running:")
        print(f"   ./setup_port_forwards.sh")
        print(f"   Or set ENTITY_STORE_URL and CUSTOMIZER_URL environment variables")
    
    print("")
    result = get_model_info(
        model_name=args.model_name,
        job_id=args.job_id,
        entity_store_url=args.entity_store_url,
        customizer_url=args.customizer_url,
        auto_mode=auto_mode
    )
    
    if result["success"]:
        # Save to JSON file
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Model information saved to: {args.output}")
        print(f"\n📋 Next steps:")
        print(f"   1. Use the files_url to download model from DataStore")
        if result.get("files_url"):
            print(f"   2. Run: python download_model_from_datastore.py --files-url '{result['files_url']}' --output-dir ./downloaded_model")
        else:
            print(f"   2. Run: python download_model_from_datastore.py --model-info {args.output}")
        return 0
    else:
        print(f"\n❌ Failed to get model information")
        return 1


if __name__ == "__main__":
    sys.exit(main())
