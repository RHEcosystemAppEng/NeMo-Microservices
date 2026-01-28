#!/usr/bin/env python3
"""
Complete Workflow: Export and Deploy Customized Model

This script combines all steps to export the customized model from Entity Store,
download from DataStore, and upload to MinIO.

Usage:
    python export_and_deploy_model.py --model-name "anemo-rhoai/llama-3.2-1b-instruct-custom-1234567890-12345@1.0"
"""

import os
import sys
import argparse
import tempfile
import shutil
from pathlib import Path

# Import our modules
from export_model_from_entity_store import get_model_info, ENTITY_STORE_URL
from download_model_from_datastore import download_model, DATASTORE_URL
from upload_model_to_minio import get_minio_config, upload_to_minio


def main():
    parser = argparse.ArgumentParser(
        description="Complete workflow: Export and deploy customized model"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=os.getenv("CUSTOMIZED_MODEL_NAME", ""),
        help="Customized model name"
    )
    parser.add_argument(
        "--target-path",
        type=str,
        help="Target path in MinIO (default: auto-generated from model name)"
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing model at models/llama-3.2-1b-instruct"
    )
    parser.add_argument(
        "--keep-downloads",
        action="store_true",
        help="Keep downloaded files after upload (default: delete)"
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        help="Directory for downloads (default: temporary directory)"
    )
    parser.add_argument(
        "--entity-store-url",
        type=str,
        default=ENTITY_STORE_URL,
        help=f"Entity Store URL (default: {ENTITY_STORE_URL})"
    )
    parser.add_argument(
        "--datastore-url",
        type=str,
        default=DATASTORE_URL,
        help=f"DataStore URL (default: {DATASTORE_URL})"
    )
    
    args = parser.parse_args()
    
    if not args.model_name:
        print("❌ Error: Model name is required")
        print("\nUsage:")
        print("  python export_and_deploy_model.py --model-name 'anemo-rhoai/llama-3.2-1b-instruct-custom-1234567890-12345@1.0'")
        sys.exit(1)
    
    print("=" * 70)
    print("Complete Workflow: Export and Deploy Customized Model")
    print("=" * 70)
    
    # Step 1: Get model info from Entity Store
    print("\n" + "=" * 70)
    print("Step 1: Get Model Information from Entity Store")
    print("=" * 70)
    model_info = get_model_info(args.model_name, args.entity_store_url)
    
    if not model_info.get("success"):
        print(f"\n❌ Failed to get model information")
        sys.exit(1)
    
    files_url = model_info.get("files_url")
    if not files_url:
        print(f"\n❌ Error: files_url not found in model info")
        sys.exit(1)
    
    # Step 2: Download from DataStore
    print("\n" + "=" * 70)
    print("Step 2: Download Model from DataStore")
    print("=" * 70)
    
    if args.download_dir:
        download_dir = args.download_dir
        Path(download_dir).mkdir(parents=True, exist_ok=True)
    else:
        download_dir = tempfile.mkdtemp(prefix="model_export_")
    
    try:
        success = download_model(files_url, download_dir, args.datastore_url)
        if not success:
            print(f"\n❌ Failed to download model")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 3: Upload to MinIO
    print("\n" + "=" * 70)
    print("Step 3: Upload Model to MinIO")
    print("=" * 70)
    
    # Determine target path
    if args.update_existing:
        target_path = "models/llama-3.2-1b-instruct"
        print("⚠️  WARNING: This will replace the existing base model!")
    elif args.target_path:
        target_path = args.target_path
    else:
        # Generate from model name
        model_name_safe = args.model_name.replace('/', '-').replace('@', '-')
        target_path = f"models/{model_name_safe}"
        print(f"ℹ️  Using auto-generated target path: {target_path}")
    
    minio_config = get_minio_config()
    if not minio_config:
        print("\n❌ Error: Could not get MinIO configuration")
        print("   Please ensure you have access to the cluster and minio-conn1 secret exists")
        sys.exit(1)
    
    try:
        success = upload_to_minio(download_dir, target_path, minio_config)
        if not success:
            print(f"\n❌ Failed to upload model")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during upload: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Cleanup
    if not args.keep_downloads and not args.download_dir:
        print(f"\n🧹 Cleaning up temporary files...")
        shutil.rmtree(download_dir, ignore_errors=True)
        print(f"   Deleted: {download_dir}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Workflow Complete!")
    print("=" * 70)
    print(f"\n📋 Summary:")
    print(f"   Model: {args.model_name}")
    print(f"   MinIO Path: {target_path}")
    print(f"   Bucket: {minio_config['bucket']}")
    
    print(f"\n📋 Next Steps:")
    print(f"   1. Update InferenceService to use the new model:")
    print(f"      oc patch inferenceservice anemo-rhoai-model-ssr -n {os.getenv('NMS_NAMESPACE', 'anemo-rhoai')} \\")
    print(f"        --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/predictor/model/storage/path\", \"value\": \"{target_path}\"}}]'")
    print(f"\n   2. Restart InferenceService pod:")
    print(f"      oc delete pod -n {os.getenv('NMS_NAMESPACE', 'anemo-rhoai')} -l serving.kserve.io/inferenceservice=anemo-rhoai-model-ssr")
    print(f"\n   3. Run test-customized-model.ipynb to test the customized model")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
