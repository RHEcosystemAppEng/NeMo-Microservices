#!/usr/bin/env python3
"""
Download Customized Model from DataStore

This script downloads the customized model files from DataStore using
the HuggingFace-compatible API.

Usage:
    python download_model_from_datastore.py --model-info model_info.json --output-dir ./downloaded_model
    
    Or specify files_url directly:
    python download_model_from_datastore.py --files-url "hf://datasets/anemo-rhoai/model-name" --output-dir ./downloaded_model
"""

import os
import sys
import json
import argparse
import tempfile
import requests
from pathlib import Path

# Load environment variables from env.donotcommit if it exists
try:
    from dotenv import load_dotenv
    env_donotcommit_path = Path(__file__).parent / "env.donotcommit"
    if env_donotcommit_path.exists():
        load_dotenv(env_donotcommit_path, override=False)
except ImportError:
    pass

# Configuration
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Determine if running locally (with port-forward) or in cluster
DATASTORE_URL = os.getenv("DATASTORE_URL")
if not DATASTORE_URL:
    # Try localhost first (for port-forward), then cluster-internal
    DATASTORE_URL = os.getenv("DATASTORE_URL_LOCAL", "http://localhost:8001")
    CLUSTER_DATASTORE_URL = f"http://nemodatastore-sample.{NMS_NAMESPACE}.svc.cluster.local:8000"
else:
    CLUSTER_DATASTORE_URL = DATASTORE_URL

NDS_TOKEN = os.getenv("NDS_TOKEN", "token")


def parse_files_url(files_url):
    """Parse files_url to extract repository information."""
    # Format: hf://datasets/{namespace}/{repo_name} or hf://models/{namespace}/{repo_name}
    if not files_url.startswith("hf://"):
        raise ValueError(f"Invalid files_url format. Expected hf://, got: {files_url}")
    
    path = files_url.replace("hf://", "")
    
    # Extract revision if present (format: repo-name@version)
    revision = None
    if "@" in path:
        path, revision = path.rsplit("@", 1)
    
    # Remove datasets/ or models/ prefix
    if path.startswith("datasets/"):
        path = path.replace("datasets/", "")
        repo_type = "dataset"
    elif path.startswith("models/"):
        path = path.replace("models/", "")
        repo_type = "model"
    else:
        repo_type = "model"  # Default
    
    if "/" in path:
        repo_namespace, repo_name = path.split("/", 1)
    else:
        repo_namespace = NMS_NAMESPACE
        repo_name = path
    
    return repo_namespace, repo_name, repo_type, revision


