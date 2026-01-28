# Steps to Merge LoRA Adapter with Base Model

This guide shows how to merge the customized LoRA adapter with the base model to create a fully merged model for RHOAI SSR.

## Prerequisites

1. **Python packages**:
   ```bash
   pip install transformers peft accelerate safetensors torch
   ```

2. **HuggingFace token** (for gated models like Llama):
   - Get token from: https://huggingface.co/settings/tokens
   - Set in `env.donotcommit` as `HF_TOKEN=your_token`
   - Or export: `export HF_TOKEN=your_token`

3. **Adapter files** (already downloaded):
   - `downloaded_model/adapter_model.safetensors`
   - `downloaded_model/adapter_config.json`
   - Tokenizer files

## Method 1: Using the Merge Script (Recommended)

### Step 1: Run the merge script

```bash
cd NeMo-Microservices/demos/customizer-test

# Using default base model (meta-llama/Llama-3.2-1B-Instruct)
python merge_adapter_with_base.py \
    --adapter-dir ./downloaded_model \
    --output-dir ./merged_model

# Or specify base model explicitly
python merge_adapter_with_base.py \
    --adapter-dir ./downloaded_model \
    --base-model meta-llama/Llama-3.2-1B-Instruct \
    --output-dir ./merged_model

# If base model is gated, provide HF token
python merge_adapter_with_base.py \
    --adapter-dir ./downloaded_model \
    --base-model meta-llama/Llama-3.2-1B-Instruct \
    --output-dir ./merged_model \
    --hf-token $(grep HF_TOKEN env.donotcommit | cut -d'=' -f2)
```

### Step 2: Verify merged model

```bash
ls -lh merged_model/
# Should see:
# - config.json
# - model.safetensors (or model-*.safetensors for sharded)
# - tokenizer.json
# - tokenizer_config.json
# - special_tokens_map.json
```

### Step 3: Check model size

```bash
du -sh merged_model/
# Should be ~2.4GB (similar to base model size)
```

---

## Method 2: Manual Python Script

If you prefer to run the merge manually:

### Step 1: Create merge script

Create a file `manual_merge.py`:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os

# Configuration
ADAPTER_DIR = "./downloaded_model"
BASE_MODEL = "meta-llama/Llama-3.2-1B-Instruct"
OUTPUT_DIR = "./merged_model"
HF_TOKEN = os.getenv("HF_TOKEN")  # From env.donotcommit or export

# Authenticate with HuggingFace (if needed)
if HF_TOKEN:
    from huggingface_hub import login
    login(token=HF_TOKEN)

# Load base model
print("Loading base model...")
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype="auto",
    device_map="auto",
    trust_remote_code=True
)
tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    trust_remote_code=True
)

# Load adapter
print("Loading LoRA adapter...")
model = PeftModel.from_pretrained(
    base_model,
    ADAPTER_DIR,
    device_map="auto"
)

# Merge
print("Merging adapter with base model...")
merged_model = model.merge_and_unload()

# Save
print("Saving merged model...")
merged_model.save_pretrained(OUTPUT_DIR, safe_serialization=True)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"✅ Merged model saved to {OUTPUT_DIR}")
```

### Step 2: Run the script

```bash
python manual_merge.py
```

---

## Method 3: Using Jupyter Notebook

You can also run the merge in a Jupyter notebook:

```python
# In a notebook cell
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv("env.donotcommit")

# Configuration
adapter_dir = "./downloaded_model"
base_model = "meta-llama/Llama-3.2-1B-Instruct"
output_dir = "./merged_model"
hf_token = os.getenv("HF_TOKEN")

# Authenticate (if needed)
if hf_token:
    from huggingface_hub import login
    login(token=hf_token)

# Load base model
print("Loading base model...")
base = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(base_model)

# Load adapter
print("Loading adapter...")
model = PeftModel.from_pretrained(base, adapter_dir)

# Merge
print("Merging...")
merged = model.merge_and_unload()

# Save
print("Saving...")
merged.save_pretrained(output_dir, safe_serialization=True)
tokenizer.save_pretrained(output_dir)

print(f"✅ Done! Merged model in {output_dir}")
```

---

## Troubleshooting

### Error: "Model not found" or "401 Unauthorized"

**Solution**: Set HuggingFace token:
```bash
export HF_TOKEN=your_token
# Or add to env.donotcommit: HF_TOKEN=your_token
```

### Error: "CUDA out of memory"

**Solution**: Use CPU or reduce memory:
```python
# Use CPU instead of GPU
base_model = AutoModelForCausalLM.from_pretrained(
    base_model,
    torch_dtype="auto",
    device_map="cpu"  # Use CPU
)
```

### Error: "adapter_config.json not found"

**Solution**: Verify adapter directory:
```bash
ls -la downloaded_model/
# Should see:
# - adapter_config.json
# - adapter_model.safetensors
```

### Error: "Base model architecture mismatch"

**Solution**: Verify base model matches adapter:
- Check `adapter_config.json` for `base_model_name_or_path`
- Ensure you're using the correct base model version

---

## Expected Output

After successful merge, you should see:

```
✅ Adapter files found
✅ Base model loaded
✅ Adapter loaded
✅ Merge complete
✅ Merged model saved

🔍 Verifying merged model files...
   ✅ config.json (0.0 MB)
   ✅ model.safetensors (2300.0 MB)
   ✅ tokenizer.json (8.7 MB)
   ✅ tokenizer_config.json (0.1 MB)

✅ Merge Complete!
Merged model saved to: ./merged_model
```

---

## Next Steps

After merging:

1. **Upload to MinIO**:
   ```bash
   python upload_model_to_minio.py \
       --model-dir ./merged_model \
       --target-path models/llama-3.2-1b-instruct-custom
   ```

2. **Update InferenceService**:
   ```bash
   oc patch inferenceservice anemo-rhoai-model-ssr -n anemo-rhoai \
     --type='json' -p='[{"op": "replace", "path": "/spec/predictor/model/storage/path", "value": "models/llama-3.2-1b-instruct-custom"}]'
   ```

3. **Restart pod**:
   ```bash
   oc delete pod -n anemo-rhoai -l serving.kserve.io/inferenceservice=anemo-rhoai-model-ssr
   ```

4. **Test with notebook**:
   - Run `test-customized-model.ipynb`
   - Verify customized responses

---

## Notes

- **Merging time**: ~5-10 minutes depending on hardware
- **Disk space**: Need ~5GB free (2.4GB base + 2.4GB merged + temp)
- **Memory**: Need ~8GB RAM minimum (16GB recommended)
- **GPU**: Optional but speeds up loading (not required for merge)
