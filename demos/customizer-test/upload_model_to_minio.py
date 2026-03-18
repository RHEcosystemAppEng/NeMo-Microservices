#!/usr/bin/env python3
"""
Upload Customized Model to MinIO

This script uploads the downloaded model files to MinIO bucket
for use with RHOAI Single Serving Runtime.

Usage:
    python upload_model_to_minio.py --model-dir ./merged_model --target-path "models/llama-3.2-1b-instruct-cust"
    
    From laptop: MinIO is in-cluster, so port-forward first, then set endpoint:
    oc port-forward -n $NAMESPACE svc/nemo-infra-minio 9000:80
    MINIO_ENDPOINT=http://localhost:9000 python upload_model_to_minio.py --model-dir ./merged_model --target-path models/llama-3.2-1b-instruct-cust
    
    Or update existing base model path:
    python upload_model_to_minio.py --model-dir ./merged_model --update-existing
"""

import os
import sys
import json
import argparse
import subprocess
import base64
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


def get_minio_config():
    """Get MinIO configuration from Kubernetes secret (tries minio-conn1, then minio-conn)."""
    for secret_name in ("minio-conn1", "minio-conn"):
        try:
            result = subprocess.run(
                ["oc", "get", "secret", secret_name, "-n", NMS_NAMESPACE, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                secret_json = json.loads(result.stdout)
                secret_data = secret_json.get('data', {})
                minio_endpoint = base64.b64decode(secret_data.get('AWS_S3_ENDPOINT', '')).decode('utf-8')
                minio_bucket = base64.b64decode(secret_data.get('AWS_S3_BUCKET', '')).decode('utf-8')
                minio_access_key = base64.b64decode(secret_data.get('AWS_ACCESS_KEY_ID', '')).decode('utf-8')
                minio_secret_key = base64.b64decode(secret_data.get('AWS_SECRET_ACCESS_KEY', '')).decode('utf-8')
                return {
                    "endpoint": minio_endpoint,
                    "bucket": minio_bucket,
                    "access_key": minio_access_key,
                    "secret_key": minio_secret_key
                }
            # Secret exists but wrong format or missing keys; try next
        except FileNotFoundError:
            print(f"⚠️  oc command not found - cannot retrieve MinIO config automatically")
            return None
        except Exception as e:
            if secret_name == "minio-conn":
                print(f"⚠️  Could not get MinIO config from {secret_name}: {e}")
            continue
    print(f"⚠️  Could not get MinIO secret (tried minio-conn1, minio-conn)")
    return None


def upload_to_minio(model_dir, target_path, minio_config):
    """Upload model files to MinIO."""
    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        print("❌ Error: boto3 not installed")
        print("   Install with: pip install boto3")
        return False
    
    print(f"\n📤 Uploading model to MinIO...")
    print(f"   Endpoint: {minio_config['endpoint']}")
    print(f"   Bucket: {minio_config['bucket']}")
    print(f"   Target Path: {target_path}")
    
    try:
        # Create S3 client for MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=minio_config['endpoint'],
            aws_access_key_id=minio_config['access_key'],
            aws_secret_access_key=minio_config['secret_key'],
            config=Config(signature_version='s3v4'),
            verify=False
        )
        
        # Find all files in model directory
        model_path = Path(model_dir)
        if not model_path.exists():
            print(f"❌ Error: Model directory does not exist: {model_dir}")
            return False
        
        # Get all files recursively
        files_to_upload = []
        for file_path in model_path.rglob('*'):
            if file_path.is_file():
                files_to_upload.append(file_path)
        
        if not files_to_upload:
            print(f"⚠️  No files found in {model_dir}")
            return False
        
        print(f"\n📋 Found {len(files_to_upload)} files to upload")
        
        # Upload files
        uploaded_count = 0
        failed_count = 0
        
        for local_file in files_to_upload:
            # Get relative path from model_dir
            rel_path = local_file.relative_to(model_path)
            s3_key = f"{target_path}/{rel_path}".replace("\\", "/")  # Normalize path separators
            
            try:
                s3_client.upload_file(str(local_file), minio_config['bucket'], s3_key)
                uploaded_count += 1
                print(f"   ✅ {s3_key}")
            except Exception as e:
                failed_count += 1
                print(f"   ⚠️  Failed to upload {rel_path}: {str(e)[:80]}")
        
        print(f"\n✅ Upload complete!")
        print(f"   Uploaded: {uploaded_count} files")
        if failed_count > 0:
            print(f"   Failed: {failed_count} files")
        
        return uploaded_count > 0
        
    except Exception as e:
        print(f"\n❌ Error uploading to MinIO: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Upload customized model to MinIO"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        required=True,
        help="Directory containing downloaded model files"
    )
    parser.add_argument(
        "--target-path",
        type=str,
        help="Target path in MinIO (e.g., models/llama-3.2-1b-instruct-custom)"
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing model at models/llama-3.2-1b-instruct (replaces base model)"
    )
    parser.add_argument(
        "--minio-endpoint",
        type=str,
        help="MinIO endpoint URL (overrides secret)"
    )
    parser.add_argument(
        "--minio-bucket",
        type=str,
        help="MinIO bucket name (overrides secret)"
    )
    parser.add_argument(
        "--minio-access-key",
        type=str,
        help="MinIO access key (overrides secret)"
    )
    parser.add_argument(
        "--minio-secret-key",
        type=str,
        help="MinIO secret key (overrides secret)"
    )
    
    args = parser.parse_args()
    
    # Determine target path
    if args.update_existing:
        target_path = "models/llama-3.2-1b-instruct"
        print("⚠️  WARNING: This will replace the existing base model!")
    elif args.target_path:
        target_path = args.target_path
    else:
        # Default: create new path based on model directory name
        model_dir_name = Path(args.model_dir).name
        target_path = f"models/{model_dir_name}"
        print(f"ℹ️  Using default target path: {target_path}")
        print(f"   Use --target-path to specify a custom path")
    
    # Get MinIO configuration
    if args.minio_endpoint and args.minio_bucket and args.minio_access_key and args.minio_secret_key:
        minio_config = {
            "endpoint": args.minio_endpoint,
            "bucket": args.minio_bucket,
            "access_key": args.minio_access_key,
            "secret_key": args.minio_secret_key
        }
    else:
        minio_config = get_minio_config()
        if not minio_config:
            print("\n❌ Error: Could not get MinIO configuration")
            print("\n💡 Options:")
            print("   1. Use --minio-endpoint, --minio-bucket, --minio-access-key, --minio-secret-key")
            print("   2. Get credentials manually:")
            print(f"      oc get secret minio-conn1 -n {NMS_NAMESPACE} -o jsonpath='{{.data}}' | jq -r 'to_entries | .[] | \"\\(.key): \\(.value | @base64d)\"'")
            sys.exit(1)
        # Override endpoint when uploading from laptop (port-forward: oc port-forward -n $NAMESPACE svc/nemo-infra-minio 9000:80)
        override = os.getenv("MINIO_ENDPOINT")
        if override:
            minio_config = {**minio_config, "endpoint": override}
    
    print("=" * 70)
    print("Upload Customized Model to MinIO")
    print("=" * 70)
    print(f"Namespace: {NMS_NAMESPACE}")
    print(f"Model Directory: {args.model_dir}")
    print(f"Target Path: {target_path}")
    
    success = upload_to_minio(args.model_dir, target_path, minio_config)
    
    if success:
        print(f"\n✅ Model uploaded successfully to MinIO!")
        print(f"\n📋 Next steps:")
        print(f"   1. Update InferenceService to use the new model path")
        print(f"   2. Run: oc patch inferenceservice <inferenceservice-name> -n {NMS_NAMESPACE} --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/predictor/model/storage/path\", \"value\": \"{target_path}\"}}]'")
        print(f"   3. Restart InferenceService pod: oc delete pod -n {NMS_NAMESPACE} -l serving.kserve.io/inferenceservice=<inferenceservice-name>")
        print(f"   4. Run test-customized-model.ipynb to test the customized model")
        return 0
    else:
        print(f"\n❌ Failed to upload model")
        return 1


if __name__ == "__main__":
    sys.exit(main())
