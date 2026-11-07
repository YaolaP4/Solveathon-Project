#!/usr/bin/env bash
# Steps 6-8 of the starter kit: build the image in the cloud, deploy the web app, create the
# daily refresh job and run it once. Re-run with a new TAG to roll out a code change:
#     TAG=v2 bash deploy/02_deploy.sh
# Secrets are read from Azure into shell variables and passed only as Container Apps secrets.
set -euo pipefail
cd "$(dirname "$0")"; source env.sh
export PYTHONIOENCODING=utf-8   # the Windows console cannot print some build-log characters
az account set --subscription "$SUBSCRIPTION"

STORAGE_CONN=$(az storage account show-connection-string -n "$STORAGE" -g "$RG" --query connectionString -o tsv)
AOAI_ENDPOINT=$(az cognitiveservices account show -n "$AOAI" -g "$RG" --query properties.endpoint -o tsv)
AOAI_KEY=$(az cognitiveservices account keys list -n "$AOAI" -g "$RG" --query key1 -o tsv)
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)
# A stable session key so every app replica/worker accepts the same form tokens.
FLASK_SECRET=$(az containerapp secret show -n "$APP" -g "$RG" --secret-name flask-secret --query value -o tsv 2>/dev/null || true)
FLASK_SECRET=${FLASK_SECRET:-$(python -c "import secrets; print(secrets.token_hex(32))")}

SECRETS=(storage-conn="$STORAGE_CONN" aoai-key="$AOAI_KEY" flask-secret="$FLASK_SECRET")
ENVS=(STORAGE_CONN=secretref:storage-conn AOAI_ENDPOINT="$AOAI_ENDPOINT" AOAI_KEY=secretref:aoai-key
      AOAI_CHAT_DEPLOYMENT=chat AOAI_EMBED_DEPLOYMENT=embed FLASK_SECRET_KEY=secretref:flask-secret TZ=America/New_York)

echo "== Step 6: build image $IMAGE in ACR (no local Docker needed)"
if [ "${SKIP_BUILD:-0}" != "1" ]; then
  # Queue the cloud build without streaming its log (the log stream crashes Windows consoles),
  # then wait for the run to finish and stop if it failed.
  RUN_ID=$(cd .. && az acr build --registry "$ACR" --image "ffm:$TAG" --no-logs . --query runId -o tsv)
  echo "ACR build run $RUN_ID queued"
  while :; do
    STATUS=$(az acr task show-run -r "$ACR" --run-id "$RUN_ID" --query status -o tsv)
    case "$STATUS" in
      Succeeded) echo "build succeeded"; break ;;
      Failed|Canceled|Error|Timeout) echo "build $STATUS: az acr task logs -r $ACR --run-id $RUN_ID"; exit 1 ;;
      *) sleep 15 ;;
    esac
  done
fi
az acr repository show-tags -n "$ACR" --repository ffm -o tsv

echo "== Step 7: web app"
if az containerapp show -n "$APP" -g "$RG" -o none 2>/dev/null; then
  az containerapp secret set -n "$APP" -g "$RG" --secrets "${SECRETS[@]}" -o none
  az containerapp update -n "$APP" -g "$RG" --image "$IMAGE" --set-env-vars MODE=app "${ENVS[@]}" -o none
else
  az containerapp create -n "$APP" -g "$RG" --environment "$CAE" --image "$IMAGE" \
    --registry-server "$ACR.azurecr.io" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --ingress external --target-port 8000 --cpu 1.0 --memory 2.0Gi --min-replicas 1 --max-replicas 1 \
    --secrets "${SECRETS[@]}" --env-vars MODE=app "${ENVS[@]}" -o none
fi
echo "App URL: https://$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)"

echo "== Step 8: daily refresh job (11:00 UTC = 6:00 AM Eastern Standard Time)"
if az containerapp job show -n "$JOB" -g "$RG" -o none 2>/dev/null; then
  az containerapp job secret set -n "$JOB" -g "$RG" --secrets "${SECRETS[@]}" -o none
  az containerapp job update -n "$JOB" -g "$RG" --image "$IMAGE" --set-env-vars MODE=job "${ENVS[@]}" -o none
else
  az containerapp job create -n "$JOB" -g "$RG" --environment "$CAE" \
    --trigger-type Schedule --cron-expression "0 11 * * *" \
    --replica-timeout 3600 --replica-retry-limit 1 --replica-completion-count 1 --parallelism 1 \
    --image "$IMAGE" --registry-server "$ACR.azurecr.io" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --cpu 1.0 --memory 2.0Gi --secrets "${SECRETS[@]}" --env-vars MODE=job "${ENVS[@]}" -o none
fi
if [ "${RUN_JOB:-1}" = "1" ]; then
  az containerapp job start -n "$JOB" -g "$RG" -o none
  echo "Job started. Watch it with:"
  echo "  az containerapp job execution list -n $JOB -g $RG --query \"[].{name:name, status:properties.status, start:properties.startTime}\" -o table"
fi
