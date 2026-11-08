# Resource names for the Federal Funds Matchmaker (starter kit sec. 4, Step 0).
# No secrets here: keys and connection strings are read from Azure at deploy time
# and stored only as Container Apps secrets (and in your local, git-ignored .env).
export PREFIX="ffm"
export LOCATION="${LOCATION:-eastus2}"
export SUFFIX="4817"
export SUBSCRIPTION="unc-sdis-solveathon-team14"
export RG="rg-$PREFIX-team14"
export STORAGE="st${PREFIX}${SUFFIX}"
export CONTAINER="ffm-data"
export AOAI="aoai-$PREFIX-$SUFFIX"
export ACR="acr${PREFIX}${SUFFIX}"
export CAE="cae-$PREFIX"
export APP="app-$PREFIX-web"
export JOB="job-$PREFIX-refresh"
export TAG="${TAG:-v8}"   # the deployed tag; bump it for every rollout (TAG=v9 bash deploy/02_deploy.sh)
export IMAGE="$ACR.azurecr.io/ffm:$TAG"
