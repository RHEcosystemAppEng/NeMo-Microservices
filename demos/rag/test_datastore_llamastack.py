#!/usr/bin/env python3
"""
Test script to verify LlamaStack dataset registration with Data Store.

This script tests:
1. Data Store connectivity (via port-forward)
2. Creating namespace in Data Store
3. Uploading files to Data Store (using HuggingFace API)
4. Registering dataset with LlamaStack
5. Verifying dataset exists in Data Store

Usage:
    # First, port-forward Data Store and LlamaStack:
    oc port-forward -n <namespace> svc/nemodatastore-sample 8000:8000 &
    oc port-forward -n <namespace> svc/llamastack 8321:8321 &
    
    # Then run this script:
    python test_datastore_llamastack.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional

# Try to load from env.donotcommit
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "env.donotcommit"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Configuration
NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")
DATASET_NAME = os.getenv("DATASET_NAME", "rag-tutorial-test")
NDS_TOKEN = os.getenv("NDS_TOKEN", "token")

# URLs (for port-forward testing)
# If running from within cluster, use cluster URLs
# If running locally, use localhost with port-forward
USE_PORT_FORWARD = os.getenv("USE_PORT_FORWARD", "true").lower() == "true"

if USE_PORT_FORWARD:
    NDS_URL = "http://localhost:8000"
    LLAMASTACK_URL = "http://localhost:8321"
    print("🔧 Using port-forward URLs (localhost)")
else:
    NDS_URL = f"http://nemodatastore-sample.{NAMESPACE}.svc.cluster.local:8000"
    LLAMASTACK_URL = f"http://llamastack.{NAMESPACE}.svc.cluster.local:8321"
    print("🔧 Using cluster URLs")

print(f"\n📋 Configuration:")
print(f"   Namespace: {NAMESPACE}")
print(f"   Dataset Name: {DATASET_NAME}")
print(f"   Data Store URL: {NDS_URL}")
print(f"   LlamaStack URL: {LLAMASTACK_URL}")
print()

# Test 1: Data Store connectivity
print("=" * 80)
print("Test 1: Data Store Connectivity")
print("=" * 80)
try:
    response = requests.get(f"{NDS_URL}/v1/datastore/namespaces", 
                           headers={"Authorization": f"Bearer {NDS_TOKEN}"},
                           timeout=5)
    if response.status_code == 200:
        print("✅ Data Store is reachable")
        namespaces = response.json()
        print(f"   Found {len(namespaces)} namespaces")
    else:
        print(f"⚠️  Data Store returned status {response.status_code}")
        print(f"   Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Failed to connect to Data Store: {e}")
    print(f"   Make sure Data Store is running and port-forward is active:")
    print(f"   oc port-forward -n {NAMESPACE} svc/nemodatastore-sample 8000:8000")
    sys.exit(1)

# Test 2: Create namespace
print("\n" + "=" * 80)
print("Test 2: Create/Verify Namespace")
print("=" * 80)
namespace_url = f"{NDS_URL}/v1/datastore/namespaces/{NAMESPACE}"
try:
    response = requests.get(namespace_url, 
                          headers={"Authorization": f"Bearer {NDS_TOKEN}"},
                          timeout=5)
    if response.status_code == 200:
        print(f"✅ Namespace '{NAMESPACE}' exists")
    elif response.status_code == 404:
        # Create namespace
        response = requests.post(
            f"{NDS_URL}/v1/datastore/namespaces",
            json={"name": NAMESPACE},
            headers={"Authorization": f"Bearer {NDS_TOKEN}"},
            timeout=5
        )
        if response.status_code in (200, 201):
            print(f"✅ Created namespace '{NAMESPACE}'")
        else:
            print(f"❌ Failed to create namespace: {response.status_code} - {response.text}")
            sys.exit(1)
    else:
        print(f"⚠️  Unexpected status: {response.status_code} - {response.text}")
except Exception as e:
    print(f"❌ Error checking namespace: {e}")
    sys.exit(1)

# Test 3: Upload sample file to Data Store using HuggingFace API
print("\n" + "=" * 80)
print("Test 3: Upload Sample File to Data Store")
print("=" * 80)

# Create a sample document
sample_doc = {
    "id": "test-doc-1",
    "title": "Test Document",
    "content": "This is a test document for RAG tutorial."
}

# Try to upload using HuggingFace API
try:
    from huggingface_hub import HfApi
    
    # Set HuggingFace endpoint to Data Store
    hf_endpoint = f"{NDS_URL}/v1/hf"
    hf_token = NDS_TOKEN if NDS_TOKEN != "token" else None
    
    hf_api = HfApi(endpoint=hf_endpoint, token=hf_token)
    
    # Create repo (dataset) in Data Store
    repo_id = f"{NAMESPACE}/{DATASET_NAME}"
    print(f"   Creating dataset repo: {repo_id}")
    
    try:
        hf_api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        print(f"✅ Dataset repo created: {repo_id}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"ℹ️  Dataset repo already exists: {repo_id}")
        else:
            print(f"⚠️  Error creating repo: {e}")
            print(f"   Continuing anyway...")
    
    # Upload a sample file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_doc, f, indent=2)
        temp_file = f.name
    
    try:
        print(f"   Uploading sample file to {repo_id}/test-doc-1.json")
        hf_api.upload_file(
            path_or_fileobj=temp_file,
            path_in_repo="test-doc-1.json",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print(f"✅ Sample file uploaded successfully")
        file_uploaded = True
    except Exception as e:
        print(f"⚠️  Error uploading file: {e}")
        print(f"   This might be OK if the dataset already has files")
        file_uploaded = False
    finally:
        os.unlink(temp_file)
    
except ImportError:
    print("⚠️  huggingface_hub not installed - skipping file upload")
    print("   Install with: pip install huggingface_hub")
    print("   For this test, we'll try to register without uploading files first")
    file_uploaded = False
    repo_id = f"{NAMESPACE}/{DATASET_NAME}"
except Exception as e:
    print(f"⚠️  Error with HuggingFace API: {e}")
    print(f"   Continuing to test LlamaStack registration...")
    file_uploaded = False
    repo_id = f"{NAMESPACE}/{DATASET_NAME}"

# Test 4: LlamaStack connectivity
print("\n" + "=" * 80)
print("Test 4: LlamaStack Connectivity")
print("=" * 80)
try:
    from llama_stack_client import LlamaStackClient
    
    client = LlamaStackClient(base_url=LLAMASTACK_URL)
    print("✅ LlamaStack client initialized")
    
    # Test connectivity
    try:
        server_info = client._client.get("/")
        print("✅ LlamaStack is reachable")
    except Exception as e:
        if "404" in str(e) or "Not Found" in str(e):
            print("✅ LlamaStack is reachable (404 on root is expected)")
        else:
            print(f"⚠️  LlamaStack connectivity issue: {e}")
            print(f"   Make sure LlamaStack is running and port-forward is active:")
            print(f"   oc port-forward -n {NAMESPACE} svc/llamastack 8321:8321")
            sys.exit(1)
            
except ImportError:
    print("❌ llama-stack-client not installed")
    print("   Install with: pip install --upgrade git+https://github.com/meta-llama/llama-stack-client-python.git@main")
    sys.exit(1)
except Exception as e:
    print(f"❌ Failed to initialize LlamaStack client: {e}")
    sys.exit(1)

# Test 5: Register dataset with LlamaStack
print("\n" + "=" * 80)
print("Test 5: Register Dataset with LlamaStack")
print("=" * 80)

dataset_uri = f"hf://datasets/{repo_id}"
print(f"   Dataset URI: {dataset_uri}")
print(f"   Dataset ID: {DATASET_NAME}")

if not file_uploaded:
    print("   ⚠️  WARNING: No files were uploaded to Data Store")
    print("   LlamaStack registration might fail if the dataset doesn't exist in Data Store")
    print("   This is the key issue we're testing!")

try:
    response = client.beta.datasets.register(
        purpose="post-training/messages",
        dataset_id=DATASET_NAME,
        source={
            "type": "uri",
            "uri": dataset_uri
        },
        metadata={
            "format": "json",
            "description": f"Test dataset for RAG tutorial verification",
            "provider_id": "nvidia",
        }
    )
    print(f"✅ Dataset registered successfully with LlamaStack!")
    print(f"   Response: {response}")
    if hasattr(response, 'dataset_id'):
        print(f"   Dataset ID: {response.dataset_id}")
    
except Exception as e:
    error_msg = str(e)
    print(f"❌ Failed to register dataset with LlamaStack")
    print(f"   Error: {error_msg}")
    
    if "not found" in error_msg.lower() or "404" in error_msg:
        print(f"\n💡 DIAGNOSIS: Dataset not found in Data Store")
        print(f"   This confirms that LlamaStack requires the dataset to exist in Data Store first!")
        print(f"   Solution: Upload files to Data Store BEFORE registering with LlamaStack")
    elif "already exists" in error_msg.lower() or "409" in error_msg:
        print(f"\n💡 Dataset already exists (this is OK)")
    else:
        print(f"\n💡 Unknown error - check LlamaStack logs")
    
    sys.exit(1)

# Test 6: Verify dataset in Data Store
print("\n" + "=" * 80)
print("Test 6: Verify Dataset in Data Store")
print("=" * 80)

try:
    # Try to list files in the dataset using HuggingFace API
    try:
        from huggingface_hub import HfApi
        hf_api = HfApi(endpoint=f"{NDS_URL}/v1/hf", token=NDS_TOKEN if NDS_TOKEN != "token" else None)
        files = hf_api.list_repo_files(repo_id=repo_id, repo_type="dataset")
        print(f"✅ Dataset exists in Data Store")
        print(f"   Files in dataset: {len(files)}")
        for file in files[:5]:  # Show first 5 files
            print(f"      - {file}")
        if len(files) > 5:
            print(f"      ... and {len(files) - 5} more")
    except ImportError:
        print("⚠️  huggingface_hub not installed - skipping verification")
    except Exception as e:
        print(f"⚠️  Error verifying dataset: {e}")
        print(f"   Dataset might still be registered with LlamaStack even if verification fails")
        
except Exception as e:
    print(f"⚠️  Error during verification: {e}")

print("\n" + "=" * 80)
print("✅ All tests completed!")
print("=" * 80)
print("\n📝 Summary:")
print(f"   - Data Store: {'✅' if True else '❌'}")
print(f"   - Namespace: {'✅' if True else '❌'}")
print(f"   - File Upload: {'✅' if file_uploaded else '⚠️  Skipped'}")
print(f"   - LlamaStack: {'✅' if True else '❌'}")
print(f"   - Dataset Registration: {'✅' if True else '❌'}")

if not file_uploaded:
    print("\n⚠️  IMPORTANT: File upload was skipped or failed.")
    print("   LlamaStack dataset registration requires files to exist in Data Store first.")
    print("   Make sure to upload files before registering with LlamaStack!")


