#!/bin/bash

################################################################################
# NeMo Microservices Installation Script
# This script automates the installation of NeMo infrastructure and instances
#
# All CRD adoption, resource patching, and SCC binding is now handled by
# Helm hooks automatically. This script just:
# 1. Checks prerequisites
# 2. Loads configuration from .env
# 3. Creates namespace and NGC secrets
# 4. Runs helm install commands
# 5. Verifies installation
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if oc CLI is installed
    if ! command -v oc &> /dev/null; then
        log_error "oc CLI not found. Please install OpenShift CLI."
        exit 1
    fi

    # Check if helm CLI is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm CLI not found. Please install Helm."
        exit 1
    fi

    # Check if logged into OpenShift
    if ! oc whoami &> /dev/null; then
        log_error "Not logged into OpenShift. Please run 'oc login' first."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Function to load variables from .env file
load_env_variables() {
    log_info "Loading configuration from .env file..."

    # Look for .env file in NeMo-Microservices repo root
    ENV_FILE="$NEMO_MS_DIR/.env"

    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env file not found at $ENV_FILE"
        log_error "Please create a .env file in the NeMo-Microservices root with the following variables:"
        log_error "  NGC_API_KEY=\"your-ngc-api-key\""
        log_error "  NVIDIA_API_KEY=\"your-nvidia-api-key\""
        log_error "  HF_TOKEN=\"your-hf-token\""
        log_error "  NAMESPACE=\"your-namespace\""
        exit 1
    fi

    # Source the .env file
    set -a  # automatically export all variables
    source "$ENV_FILE"
    set +a

    # Validate required variables
    if [ -z "$NGC_API_KEY" ]; then
        log_error "NGC_API_KEY is not set in .env file"
        exit 1
    fi

    if [ -z "$NVIDIA_API_KEY" ]; then
        log_error "NVIDIA_API_KEY is not set in .env file"
        log_error "Generate one at: https://build.nvidia.com"
        exit 1
    fi

    if [ -z "$HF_TOKEN" ]; then
        log_error "HF_TOKEN is not set in .env file"
        log_error "Generate one at: https://huggingface.co/settings/tokens"
        exit 1
    fi

    if [ -z "$NAMESPACE" ]; then
        log_error "NAMESPACE is not set in .env file"
        exit 1
    fi

    log_success "Configuration loaded from .env"
}

# Function to create or verify namespace
create_namespace() {
    log_info "Creating/verifying namespace: $NAMESPACE"

    if oc get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace $NAMESPACE already exists"
    else
        oc new-project "$NAMESPACE"
        log_success "Namespace $NAMESPACE created"
    fi

    # Switch to namespace
    oc project "$NAMESPACE"
}

# Function to create all required secrets for NeMo and Data Flywheel
create_secrets() {
    log_info "Creating secrets for NeMo Microservices and Data Flywheel..."

    # Delete existing secrets if they exist
    oc delete secret nvcrimagepullsecret ngc-api nvidia-api hf-secret \
        -n "$NAMESPACE" --ignore-not-found=true

    # Create NGC Image Pull Secret (for nvcr.io registry)
    oc create secret docker-registry nvcrimagepullsecret \
        --docker-server=nvcr.io \
        --docker-username='$oauthtoken' \
        --docker-password="$NGC_API_KEY" \
        -n "$NAMESPACE"

    # Create NGC API Secret (for NeMo model access)
    oc create secret generic ngc-api \
        --from-literal=NGC_API_KEY="$NGC_API_KEY" \
        -n "$NAMESPACE"

    # Create NVIDIA API Secret (for remote LLM judge and NVIDIA API catalog)
    oc create secret generic nvidia-api \
        --from-literal=NVIDIA_API_KEY="$NVIDIA_API_KEY" \
        -n "$NAMESPACE"

    # Create Hugging Face Token Secret (for HF model/dataset access)
    oc create secret generic hf-secret \
        --from-literal=HF_TOKEN="$HF_TOKEN" \
        -n "$NAMESPACE"

    log_success "All secrets created successfully (compatible with Data Flywheel)"
}

