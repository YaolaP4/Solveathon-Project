#!/usr/bin/env bash
# Steps 1-5 of the starter kit (capacity = thousands of tokens per minute; the kit default of 50
# made the first full embedding pass take ~30 minutes, so we use 1000 for embeddings and 500 for chat): resource group, Blob Storage, Azure OpenAI (+2 models),
# container registry and Container Apps environment. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"; source env.sh
az account set --subscription "$SUBSCRIPTION"

echo "== Step 1: providers and resource group"
az extension add --name containerapp --upgrade --only-show-errors
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.Storage Microsoft.CognitiveServices; do
  az provider register --namespace "$ns" --wait
done
az group create --name "$RG" --location "$LOCATION" -o none
az group show -n "$RG" --query properties.provisioningState -o tsv

echo "== Step 2: Blob Storage (no public blob access, TLS 1.2)"
az storage account create -n "$STORAGE" -g "$RG" -l "$LOCATION" --sku Standard_LRS --kind StorageV2 \
  --min-tls-version TLS1_2 --allow-blob-public-access false -o none
CONN=$(az storage account show-connection-string -n "$STORAGE" -g "$RG" --query connectionString -o tsv)
az storage container create --name "$CONTAINER" --connection-string "$CONN" -o none
az storage container list --connection-string "$CONN" --query "[].name" -o tsv

echo "== Step 3: Azure OpenAI + two model deployments"
az cognitiveservices account create -n "$AOAI" -g "$RG" -l "$LOCATION" --kind OpenAI --sku S0 \
  --custom-domain "$AOAI" --yes -o none
az cognitiveservices account deployment create -n "$AOAI" -g "$RG" --deployment-name embed \
  --model-name text-embedding-3-small --model-version 1 --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 1000 -o none || echo "embed deployment: check list-models"
az cognitiveservices account deployment create -n "$AOAI" -g "$RG" --deployment-name chat \
  --model-name "${CHAT_MODEL:-gpt-4.1-mini}" --model-version "${CHAT_MODEL_VERSION:-2025-04-14}" --model-format OpenAI \
  --sku-name GlobalStandard --sku-capacity 500 -o none || echo "chat deployment: check list-models"
az cognitiveservices account deployment list -n "$AOAI" -g "$RG" \
  --query "[].{name:name, model:properties.model.name, version:properties.model.version, state:properties.provisioningState}" -o table

echo "== Step 5: container registry + Container Apps environment"
az acr create -n "$ACR" -g "$RG" -l "$LOCATION" --sku Basic --admin-enabled true -o none
az containerapp env create -n "$CAE" -g "$RG" -l "$LOCATION" -o none
az containerapp env show -n "$CAE" -g "$RG" --query properties.provisioningState -o tsv
