#!/bin/bash
# Stop Port Forwards for NeMo Services
#
# This script stops all port-forwards started by setup_port_forwards.sh
#
# Usage:
#   ./stop_port_forwards.sh

set -euo pipefail

NAMESPACE="${1:-${NAMESPACE:-your-namespace}}"
PIDS_FILE="/tmp/nemo_port_forwards_${NAMESPACE}.pids"

echo "=========================================="
echo "Stopping port-forwards for NeMo services"
echo "=========================================="
echo "Namespace: $NAMESPACE"
echo ""

# Kill port-forwards by PID file if it exists
if [ -f "$PIDS_FILE" ]; then
    echo "📋 Stopping port-forwards from PID file..."
    while IFS= read -r pid; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "   Stopping PID: $pid"
            kill "$pid" 2>/dev/null || true
        fi
    done < "$PIDS_FILE"
    rm -f "$PIDS_FILE"
    echo "✅ PID file cleaned up"
fi

# Also kill any remaining oc port-forward processes for nemo and minio
echo ""
echo "🧹 Cleaning up any remaining port-forwards..."
pkill -f "oc port-forward.*nemo" 2>/dev/null || true
pkill -f "oc port-forward.*minio" 2>/dev/null || true

echo ""
echo "✅ All port-forwards stopped"
