#!/bin/bash

# Set default namespace if not provided
NAMESPACE=${NAMESPACE:-default}

# Check if NEMO_NAMESPACE is provided
if [ -z "$NEMO_NAMESPACE" ]; then
    echo "ERROR: You must set NEMO_NAMESPACE to your actual NeMo namespace!"
    echo "Example: NEMO_NAMESPACE=my-nemo-ns ./deploy_llamastack.sh"
    exit 1
fi

echo "Deploying LlamaStack to namespace: $NAMESPACE"
echo "Using NeMo namespace: $NEMO_NAMESPACE"

# Update the deployment.yaml with the actual NeMo namespace
sed -i.bak "s/YOUR_NEMO_NAMESPACE/$NEMO_NAMESPACE/g" deployment.yaml
sed -i.bak "s/YOUR_NEMO_NAMESPACE/$NEMO_NAMESPACE/g" configmap.yaml

oc apply -f configmap.yaml -n $NAMESPACE
oc apply -f service.yaml -n $NAMESPACE
oc apply -f deployment.yaml -n $NAMESPACE
oc wait --for=condition=available deployment/llamastack --timeout=300s -n $NAMESPACE
sleep 3s
# oc apply -f route.yaml -n $NAMESPACE

oc get pods -n $NAMESPACE | grep llamastack
# oc get route -n $NAMESPACE | grep llamastack