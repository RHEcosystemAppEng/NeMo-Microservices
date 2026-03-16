#!/bin/bash
# Setup Port Forwards for Local Development
#
# This script sets up port-forwards to NeMo services so you can run
# the export scripts from your local machine.
#
# Usage:
#   ./setup_port_forwards.sh
#   ./setup_port_forwards.sh your-namespace
#   NAMESPACE=your-namespace ./setup_port_forwards.sh
#
# The port-forwards will run in the background. To stop them:
#   ./stop_port_forwards.sh
#   or
#   pkill -f "oc port-forward"

set -euo pipefail

# Parse namespace from argument or environment variable
NAMESPACE="${1:-${NAMESPACE:-your-namespace}}"

echo "=========================================="
echo "Setting up port-forwards for NeMo services"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo ""

# Check if oc is available
if ! command -v oc &> /dev/null; then
    echo "❌ Error: oc command not found"
    echo "   Please install OpenShift CLI (oc)"
    exit 1
fi

# Check if we're logged in
if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged in to OpenShift"
    echo "   Please run: oc login"
    exit 1
fi

# Check if namespace exists
if ! oc get namespace "$NAMESPACE" &> /dev/null; then
    echo "❌ Error: Namespace '$NAMESPACE' not found"
    exit 1
fi

# Kill existing port-forwards
echo "🧹 Cleaning up existing port-forwards..."
pkill -f "oc port-forward.*nemo" 2>/dev/null || true
pkill -f "oc port-forward.*minio" 2>/dev/null || true
sleep 2

# Port-forward mappings: "local_port:service_name:service_port"
# Using array format compatible with bash 3.2
PORT_FORWARDS=(
    "8001:nemodatastore-sample:8000"
    "8002:nemoentitystore-sample:8000"
    "8003:nemocustomizer-sample:8000"
)

# Store PIDs for cleanup
PIDS_FILE="/tmp/nemo_port_forwards_${NAMESPACE}.pids"
rm -f "$PIDS_FILE"
touch "$PIDS_FILE"

echo ""
echo "📡 Starting port-forwards..."
echo ""

# Start port-forwards in background
for FORWARD_SPEC in "${PORT_FORWARDS[@]}"; do
    LOCAL_PORT="${FORWARD_SPEC%%:*}"
    REST="${FORWARD_SPEC#*:}"
    SERVICE_NAME="${REST%%:*}"
    SERVICE_PORT="${REST#*:}"
    
    echo "   Forwarding $SERVICE_NAME: localhost:$LOCAL_PORT -> $SERVICE_PORT"
    
    # Check if service exists
    if ! oc get svc "$SERVICE_NAME" -n "$NAMESPACE" &> /dev/null; then
        echo "   ⚠️  Service '$SERVICE_NAME' not found in namespace '$NAMESPACE'"
        continue
    fi
    
    # Start port-forward in background
    oc port-forward -n "$NAMESPACE" "svc/$SERVICE_NAME" "$LOCAL_PORT:$SERVICE_PORT" > /dev/null 2>&1 &
    PF_PID=$!
    
    # Save PID to file
    echo "$PF_PID" >> "$PIDS_FILE"
    
    # Wait a moment and verify it's still running
    sleep 2
    if kill -0 "$PF_PID" 2>/dev/null; then
        echo "   ✅ Port-forward started (PID: $PF_PID)"
    else
        echo "   ❌ Port-forward failed to start"
        # Check if port is already in use
        if lsof -ti:$LOCAL_PORT &> /dev/null; then
            echo "      Port $LOCAL_PORT is already in use"
            echo "      Kill existing process: lsof -ti:$LOCAL_PORT | xargs kill"
        fi
    fi
done

# MinIO API (9000) and web console (9001)
if oc get svc nemo-infra-minio -n "$NAMESPACE" &> /dev/null; then
    echo "   Forwarding nemo-infra-minio (MinIO API): localhost:9000 -> 80"
    oc port-forward -n "$NAMESPACE" svc/nemo-infra-minio 9000:80 > /dev/null 2>&1 &
    PF_PID=$!
    echo "$PF_PID" >> "$PIDS_FILE"
    sleep 2
    if kill -0 "$PF_PID" 2>/dev/null; then
        echo "   ✅ MinIO API port-forward started (localhost:9000)"
    else
        echo "   ⚠️  MinIO API port-forward failed"
    fi
fi
# MinIO web console: embedded in main MinIO pod on port 9001 (no separate console image)
MINIO_POD=$(oc get pods -n "$NAMESPACE" -l app.kubernetes.io/name=minio -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [ -n "$MINIO_POD" ]; then
    echo "   Forwarding MinIO console: localhost:9001 -> $MINIO_POD:9001"
    oc port-forward -n "$NAMESPACE" "pod/$MINIO_POD" 9001:9001 > /dev/null 2>&1 &
    echo "$!" >> "$PIDS_FILE"
    sleep 1
    echo "   ✅ MinIO console (http://localhost:9001)"
fi

echo ""
echo "✅ Port-forwards setup complete!"
echo ""
echo "Service URLs:"
echo "  - DataStore:    http://localhost:8001"
echo "  - Entity Store: http://localhost:8002"
echo "  - Customizer:   http://localhost:8003"
echo "  - MinIO API:    http://localhost:9000 (set MINIO_ENDPOINT for upload script)"
echo "  - MinIO console: http://localhost:9001"
echo ""
echo "Environment variables (add to your shell or env.donotcommit):"
echo "  export DATASTORE_URL=http://localhost:8001"
echo "  export ENTITY_STORE_URL=http://localhost:8002"
echo "  export CUSTOMIZER_URL=http://localhost:8003"
echo ""
echo "To stop port-forwards:"
echo "  pkill -f 'oc port-forward'"
echo "  or"
echo "  ./stop_port_forwards.sh"
echo ""
echo "Note: Port-forwards are running in the background."
echo "      Keep this terminal open or run in a separate terminal."
echo ""
echo "PID file: $PIDS_FILE"