# Function to install nemo-infra
install_nemo_infra() {
    log_info "Installing nemo-infra..."

    # Navigate to nemo-infra deploy directory
    if [ ! -d "$NEMO_MS_DIR/deploy/nemo-infra" ]; then
        log_error "nemo-infra directory not found at $NEMO_MS_DIR/deploy/nemo-infra"
        exit 1
    fi

    cd "$NEMO_MS_DIR/deploy/nemo-infra"

    # Check if nemo-infra release already exists with failed status
    if helm list -n "$NAMESPACE" | grep "nemo-infra" | grep -q "failed"; then
        log_warn "Existing nemo-infra release found in failed state. Uninstalling..."
        helm uninstall nemo-infra -n "$NAMESPACE" || log_warn "Failed to uninstall nemo-infra"
        sleep 5  # Give time for resources to clean up
    elif helm list -n "$NAMESPACE" | grep -q "nemo-infra"; then
        log_info "nemo-infra release already exists and is deployed. Skipping installation."
        return 0
    fi

    # Check that values.yaml exists (standard Helm pattern)
    if [ ! -f "values.yaml" ]; then
        log_error "values.yaml not found in $NEMO_MS_DIR/deploy/nemo-infra"
        log_error "Please ensure NeMo-Microservices is up to date"
        exit 1
    fi

    log_info "Using values.yaml for nemo-infra configuration"

    # Update namespace in values.yaml to match .env
    log_info "Setting namespace to $NAMESPACE in values.yaml..."
    sed -i.bak "s/name: .*/name: $NAMESPACE/g" values.yaml
    rm -f values.yaml.bak
    log_success "Namespace updated in values.yaml"

    # Update Helm dependencies (force rebuild to pick up values changes)
    log_info "Updating Helm dependencies for nemo-infra..."
    rm -rf charts/*.tgz Chart.lock 2>/dev/null || true
    helm dependency update

    # Install nemo-infra
    # Note: Helm hooks will automatically:
    #   - Adopt existing Argo/Volcano CRDs (pre-install hook)
    #   - Adopt existing cluster resources (pre-install hook)
    #   - Bind SCC to service accounts (post-install hook)
    log_info "Installing nemo-infra Helm chart..."
    log_info "Helm pre-install hooks will handle CRD and resource adoption"
    helm install nemo-infra . -n "$NAMESPACE" \
        --create-namespace \
        -f values.yaml

    log_success "nemo-infra installed"

    # Wait for infrastructure to be ready
    log_info "Waiting for nemo-infra pods to be ready (this may take a few minutes)..."
    oc wait --for=condition=ready pod -l app.kubernetes.io/instance=nemo-infra \
        -n "$NAMESPACE" --timeout=300s || log_warn "Some infrastructure pods may still be starting"

    log_success "nemo-infra is ready"
}

# Function to install nemo-instances
install_nemo_instances() {
    log_info "Installing nemo-instances with chat model..."

    # Navigate to nemo-instances deploy directory
    if [ ! -d "$NEMO_MS_DIR/deploy/nemo-instances" ]; then
        log_error "nemo-instances directory not found at $NEMO_MS_DIR/deploy/nemo-instances"
        exit 1
    fi

    cd "$NEMO_MS_DIR/deploy/nemo-instances"

    # Check if nemo-instances release already exists with failed status
    if helm list -n "$NAMESPACE" | grep "nemo-instances" | grep -q "failed"; then
        log_warn "Existing nemo-instances release found in failed state. Uninstalling..."
        helm uninstall nemo-instances -n "$NAMESPACE" || log_warn "Failed to uninstall nemo-instances"
        sleep 5  # Give time for resources to clean up
    elif helm list -n "$NAMESPACE" | grep -q "nemo-instances"; then
        log_info "nemo-instances release already exists and is deployed. Skipping installation."
        return 0
    fi

    # Check that values.yaml exists (standard Helm pattern)
    if [ ! -f "values.yaml" ]; then
        log_error "values.yaml not found in $NEMO_MS_DIR/deploy/nemo-instances"
        log_error "Please ensure NeMo-Microservices is up to date"
        exit 1
    fi

    log_info "Using values.yaml for nemo-instances configuration"

    # Update namespace in values.yaml to match .env
    log_info "Setting namespace to $NAMESPACE in values.yaml..."
    sed -i.bak "s/name: .*/name: $NAMESPACE/g" values.yaml
    rm -f values.yaml.bak
    log_success "Namespace updated in values.yaml"

    # Update Helm dependencies (force rebuild to pick up nim-operator subchart)
    log_info "Updating Helm dependencies for nemo-instances..."
    rm -rf charts/*.tgz Chart.lock 2>/dev/null || true
    helm dependency update

    # Install nemo-instances (LlamaStack disabled initially, Gateway enabled)
    # Note: Helm hooks will automatically:
    #   - Validate configuration (pre-install hook)
    #   - Adopt existing cluster resources (pre-install hook)
    #   - Patch evaluator deployment for EVALUATOR_IMAGE (post-install hook)
    #   - Bind customizer SA to SCC (post-install hook)
    log_info "Installing nemo-instances Helm chart with NeMo Gateway..."
    log_info "Helm pre/post-install hooks will handle:"
    log_info "  - Configuration validation"
    log_info "  - Resource adoption"
    log_info "  - Evaluator init container patching"
    log_info "  - SCC binding for customizer"
    helm install nemo-instances . -n "$NAMESPACE" \
        -f values.yaml \
        --set llamastack.enabled=false \
        --set gateway.enabled=true

    log_success "nemo-instances installed"

    # Note: Model downloader jobs are created dynamically by the NeMo Operator when customizer starts
    # Jobs appear as: model-downloader-<model-name>
    # If no jobs appear after a few minutes, check:
    #   1. NeMo Operator logs: oc logs -n $NAMESPACE deployment/nemo-operator-controller-manager
    #   2. Customizer pod logs: oc logs -n $NAMESPACE deployment/nemocustomizer-sample
    #   3. Restart customizer if needed: oc rollout restart deployment/nemocustomizer-sample -n $NAMESPACE
    log_info "Model downloader jobs will be created by NeMo Operator when customizer pod starts"

    # Wait for services to be ready
    log_info "Waiting for NeMo services to be ready (this may take several minutes)..."
    sleep 30  # Give pods time to start

    log_info "Checking NeMo service status..."
    oc get pods -n "$NAMESPACE" | grep -E "nemo(datastore|entitystore|customizer|evaluator|guardrail|gateway)|llama3-1b|embedqa"

    log_success "nemo-instances with gateway is ready"
}

# Function to verify installation
verify_installation() {
    log_info "Verifying installation..."

    echo ""
    log_info "=== Helm Releases ==="
    helm list -n "$NAMESPACE"

    echo ""
    log_info "=== Custom Resources ==="
    oc get nemodatastore,nemoentitystore,nemocustomizer,nemoevaluator,nemoguardrail,nimcache,nimpipeline -n "$NAMESPACE"

    echo ""
    log_info "=== Services ==="
    oc get svc -n "$NAMESPACE" | grep -E "nemo|llama|embedqa"

    echo ""
    log_info "=== Pods ==="
    oc get pods -n "$NAMESPACE"

    log_success "Installation verification complete"
}

# Function to display next steps
display_next_steps() {
    echo ""
    log_success "==================================================================="
    log_success "NeMo Microservices Installation Complete!"
    log_success "==================================================================="
    echo ""
    log_info "Installed components:"
    echo "  ✅ NeMo Infrastructure (nemo-infra)"
    echo "  ✅ NeMo Services (customizer, datastore, entitystore, evaluator, guardrails)"
    echo "  ✅ Chat Model NIM: meta-llama3-1b-instruct"
    echo "  ✅ NeMo Gateway (unified API endpoint)"
    echo ""
    log_info "Shared secrets created (compatible with Data Flywheel):"
    echo "  ✅ nvcrimagepullsecret (Docker registry auth)"
    echo "  ✅ ngc-api (NGC API Key)"
    echo "  ✅ nvidia-api (NVIDIA API Key)"
    echo "  ✅ hf-secret (Hugging Face Token)"
    echo ""
    log_info "Service URLs (cluster-internal):"
    echo "  • Gateway:        http://nemo-gateway.$NAMESPACE.svc.cluster.local (unified endpoint)"
    echo "  • Chat Model:     http://meta-llama3-1b-instruct.$NAMESPACE.svc.cluster.local:8000"
    echo "  • Data Store:     http://nemodatastore-sample.$NAMESPACE.svc.cluster.local:8000"
    echo "  • Entity Store:   http://nemoentitystore-sample.$NAMESPACE.svc.cluster.local:8000"
    echo "  • Customizer:     http://nemocustomizer-sample.$NAMESPACE.svc.cluster.local:8000"
    echo "  • Evaluator:      http://nemoevaluator-sample.$NAMESPACE.svc.cluster.local:8000"
    echo "  • Guardrails:     http://nemoguardrails-sample.$NAMESPACE.svc.cluster.local:8000"
    echo ""
    log_info "Optional Models (disabled by default):"
    echo "  To enable embedding model: helm upgrade nemo-instances deploy/nemo-instances -n $NAMESPACE --set deployEmbeddingModel=true"
    echo "  To enable retriever model: helm upgrade nemo-instances deploy/nemo-instances -n $NAMESPACE --set deployRetrieverModel=true"
    echo ""
    log_info "Gateway Usage:"
    echo "  Access all NeMo services through the unified gateway endpoint:"
    echo "    http://nemo-gateway.$NAMESPACE.svc.cluster.local"
    echo ""
    log_info "Ready to deploy NVIDIA Data Flywheel:"
    echo "  The secrets required by Data Flywheel have been created."
    echo "  Configure Data Flywheel to use the gateway:"
    echo "    nemo_base_url: http://nemo-gateway"
    echo "    datastore_base_url: http://nemo-gateway"
    echo ""
    log_info "For manual installation (without this script):"
    echo "  1. Create namespace and secrets"
    echo "  2. helm install nemo-infra deploy/nemo-infra -n $NAMESPACE -f deploy/nemo-infra/values.yaml"
    echo "  3. helm install nemo-instances deploy/nemo-instances -n $NAMESPACE -f deploy/nemo-instances/values.yaml --set llamastack.enabled=false --set gateway.enabled=true"
    echo ""
}

################################################################################
# Main Script
################################################################################

main() {
    # Get script directory (this is the NeMo-Microservices repo root)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # This script is now in the NeMo-Microservices repo root
    NEMO_MS_DIR="$SCRIPT_DIR"

    log_info "Starting NeMo Microservices Installation"
    log_info "NeMo-Microservices directory: $NEMO_MS_DIR"
    echo ""

    # Check prerequisites
    check_prerequisites

    # Load variables from .env
    load_env_variables

    echo ""
    log_info "Installation Configuration:"
    log_info "  Namespace: $NAMESPACE"
    log_info "  NGC API Key: ${NGC_API_KEY:0:10}... (hidden)"
    echo ""

    read -p "Proceed with installation? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Installation cancelled"
        exit 0
    fi

    echo ""
    log_info "Starting installation..."
    echo ""

    # Execute installation steps
    create_namespace
    create_secrets
    install_nemo_infra
    install_nemo_instances
    verify_installation
    display_next_steps
}

# Run main function
main "$@"
