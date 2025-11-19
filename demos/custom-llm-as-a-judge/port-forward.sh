#!/bin/bash
# Port-forward script for Custom LLM-as-a-Judge tutorial
# Run this script to set up port-forwards for local development

NAMESPACE=${NMS_NAMESPACE:-anemo-rhoai}

echo "Setting up port-forwards for NeMo Microservices in namespace: $NAMESPACE"
echo "Press Ctrl+C to stop all port-forwards"
echo ""

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $1 is already in use. Skipping..."
        return 1
    fi
    return 0
}

# Start port-forwards in background
if check_port 8001; then
    echo "📡 Port-forwarding Data Store (8001)..."
    oc port-forward -n $NAMESPACE svc/nemodatastore-sample 8001:8000 > /dev/null 2>&1 &
    PF1_PID=$!
fi

if check_port 8002; then
    echo "📡 Port-forwarding Entity Store (8002)..."
    oc port-forward -n $NAMESPACE svc/nemoentitystore-sample 8002:8000 > /dev/null 2>&1 &
    PF2_PID=$!
fi

if check_port 8004; then
    echo "📡 Port-forwarding Evaluator (8004)..."
    oc port-forward -n $NAMESPACE svc/nemoevaluator-sample 8004:8000 > /dev/null 2>&1 &
    PF4_PID=$!
fi

if check_port 8006; then
    echo "📡 Port-forwarding External NIM (8006)..."
    # Adjust service name based on your external NIM
    EXTERNAL_NIM_SERVICE=${EXTERNAL_NIM_SERVICE:-anemo-rhoai-predictor-00002}
    oc port-forward -n $NAMESPACE svc/$EXTERNAL_NIM_SERVICE 8006:80 > /dev/null 2>&1 &
    PF6_PID=$!
fi

echo ""
echo "✅ Port-forwards started. PIDs: $PF1_PID $PF2_PID $PF4_PID $PF6_PID"
echo "To stop, run: kill $PF1_PID $PF2_PID $PF4_PID $PF6_PID"
echo ""
echo "Waiting... (Press Ctrl+C to stop)"

# Wait for interrupt
trap "echo ''; echo 'Stopping port-forwards...'; kill $PF1_PID $PF2_PID $PF4_PID $PF6_PID 2>/dev/null; exit" INT
wait

