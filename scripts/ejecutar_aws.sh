#!/usr/bin/env bash
# Sube raw/ y clean/ al bucket privado y levanta el tablero leyendo desde S3.
# Antes: python scripts/pipeline_e1.py   (genera data/raw y data/clean con los Excel originales)
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${MINETRAC_BUCKET:?Define MINETRAC_BUCKET con el nombre de tu bucket privado}"
REGION="${AWS_DEFAULT_REGION:?Define AWS_DEFAULT_REGION}"
ARN="$(aws sts get-caller-identity --query Arn --output text)"
case "$ARN" in *:root) echo "Usa una identidad IAM individual."; exit 1;; esac
aws s3api head-bucket --bucket "$BUCKET"
# raw/: originales de la empresa. NO se suben los JSON privados de proveedores.
aws s3 cp "data/raw/EQUIPOS MAQ CENTELLA.xlsx" "s3://$BUCKET/raw/EQUIPOS MAQ CENTELLA.xlsx" --only-show-errors
aws s3 cp "data/raw/CAMIONES 12M3 Y 14M3.xlsx" "s3://$BUCKET/raw/CAMIONES 12M3 Y 14M3.xlsx" --only-show-errors
# clean/: tablas limpias que lee el tablero (mantenimiento, inventario, fft, resultados)
aws s3 sync data/clean/ "s3://$BUCKET/clean/" --only-show-errors
python3 -m pip install --user -r requirements.txt
export MINETRAC_STORAGE=s3 MINETRAC_BUCKET="$BUCKET" AWS_DEFAULT_REGION="$REGION"
python3 -m streamlit run services/tablero/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false
