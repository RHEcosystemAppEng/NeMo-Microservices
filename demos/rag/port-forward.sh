#!/bin/bash
# Port-forward script for RAG tutorial
# Run this script to set up port-forwards for local development
# This script monitors and auto-restarts port-forwards if they die

NAMESPACE=${NMS_NAMESPACE:-anemo-rhoai}
PID_FILE="/tmp/rag-port-forwards.pid"
LOG_FILE="/tmp/rag-port-forwards.log"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping all port-forwards..."
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            kill $pid 2>/dev/null
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    pkill -f "oc port-forward.*nemodatastore" 2>/dev/null
    pkill -f "oc port-forward.*nemoentitystore" 2>/dev/null
    pkill -f "oc port-forward.*nemoguardrails" 2>/dev/null
    pkill -f "oc port-forward.*meta-llama3" 2>/dev/null
    pkill -f "oc port-forward.*nv-embedqa" 2>/dev/null
    pkill -f "oc port-forward.*llamastack" 2>/dev/null
    echo "✅ All port-forwards stopped"
    exit 0
}

trap cleanup INT TERM

# Function to start a port-forward with monitoring
start_port_forward() {
    local PORT=$1
    local SERVICE=$2
    local NAME=$3
    
    # Check if port is already in use
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $PORT is already in use. Skipping $NAME..."
        return 1
    fi
    
    echo "📡 Starting port-forward for $NAME (port $PORT)..."
    
    # Start port-forward in background
    oc port-forward -n $NAMESPACE svc/$SERVICE $PORT:8000 >> "$LOG_FILE" 2>&1 &
    local PF_PID=$!
    echo $PF_PID >> "$PID_FILE"
    
    # Wait a moment to check if it started successfully
    sleep 1
    if ! kill -0 $PF_PID 2>/dev/null; then
        echo "❌ Failed to start port-forward for $NAME"
        return 1
    fi
    
    echo "✅ $NAME port-forward started (PID: $PF_PID)"
    return 0
}

# Function to monitor and restart port-forwards
monitor_port_forwards() {
    while true; do
        sleep 5
        if [ -f "$PID_FILE" ]; then
            while read pid; do
                if ! kill -0 $pid 2>/dev/null; then
                    echo "⚠️  Port-forward process $pid died. Check $LOG_FILE for details."
                    echo "   You may need to restart this script."
                fi
            done < "$PID_FILE"
        fi
    done
}

# Clean up any existing port-forwards
echo "Cleaning up any existing port-forwards..."
pkill -f "oc port-forward.*nemodatastore" 2>/dev/null
pkill -f "oc port-forward.*nemoentitystore" 2>/dev/null
pkill -f "oc port-forward.*nemoguardrails" 2>/dev/null
pkill -f "oc port-forward.*meta-llama3" 2>/dev/null
pkill -f "oc port-forward.*nv-embedqa" 2>/dev/null
pkill -f "oc port-forward.*llamastack" 2>/dev/null
sleep 1

# Initialize PID file
rm -f "$PID_FILE"
touch "$PID_FILE"

echo "Setting up port-forwards for NeMo Microservices in namespace: $NAMESPACE"
echo "Log file: $LOG_FILE"
echo "Press Ctrl+C to stop all port-forwards"
echo ""

# Start port-forwards
start_port_forward 8001 "nemodatastore-sample" "Data Store"
start_port_forward 8002 "nemoentitystore-sample" "Entity Store"
start_port_forward 8005 "nemoguardrails-sample" "Guardrails"
start_port_forward 8006 "meta-llama3-1b-instruct" "Chat NIM"
start_port_forward 8007 "nv-embedqa-1b-v2" "Embedding NIM"
# LlamaStack uses port 8321, not 8000
echo "📡 Starting port-forward for LlamaStack (port 8321)..."
oc port-forward -n $NAMESPACE svc/llamastack 8321:8321 >> "$LOG_FILE" 2>&1 &
LLAMASTACK_PID=$!
echo $LLAMASTACK_PID >> "$PID_FILE"
sleep 1
if kill -0 $LLAMASTACK_PID 2>/dev/null; then
    echo "✅ LlamaStack port-forward started (PID: $LLAMASTACK_PID)"
else
    echo "❌ Failed to start port-forward for LlamaStack"
fi

echo ""
echo "✅ All port-forwards started"
echo "PIDs saved to: $PID_FILE"
echo ""
echo "⚠️  Note: Port-forwards can be unreliable. For better reliability:"
echo "   1. Run the notebook inside the cluster (recommended)"
echo "   2. Or use a tool like 'kubectl port-forward' in separate terminals"
echo ""
echo "Monitoring port-forwards... (Press Ctrl+C to stop)"

# Start monitoring in background
monitor_port_forwards &
MONITOR_PID=$!

# Wait for interrupt
wait