def download_model(files_url, output_dir, datastore_url=None, job_id=None, model_name=None):
    """Download model files from DataStore using HuggingFace API.
    
    If DataStore is empty, this will suggest using download_model_from_pvc.py as fallback.
    """
    if datastore_url is None:
        datastore_url = DATASTORE_URL
    
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError:
        print("❌ Error: huggingface_hub not installed")
        print("   Install with: pip install huggingface_hub")
        return False
    
    print(f"\n📥 Downloading model from DataStore...")
    print(f"   Files URL: {files_url}")
    print(f"   DataStore URL: {datastore_url}")
    
    try:
        repo_namespace, repo_name, repo_type, revision = parse_files_url(files_url)
        repo_id = f"{repo_namespace}/{repo_name}"
        
        print(f"   Repository: {repo_id} (type: {repo_type})")
        if revision:
            print(f"   Revision: {revision}")
        
        # Initialize HuggingFace API pointing to DataStore
        hf_endpoint = f"{datastore_url}/v1/hf"
        hf_token = NDS_TOKEN if NDS_TOKEN != "token" else None
        api = HfApi(endpoint=hf_endpoint, token=hf_token)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Verify repository exists first
        # IMPORTANT: Customizer stores output models as "model" type in DataStore,
        # even if the files_url uses "datasets/" prefix. Try both types.
        print(f"\n📋 Verifying repository exists...")
        repo_info = None
        actual_repo_type = None
        
        # Try the parsed repo_type first
        try:
            repo_info = api.repo_info(repo_id=repo_id, repo_type=repo_type)
            actual_repo_type = repo_type
            print(f"   ✅ Repository found as {repo_type}: {repo_id}")
            print(f"   Repository ID: {repo_info.id}")
        except Exception as e:
            # If failed, try the other type (models are often stored as "model" even if URL says "datasets")
            other_type = "model" if repo_type == "dataset" else "dataset"
            try:
                print(f"   ⚠️  Not found as {repo_type}, trying as {other_type}...")
                repo_info = api.repo_info(repo_id=repo_id, repo_type=other_type)
                actual_repo_type = other_type
                print(f"   ✅ Repository found as {other_type}: {repo_id}")
                print(f"   Repository ID: {repo_info.id}")
                print(f"   💡 Note: files_url used '{repo_type}' prefix, but actual storage is '{other_type}'")
                repo_type = other_type  # Update for download
            except Exception as e2:
                print(f"   ❌ Repository not found as either type")
                print(f"   Repository: {repo_id}")
                print(f"   Tried as {repo_type}: {str(e)[:100]}")
                print(f"   Tried as {other_type}: {str(e2)[:100]}")
                print(f"   DataStore URL: {datastore_url}")
                return False
        
        # Download entire repository snapshot
        print(f"\n⬇️  Downloading repository snapshot to: {output_dir}")
        try:
            # Use snapshot_download to download entire repo
            # This is more reliable than downloading files individually
            download_kwargs = {
                "repo_id": repo_id,
                "local_dir": str(output_path),
                "endpoint": hf_endpoint,
                "token": hf_token,
                "repo_type": repo_type,
                "local_dir_use_symlinks": False  # Don't use symlinks, copy files directly
            }
            if revision:
                download_kwargs["revision"] = revision
                print(f"   📌 Using revision: {revision}")
            
            downloaded_path = snapshot_download(**download_kwargs)
            
            # Count downloaded files (exclude cache and metadata files)
            all_files = list(output_path.rglob("*"))
            downloaded_files = [
                f for f in all_files 
                if f.is_file() 
                and not str(f).endswith('.lock')
                and not str(f).endswith('.metadata')
                and '.cache' not in str(f)
                and f.name != '.gitignore'
            ]
            
            # Check if we got actual model files (not just .gitattributes)
            model_files = [
                f for f in downloaded_files 
                if not f.name.startswith('.') 
                or f.name in ['.gitattributes', 'config.json', 'tokenizer.json']
            ]
            
            if len(model_files) == 0 or (len(model_files) == 1 and model_files[0].name == '.gitattributes'):
                print(f"\n⚠️  WARNING: Repository appears to be empty!")
                print(f"   Only metadata files found (no actual model files)")
                print(f"   This suggests the model files were not uploaded to DataStore")
                print(f"\n💡 Model files are likely in PVC or training pod")
                print(f"\n🔄 Attempting to download from PVC/training pod as fallback...")
                print(f"   (This requires job_id or model_name - checking if available)")
                
                # Try to get job_id from files_url or model_info if available
                # This is a fallback - we'll create a separate script for PVC download
                print(f"\n📋 To download from PVC, use:")
                print(f"   python download_model_from_pvc.py --job-id <job-id> --output-dir {output_dir}")
                print(f"   Or:")
                print(f"   python download_model_from_pvc.py --model-name <model-name> --output-dir {output_dir}")
                print(f"\n   The download_model_from_pvc.py script will:")
                print(f"   1. Find the training pod (if still exists)")
                print(f"   2. Or access the workspace PVC directly")
                print(f"   3. Download model files from /pvc/workspace or similar location")
                
                return False
            
            print(f"\n✅ Download complete!")
            print(f"   Downloaded {len(model_files)} model file(s) to: {output_dir}")
            print(f"   Files include:")
            for f in sorted(model_files)[:15]:  # Show first 15 files
                rel_path = f.relative_to(output_path)
                file_size = f.stat().st_size
                size_str = f"({file_size:,} bytes)" if file_size > 0 else "(empty)"
                print(f"      - {rel_path} {size_str}")
            if len(model_files) > 15:
                print(f"      ... and {len(model_files) - 15} more files")
            
            return len(model_files) > 0
            
        except Exception as e:
            print(f"   ❌ Error downloading repository: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download customized model from DataStore"
    )
    parser.add_argument(
        "--model-info",
        type=str,
        help="JSON file with model information (from export_model_from_entity_store.py)"
    )
    parser.add_argument(
        "--files-url",
        type=str,
        help="Files URL directly (e.g., hf://datasets/namespace/model-name)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./downloaded_model",
        help="Output directory for downloaded model files"
    )
    parser.add_argument(
        "--datastore-url",
        type=str,
        default=DATASTORE_URL,
        help=f"DataStore URL (default: {DATASTORE_URL})"
    )
    
    args = parser.parse_args()
    
    # Get files_url from either model-info file or direct argument
    files_url = None
    
    if args.model_info:
        try:
            with open(args.model_info, 'r') as f:
                model_info = json.load(f)
            files_url = model_info.get("files_url")
            if not files_url:
                print(f"❌ Error: files_url not found in {args.model_info}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading model info file: {e}")
            sys.exit(1)
    elif args.files_url:
        files_url = args.files_url
    else:
        print("❌ Error: Either --model-info or --files-url must be provided")
        parser.print_help()
        sys.exit(1)
    
    print("=" * 70)
    print("Download Customized Model from DataStore")
    print("=" * 70)
    print(f"DataStore URL: {args.datastore_url}")
    print(f"Namespace: {NMS_NAMESPACE}")
    
    # Check connectivity
    try:
        health_response = requests.get(f"{args.datastore_url}/v1/health", timeout=5)
        if health_response.status_code == 200:
            print("✅ DataStore is accessible")
        else:
            print(f"⚠️  DataStore health check returned: {health_response.status_code}")
    except Exception as e:
        print(f"⚠️  Cannot reach DataStore at {args.datastore_url}")
        print(f"   Error: {e}")
        print(f"\n💡 Make sure port-forward is running:")
        print(f"   oc port-forward -n {NMS_NAMESPACE} svc/nemodatastore-sample 8001:8000")
        print(f"   Or set DATASTORE_URL environment variable")
        if 'CLUSTER_DATASTORE_URL' in globals():
            print(f"   Cluster-internal URL: {CLUSTER_DATASTORE_URL} (requires running in cluster)")
    
    success = download_model(files_url, args.output_dir, args.datastore_url)
    
    if success:
        print(f"\n✅ Model downloaded successfully to: {args.output_dir}")
        print(f"\n📋 Next steps:")
        print(f"   1. Upload model to MinIO")
        print(f"   2. Run: python upload_model_to_minio.py --model-dir {args.output_dir}")
        return 0
    else:
        print(f"\n❌ Failed to download model")
        return 1


if __name__ == "__main__":
    sys.exit(main())
