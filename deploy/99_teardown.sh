#!/usr/bin/env bash
# AFTER JUDGING ONLY: delete every resource this project created (one resource group).
set -euo pipefail
cd "$(dirname "$0")"; source env.sh
read -r -p "Delete resource group $RG and everything in it? Type the name to confirm: " ans
[ "$ans" = "$RG" ] && az group delete -n "$RG" --yes --no-wait && echo "Deleting $RG"
