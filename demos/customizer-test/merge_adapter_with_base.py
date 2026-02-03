#!/usr/bin/env python3
"""
Merge LoRA Adapter with Base Model

This script merges the LoRA adapter files from the customized model
with the base model to create a fully merged model for RHOAI SSR.

Usage:
    python merge_adapter_with_base.py \
        --adapter-dir ./downloaded_model \
        --base-model meta-llama/Llama-3.2-1B-Instruct \
        --output-dir ./merged_model

Or with HuggingFace token:
    export HF_TOKEN=your_token
    python merge_adapter_with_base.py \
        --adapter-dir ./downloaded_model \
        --base-model meta-llama/Llama-3.2-1B-Instruct \
        --output-dir ./merged_model
"""

import os
import sys
import argparse
from pathlib import Path

# Load environment variables from env.donotcommit if it exists
try:
    from dotenv import load_dotenv
    env_donotcommit_path = Path(__file__).parent / "env.donotcommit"
    if env_donotcommit_path.exists():
        load_dotenv(env_donotcommit_path, override=False)
except ImportError:
    pass


def merge_adapter_with_base(adapter_dir, base_model, output_dir, hf_token=None):
    """
    Merge LoRA adapter with base model.
    
    Args:
        adapter_dir: Directory containing adapter files (adapter_model.safetensors, adapter_config.json)
        base_model: Base model identifier (HuggingFace model ID or local path)
        output_dir: Output directory for merged model
        hf_token: HuggingFace token (optional, for gated models)
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("❌ Error: Required packages not installed")
        print("   Install with: pip install transformers peft accelerate safetensors")
        return False
    
    print("=" * 70)
    print("Merge LoRA Adapter with Base Model")
    print("=" * 70)
    print(f"Adapter Directory: {adapter_dir}")
    print(f"Base Model: {base_model}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Check adapter directory
    adapter_path = Path(adapter_dir)
    if not adapter_path.exists():
        print(f"❌ Error: Adapter directory does not exist: {adapter_dir}")
        return False
    
    adapter_config = adapter_path / "adapter_config.json"
    adapter_model = adapter_path / "adapter_model.safetensors"
    
    if not adapter_config.exists():
        print(f"❌ Error: adapter_config.json not found in {adapter_dir}")
        return False
    
    if not adapter_model.exists():
        print(f"❌ Error: adapter_model.safetensors not found in {adapter_dir}")
        return False
    
    print("✅ Adapter files found")
    print(f"   - {adapter_config}")
    print(f"   - {adapter_model}")
    print()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory created: {output_dir}")
    print()
    
    # Load base model
    print("📥 Loading base model...")
    print(f"   Model: {base_model}")
    
    try:
        # Set HuggingFace token if provided
        if hf_token:
            os.environ['HF_TOKEN'] = hf_token
            from huggingface_hub import login
            login(token=hf_token)
            print("   ✅ Authenticated with HuggingFace")
        
        # Load base model and tokenizer
        print("   Loading model weights...")
        base_model_obj = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
        
        print("   Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            base_model,
            trust_remote_code=True
        )
        
        print("✅ Base model loaded")
        print()
        
    except Exception as e:
        print(f"❌ Error loading base model: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check if base model name is correct")
        print("   2. For gated models, set HF_TOKEN environment variable")
        print("   3. Ensure you have internet access to download model")
        print("   4. Check HuggingFace model page for access requirements")
        return False
    
    # Load adapter
    print("📥 Loading LoRA adapter...")
    print(f"   Adapter: {adapter_dir}")
    
    try:
        # Load adapter using PEFT
        model = PeftModel.from_pretrained(
            base_model_obj,
            adapter_dir,
            device_map="auto"
        )
        print("✅ Adapter loaded")
        print()
        
    except Exception as e:
        print(f"❌ Error loading adapter: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check if adapter files are complete")
        print("   2. Verify adapter_config.json is valid")
        print("   3. Ensure adapter matches base model architecture")
        return False
    
    # Merge adapter with base model
    print("🔀 Merging adapter with base model...")
    print("   This may take a few minutes...")
    
    try:
        merged_model = model.merge_and_unload()
        print("✅ Merge complete")
        print()
        
    except Exception as e:
        print(f"❌ Error merging adapter: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Save merged model
    print("💾 Saving merged model...")
    print(f"   Output: {output_dir}")
    
    try:
        merged_model.save_pretrained(
            str(output_path),
            safe_serialization=True  # Use safetensors format
        )
        tokenizer.save_pretrained(str(output_path))
        print("✅ Merged model saved")
        print()
        
    except Exception as e:
        print(f"❌ Error saving merged model: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify output
    print("🔍 Verifying merged model files...")
    required_files = [
        "config.json",
        "model.safetensors",  # or model-*.safetensors for sharded models
        "tokenizer.json",
        "tokenizer_config.json"
    ]
    
    found_files = []
    for file in required_files:
        if (output_path / file).exists():
            found_files.append(file)
            file_size = (output_path / file).stat().st_size / (1024 * 1024)  # MB
            print(f"   ✅ {file} ({file_size:.1f} MB)")
        else:
            # Check for sharded models
            sharded = list(output_path.glob(f"model-*.safetensors"))
            if sharded and file == "model.safetensors":
                total_size = sum(f.stat().st_size for f in sharded) / (1024 * 1024)
                print(f"   ✅ model-*.safetensors ({len(sharded)} shards, {total_size:.1f} MB total)")
                found_files.append("model-*.safetensors")
            else:
                print(f"   ⚠️  {file} not found")
    
    if len(found_files) >= 3:  # At least config, model, and tokenizer
        print()
        print("=" * 70)
        print("✅ Merge Complete!")
        print("=" * 70)
        print(f"Merged model saved to: {output_dir}")
        print()
        print("📋 Next steps:")
        print(f"   1. Upload merged model to MinIO:")
        print(f"      python upload_model_to_minio.py --model-dir {output_dir} --target-path models/llama-3.2-1b-instruct-custom")
        print()
        print(f"   2. Update InferenceService path:")
        print(f"      oc patch inferenceservice anemo-rhoai-model-ssr -n anemo-rhoai \\")
        print(f"        --type='json' -p='[{{\"op\": \"replace\", \"path\": \"/spec/predictor/model/storage/path\", \"value\": \"models/llama-3.2-1b-instruct-custom\"}}]'")
        print()
        print(f"   3. Restart InferenceService pod:")
        print(f"      oc delete pod -n anemo-rhoai -l serving.kserve.io/inferenceservice=anemo-rhoai-model-ssr")
        return True
    else:
        print()
        print("⚠️  Warning: Some required files are missing")
        print("   The merged model may not be complete")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Merge LoRA adapter with base model for RHOAI SSR"
    )
    parser.add_argument(
        "--adapter-dir",
        type=str,
        required=True,
        help="Directory containing LoRA adapter files (adapter_model.safetensors, adapter_config.json)"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="meta-llama/Llama-3.2-1B-Instruct",
        help="Base model identifier (HuggingFace model ID or local path). Default: meta-llama/Llama-3.2-1B-Instruct"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./merged_model",
        help="Output directory for merged model (default: ./merged_model)"
    )
    parser.add_argument(
        "--hf-token",
        type=str,
        help="HuggingFace token (for gated models). Can also set HF_TOKEN environment variable"
    )
    
    args = parser.parse_args()
    
    # Get HF token from args, env var, or env.donotcommit
    hf_token = args.hf_token or os.getenv("HF_TOKEN")
    
    success = merge_adapter_with_base(
        args.adapter_dir,
        args.base_model,
        args.output_dir,
        hf_token
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
