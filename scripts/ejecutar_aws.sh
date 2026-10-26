
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUCKET="${MINETRAC_BUCKET:-minetrac-e1-251869518832}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ARN="$(aws sts get-caller-identity --query Arn --output text)"
case "$ARN" in *:root) echo "Usa una identidad IAM individual."; exit 1;; esac
aws s3api head-bucket --bucket "$BUCKET"
aws s3 cp data/raw/operacion_simulada_raw.csv "s3://$BUCKET/raw/operacion_simulada_raw.csv" --only-show-errors
aws s3 cp data/raw/inventario_proporcionado.csv "s3://$BUCKET/raw/inventario_proporcionado.csv" --only-show-errors
aws s3 sync data/clean/ "s3://$BUCKET/clean/" --only-show-errors
python3 -m pip install --user -r requirements.txt
export MINETRAC_STORAGE=s3 MINETRAC_BUCKET="$BUCKET" AWS_DEFAULT_REGION="$REGION"
python3 -m streamlit run services/tablero/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true --browser.gatherUsageStats false

