#!/usr/bin/env python3
"""
Download Customized Model from PVC/Training Pod

This script downloads the customized model files directly from PVC storage.
It checks multiple locations and provides clear feedback.

⚠️  IMPORTANT: This script creates temporary pods that mount PVCs. These pods
   MUST be deleted after use, otherwise they will block training pods from
   accessing the same PVC (ReadWriteOnce volumes can only attach to one pod).

Usage:
    python download_model_from_pvc.py --job-id "cust-3W6fw2ABh4j6fH329mCH5Q" --output-dir ./downloaded_model
"""

import os
import sys
import json
import argparse
import subprocess
import time
import tarfile
import signal
import atexit
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_donotcommit_path = Path(__file__).parent / "env.donotcommit"
    if env_donotcommit_path.exists():
        load_dotenv(env_donotcommit_path, override=False)
except ImportError:
    pass

NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")

# Global registry of pods to clean up
_pods_to_cleanup = []
_cleanup_registered = False


def register_pod_for_cleanup(pod_name, namespace):
    """Register a pod to be cleaned up on exit."""
    global _pods_to_cleanup
    if pod_name:
        _pods_to_cleanup.append((pod_name, namespace))
        _register_cleanup_handlers()


def _register_cleanup_handlers():
    """Register signal handlers and atexit for cleanup."""
    global _cleanup_registered
    if _cleanup_registered:
        return
    
    _cleanup_registered = True
    
    def cleanup_all_pods():
        """Clean up all registered pods."""
        global _pods_to_cleanup
        if not _pods_to_cleanup:
            return
        
        print(f"\n🧹 Cleaning up {len(_pods_to_cleanup)} temporary pod(s)...")
        for pod_name, namespace in _pods_to_cleanup:
            try:
                result = subprocess.run(
                    ["oc", "delete", "pod", pod_name, "-n", namespace, "--ignore-not-found=true"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print(f"   ✅ Deleted pod: {pod_name}")
                else:
                    print(f"   ⚠️  Failed to delete pod {pod_name}: {result.stderr}")
            except Exception as e:
                print(f"   ⚠️  Error deleting pod {pod_name}: {e}")
        
        _pods_to_cleanup = []
    
    def signal_handler(signum, frame):
        """Handle interrupt signals."""
        print(f"\n⚠️  Interrupted (signal {signum}). Cleaning up...")
        cleanup_all_pods()
        sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Register atexit handler
    atexit.register(cleanup_all_pods)


def find_job_id_from_model_name(model_name, customizer_url):
    """Find job ID from model name."""
    try:
        import requests
        response = requests.get(f"{customizer_url}/v1/customization/jobs", timeout=30)
        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get('data', [])
            for job in jobs:
                if job.get('output_model') == model_name:
                    return job.get('id')
    except:
        pass
    return None


def find_pvc_for_job(job_id, namespace):
    """Find PVCs that might contain model files for this job."""
    try:
        result = subprocess.run(
            ["oc", "get", "pvc", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return []
        
        pvcs_data = json.loads(result.stdout)
        pvcs = pvcs_data.get('items', [])
        
        job_id_short = job_id.replace('cust-', '').lower()
        found_pvcs = []
        
        for pvc in pvcs:
            pvc_name = pvc.get('metadata', {}).get('name', '')
            # Check if PVC name contains job ID or is a workspace/finetuning PVC
            if (job_id_short in pvc_name.lower() or 
                job_id.lower() in pvc_name.lower() or
                'workspace' in pvc_name.lower() or
                'finetuning' in pvc_name.lower() or
                'models' in pvc_name.lower()):
                found_pvcs.append({
                    'name': pvc_name,
                    'size': pvc.get('spec', {}).get('resources', {}).get('requests', {}).get('storage', 'Unknown')
                })
        
        return found_pvcs
    except Exception as e:
        print(f"   ⚠️  Error finding PVCs: {e}")
        return []


def create_temp_pod(pvc_name, namespace, mount_path="/pvc/data"):
    """Create a temporary pod to access PVC."""
    # Use PVC name in pod name to ensure uniqueness when checking multiple PVCs
    pvc_suffix = pvc_name.replace('-', '').lower()[:15]  # Shortened PVC name for uniqueness
    pod_name = f"model-dl-{os.getpid()}-{pvc_suffix}"
    
    pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: {namespace}
spec:
  containers:
  - name: exporter
    image: busybox:latest
    command: ["sleep", "600"]
    volumeMounts:
    - name: pvc
      mountPath: {mount_path}
  volumes:
  - name: pvc
    persistentVolumeClaim:
      claimName: {pvc_name}
  restartPolicy: Never
"""
    
    try:
        # Delete any existing pod with this name first (in case of previous failed run)
        subprocess.run(
            ["oc", "delete", "pod", pod_name, "-n", namespace, "--ignore-not-found=true"],
            capture_output=True,
            timeout=10
        )
        time.sleep(1)  # Brief wait for deletion to complete
        
        # Create pod (use create instead of apply to avoid update conflicts)
        result = subprocess.run(
            ["oc", "create", "-f", "-"],
            input=pod_yaml,
            text=True,
            capture_output=True,
            timeout=30
        )
        if result.returncode != 0:
            # If pod already exists, that's OK - try to use it
            if "AlreadyExists" in result.stderr or "already exists" in result.stderr.lower():
                print(f"   ℹ️  Pod {pod_name} already exists, will try to use it")
            else:
                return None, result.stderr
        
        # Wait for pod to be ready
        for i in range(30):
            result = subprocess.run(
                ["oc", "get", "pod", pod_name, "-n", namespace, "-o", "jsonpath={.status.phase}"],
                capture_output=True,
                timeout=10
            )
            phase = result.stdout.strip().decode('utf-8') if isinstance(result.stdout, bytes) else result.stdout.strip()
            if phase == "Running":
                # Double-check with a test exec to ensure pod is actually usable
                test_result = subprocess.run(
                    ["oc", "exec", "-n", namespace, pod_name, "--", "echo", "test"],
                    capture_output=True,
                    timeout=5
                )
                if test_result.returncode == 0:
                    return pod_name, None
            elif phase == "Failed" or phase == "Error":
                # Get error details
                describe_result = subprocess.run(
                    ["oc", "describe", "pod", pod_name, "-n", namespace],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                error_msg = describe_result.stdout
                if "Multi-Attach" in error_msg or "volume is already attached" in error_msg:
                    return None, f"PVC is already attached to another pod (ReadWriteOnce limitation)"
            time.sleep(2)
        
        # Check final status
        final_result = subprocess.run(
            ["oc", "get", "pod", pod_name, "-n", namespace, "-o", "jsonpath={.status.phase}"],
            capture_output=True,
            timeout=10
        )
        final_phase = final_result.stdout.strip().decode('utf-8') if isinstance(final_result.stdout, bytes) else final_result.stdout.strip()
        if final_phase == "Running":
            # Pod is running but might not have been ready when we checked
            return pod_name, None
        return None, f"Pod did not become ready (final phase: {final_phase})"
    except Exception as e:
        return None, str(e)


def search_for_model_files(pod_name, namespace, search_path):
    """Search for model files in the pod."""
    try:
        # List directory
        result = subprocess.run(
            ["oc", "exec", "-n", namespace, pod_name, "--", "ls", "-la", search_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None, f"Path {search_path} does not exist or is not accessible"
        
        # Look for model files
        find_cmd = f"find {search_path} -type f \\( -name '*.pt' -o -name '*.safetensors' -o -name '*.bin' -o -name 'config.json' -o -name 'tokenizer.json' \\) 2>/dev/null | head -20"
        result = subprocess.run(
            ["oc", "exec", "-n", namespace, pod_name, "--", "sh", "-c", find_cmd],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and result.stdout.strip():
            files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            if files:
                # Get parent directory of first file
                dir_result = subprocess.run(
                    ["oc", "exec", "-n", namespace, pod_name, "--", "dirname", files[0]],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if dir_result.returncode == 0:
                    return dir_result.stdout.strip(), None
        
        # If no model files found, check if directory has subdirectories that might contain models
        dir_cmd = f"find {search_path} -maxdepth 2 -type d 2>/dev/null | head -10"
        result = subprocess.run(
            ["oc", "exec", "-n", namespace, pod_name, "--", "sh", "-c", dir_cmd],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            dirs = [d.strip() for d in result.stdout.strip().split('\n') if d.strip() and d.strip() != search_path]
            if dirs:
                return search_path, f"Found {len(dirs)} subdirectories, will download all"
        
        return search_path, "No model files found, but directory exists"
    except Exception as e:
        return None, str(e)


def download_from_pod(pod_name, namespace, source_path, output_dir):
    """Download files from pod."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"   📦 Creating archive...")
        archive_path = f"/tmp/model_{os.getpid()}.tar.gz"
        
        # Create tar archive
        # Use absolute paths and handle errors better
        tar_cmd = f"cd {source_path} && tar -czf {archive_path} . 2>&1 || (echo 'TAR_ERROR:' && cat {archive_path}.err 2>/dev/null || echo 'tar command failed')"
        result = subprocess.run(
            ["oc", "exec", "-n", namespace, pod_name, "--", "sh", "-c", tar_cmd],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            # Check if it's a disk space issue or permission issue
            if "No space left" in error_msg or "disk full" in error_msg.lower():
                return False, f"Failed to create archive: No space left on device"
            elif "Permission denied" in error_msg or "permission" in error_msg.lower():
                return False, f"Failed to create archive: Permission denied"
            else:
                return False, f"Failed to create archive: {error_msg[:200]}"
        
        # Copy archive
        print(f"   ⬇️  Downloading archive...")
        local_archive = output_path / "model.tar.gz"
        
        result = subprocess.run(
            ["oc", "cp", f"{namespace}/{pod_name}:{archive_path}", str(local_archive)],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            return False, f"Failed to copy archive: {result.stderr}"
        
        # Extract
        print(f"   📂 Extracting files...")
        with tarfile.open(local_archive, 'r:gz') as tar:
            tar.extractall(path=output_path)
        
        # Cleanup
        local_archive.unlink()
        subprocess.run(
            ["oc", "exec", "-n", namespace, pod_name, "--", "rm", "-f", archive_path],
            capture_output=True,
            timeout=10
        )
        
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Download customized model from PVC")
    parser.add_argument("--job-id", type=str, help="Customization job ID")
    parser.add_argument("--model-name", type=str, help="Model name (will find job ID)")
    parser.add_argument("--output-dir", type=str, default="./downloaded_model", help="Output directory")
    parser.add_argument("--namespace", type=str, default=NMS_NAMESPACE, help="Kubernetes namespace")
    parser.add_argument("--pvc-name", type=str, help="Specific PVC name to check")
    
    args = parser.parse_args()
    
    # Get job ID
    job_id = args.job_id
    if not job_id and args.model_name:
        print("🔍 Finding job ID from model name...")
        customizer_url = os.getenv("CUSTOMIZER_URL", "http://localhost:8003")
        job_id = find_job_id_from_model_name(args.model_name, customizer_url)
        if job_id:
            print(f"   ✅ Found job ID: {job_id}")
        else:
            print(f"   ❌ Could not find job ID")
            sys.exit(1)
    
    if not job_id:
        print("❌ Error: --job-id or --model-name required")
        parser.print_help()
        sys.exit(1)
    
    print("=" * 70)
    print("Download Customized Model from PVC")
    print("=" * 70)
    print(f"Job ID: {job_id}")
    print(f"Namespace: {args.namespace}")
    print(f"Output: {args.output_dir}\n")
    
    # Find PVCs
    if args.pvc_name:
        pvcs_to_check = [{'name': args.pvc_name, 'size': 'Unknown'}]
    else:
        print("🔍 Searching for PVCs...")
        pvcs_to_check = find_pvc_for_job(job_id, args.namespace)
        if not pvcs_to_check:
            print("   ❌ No relevant PVCs found")
            print("   💡 Try specifying --pvc-name manually")
            sys.exit(1)
        print(f"   ✅ Found {len(pvcs_to_check)} PVC(s) to check")
    
    # Try each PVC
    success = False
    for pvc_info in pvcs_to_check:
        pvc_name = pvc_info['name']
        print(f"\n📦 Checking PVC: {pvc_name} ({pvc_info.get('size', 'Unknown')})")
        
        # Determine mount path
        if 'finetuning' in pvc_name.lower() or 'models' in pvc_name.lower():
            mount_path = "/pvc/models"
            search_paths = ["/pvc/models"]
        else:
            mount_path = "/pvc/workspace"
            search_paths = ["/pvc/workspace", "/pvc/workspace/checkpoints", "/pvc/workspace/output"]
        
        # Create temp pod
        pod_name, error = create_temp_pod(pvc_name, args.namespace, mount_path)
        if not pod_name:
            print(f"   ⚠️  Could not create pod: {error}")
            continue
        
        # Register pod for cleanup (even if script is interrupted)
        register_pod_for_cleanup(pod_name, args.namespace)
        
        try:
            # Search for model files
            for search_path in search_paths:
                model_path, info = search_for_model_files(pod_name, args.namespace, search_path)
                if model_path:
                    print(f"   ✅ Found model location: {model_path}")
                    if info:
                        print(f"   ℹ️  {info}")
                    
                    # Download
                    print(f"\n⬇️  Downloading from {model_path}...")
                    download_success, download_error = download_from_pod(pod_name, args.namespace, model_path, args.output_dir)
                    
                    if download_success:
                        success = True
                        break
                    else:
                        print(f"   ⚠️  Download failed: {download_error}")
            
            if not success:
                print(f"   ⚠️  No model files found in this PVC")
        finally:
            # Cleanup pod - CRITICAL: Must delete to free PVC for other pods
            print(f"   🧹 Cleaning up temporary pod...")
            cleanup_result = subprocess.run(
                ["oc", "delete", "pod", pod_name, "-n", args.namespace, "--ignore-not-found=true"],
                capture_output=True,
                timeout=30
            )
            if cleanup_result.returncode == 0:
                print(f"   ✅ Pod deleted")
                # Remove from cleanup registry since we cleaned it up
                global _pods_to_cleanup
                _pods_to_cleanup = [(p, n) for p, n in _pods_to_cleanup if p != pod_name]
            else:
                print(f"   ⚠️  Warning: Pod cleanup may have failed: {cleanup_result.stderr}")
                print(f"   💡 Manually delete with: oc delete pod {pod_name} -n {args.namespace}")
                # Keep in registry for atexit cleanup
        
        if success:
            break
    
    # Final cleanup check - ensure all pods are deleted
    if _pods_to_cleanup:
        print(f"\n🧹 Final cleanup: removing {len(_pods_to_cleanup)} remaining pod(s)...")
        for pod_name, namespace in _pods_to_cleanup:
            subprocess.run(
                ["oc", "delete", "pod", pod_name, "-n", namespace, "--ignore-not-found=true"],
                capture_output=True,
                timeout=10
            )
        _pods_to_cleanup = []
    
    # Report results
    if success:
        output_path = Path(args.output_dir)
        files = [f for f in output_path.rglob("*") if f.is_file() and '.cache' not in str(f)]
        
        print(f"\n✅ Download complete!")
        print(f"   Downloaded {len(files)} files to: {args.output_dir}")
        if files:
            print(f"   Sample files:")
            for f in sorted(files)[:10]:
                print(f"      - {f.relative_to(output_path)}")
        return 0
    else:
        print(f"\n❌ Failed to download model from any PVC")
        print(f"\n💡 Possible reasons:")
        print(f"   1. Workspace PVC was deleted after job completion")
        print(f"   2. Model files were not stored in PVC")
        print(f"   3. Model may only be in DataStore (try download_model_from_datastore.py)")
        print(f"   4. Model may need to be exported manually from training pod before it's deleted")
        return 1


if __name__ == "__main__":
    sys.exit(main())
