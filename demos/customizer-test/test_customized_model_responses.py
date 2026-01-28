#!/usr/bin/env python3
"""
Test Customized Model Responses

This script tests the customized model deployed to RHOAI SSR and displays
the responses to verify customization is working.

Usage:
    python test_customized_model_responses.py
"""

import os
import sys
import json
import requests
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

# Configuration
NMS_NAMESPACE = os.getenv("NMS_NAMESPACE", "anemo-rhoai")
INFERENCE_SERVICE_URL = os.getenv("INFERENCE_SERVICE_URL", "")
INFERENCE_SERVICE_NAME = os.getenv("INFERENCE_SERVICE_NAME", "anemo-rhoai-model-ssr")
NIM_SERVICE_ACCOUNT_TOKEN = os.getenv("NIM_SERVICE_ACCOUNT_TOKEN", "")


def test_model(prompts, model_name, url, token=None):
    """Test model with given prompts."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    headers = {
        "Content-Type": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    responses = {}
    
    print(f"\n📝 Testing model: {model_name}")
    print(f"   URL: {url}")
    print("=" * 70)
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] Prompt: {prompt}")
        print("-" * 70)
        
        try:
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
                verify=False
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    response_text = result['choices'][0]['message']['content']
                    responses[prompt] = response_text
                    print(f"✅ Response ({len(response_text)} chars):")
                    print(f"\n{response_text}\n")
                else:
                    print(f"⚠️  Unexpected response format: {result}")
                    responses[prompt] = None
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text[:200]}")
                responses[prompt] = None
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            responses[prompt] = None
    
    return responses


def detect_working_url_and_model():
    """Detect working InferenceService URL and model name."""
    if not INFERENCE_SERVICE_URL:
        print("❌ INFERENCE_SERVICE_URL not set in env.donotcommit")
        return None, None
    
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    headers = {
        "Content-Type": "application/json"
    }
    if NIM_SERVICE_ACCOUNT_TOKEN:
        headers["Authorization"] = f"Bearer {NIM_SERVICE_ACCOUNT_TOKEN}"
    
    # Try different URLs
    potential_urls = [INFERENCE_SERVICE_URL]
    if INFERENCE_SERVICE_NAME:
        if INFERENCE_SERVICE_URL.startswith('https://'):
            internal_url = f"https://{INFERENCE_SERVICE_NAME}-predictor.{NMS_NAMESPACE}.svc.cluster.local:8443"
        else:
            internal_url = f"http://{INFERENCE_SERVICE_NAME}-predictor.{NMS_NAMESPACE}.svc.cluster.local:80"
        potential_urls.append(internal_url)
    
    # Try different model names
    model_names_to_try = []
    if INFERENCE_SERVICE_NAME:
        model_names_to_try.append(INFERENCE_SERVICE_NAME)
    # Also try variations
    model_names_to_try.append("anemo-rhoai-model-ssr")
    model_names_to_try = list(dict.fromkeys(model_names_to_try))
    
    print("🔍 Detecting working InferenceService URL and model name...")
    
    for test_url in potential_urls:
        for model_name in model_names_to_try:
            try:
                test_payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 5
                }
                response = requests.post(
                    f"{test_url}/v1/chat/completions",
                    headers=headers,
                    json=test_payload,
                    timeout=10,
                    verify=False
                )
                if response.status_code == 200:
                    print(f"✅ Found working URL: {test_url}")
                    print(f"✅ Working model name: {model_name}")
                    return test_url, model_name
            except Exception as e:
                continue
    
    print("❌ Could not detect working URL/model name")
    return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Test customized model responses from RHOAI SSR"
    )
    parser.add_argument(
        "--prompts",
        type=str,
        nargs="+",
        default=[
            "What personal data does Red Hat collect?",
            "How does Red Hat use my personal data?",
            "What are my privacy rights with Red Hat?",
            "Does Red Hat share my personal data with third parties?"
        ],
        help="Test prompts (default: ML-related prompts)"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="InferenceService URL (overrides env.donotcommit)"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        help="Model name (overrides auto-detection)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Test Customized Model Responses")
    print("=" * 70)
    print(f"Namespace: {NMS_NAMESPACE}")
    print(f"Test Prompts: {len(args.prompts)}")
    
    # Get URL and model name
    if args.url and args.model_name:
        working_url = args.url
        working_model_name = args.model_name
        print(f"Using provided URL: {working_url}")
        print(f"Using provided model name: {working_model_name}")
    else:
        working_url, working_model_name = detect_working_url_and_model()
        if not working_url or not working_model_name:
            print("\n❌ Could not detect working URL/model name")
            print("\n💡 Options:")
            print("   1. Set INFERENCE_SERVICE_URL in env.donotcommit")
            print("   2. Use --url and --model-name arguments")
            print("   3. Check if InferenceService is running:")
            print(f"      oc get inferenceservice {INFERENCE_SERVICE_NAME} -n {NMS_NAMESPACE}")
            return 1
    
    # Test the model
    responses = test_model(
        args.prompts,
        working_model_name,
        working_url,
        NIM_SERVICE_ACCOUNT_TOKEN
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    successful = sum(1 for v in responses.values() if v is not None)
    print(f"✅ Successful responses: {successful}/{len(args.prompts)}")
    
    if successful > 0:
        print("\n✅ Customized model is responding!")
        print("\n💡 Next steps:")
        print("   - Review responses above to verify customization")
        print("   - Compare with base model responses (if available)")
        print("   - Look for differences in style, detail, or accuracy")
        return 0
    else:
        print("\n❌ No successful responses")
        print("\n💡 Troubleshooting:")
        print("   1. Check if InferenceService pod is ready:")
        print(f"      oc get pods -n {NMS_NAMESPACE} -l serving.kserve.io/inferenceservice={INFERENCE_SERVICE_NAME}")
        print("   2. Check pod logs:")
        print(f"      oc logs -n {NMS_NAMESPACE} -l serving.kserve.io/inferenceservice={INFERENCE_SERVICE_NAME} --tail=50")
        return 1


if __name__ == "__main__":
    sys.exit(main())
