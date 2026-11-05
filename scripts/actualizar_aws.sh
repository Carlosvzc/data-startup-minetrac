#!/usr/bin/env bash
# Actualiza MineTrac en AWS con el rediseño del tablero y la libreta de taller.
# Se ejecuta en AWS CloudShell (con tu usuario IAM, no con la cuenta raíz) desde la carpeta donde descomprimiste el paquete:
#     unzip minetrac_actualizacion_aws.zip && cd minetrac_actualizacion_aws && bash actualizar_aws.sh
# No guarda claves: CloudShell usa tu sesión. Solo toca el bucket, el rol de lectura de la instancia y los archivos de la app.
set -euo pipefail
BUCKET="minetrac-reales-251869518832-20261026"
REGION="us-east-1"
INSTANCE="i-081fa473088bece22"
ROLE="minetrac-e1-reales-ReadRole-XxCmmx32Dnlz"
export AWS_DEFAULT_REGION="$REGION"

ARN="$(aws sts get-caller-identity --query Arn --output text)"
echo "Identidad: $ARN"
case "$ARN" in *:root) echo "Usa un usuario IAM individual, no la cuenta raíz."; exit 1;; esac
aws s3api head-bucket --bucket "$BUCKET"

echo "1/5 Subiendo clean/ y la transcripción privada a raw/ ..."
aws s3 cp clean/ "s3://$BUCKET/clean/" --recursive --only-show-errors
aws s3 cp raw/libreta_transcripcion_PRIVADO.md "s3://$BUCKET/raw/libreta_transcripcion_PRIVADO.md" --only-show-errors
aws s3 cp deploy/minetrac.zip "s3://$BUCKET/deploy/minetrac.zip" --only-show-errors

echo "2/5 Ampliando el permiso de lectura del rol de la instancia (solo lectura de clean/ y del zip) ..."
cat > /tmp/politica.json <<JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":"s3:GetObject","Resource":["arn:aws:s3:::$BUCKET/clean/*","arn:aws:s3:::$BUCKET/deploy/minetrac.zip"]},
 {"Effect":"Allow","Action":"s3:ListBucket","Resource":"arn:aws:s3:::$BUCKET","Condition":{"StringLike":{"s3:prefix":["clean/*","deploy/minetrac.zip"]}}}]}
JSON
aws iam put-role-policy --role-name "$ROLE" --policy-name MineTracRealRead --policy-document file:///tmp/politica.json
# Permite administrar la instancia con Systems Manager (sin abrir SSH) para actualizar la app sin recrearla.
aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

echo "3/5 Esperando a que la instancia aparezca en Systems Manager (puede tardar unos minutos) ..."
for i in $(seq 1 40); do
  ST="$(aws ssm describe-instance-information --filters Key=InstanceIds,Values=$INSTANCE --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
  [ "$ST" = "Online" ] && break
  sleep 15
done
if [ "$ST" != "Online" ]; then
  echo "La instancia aún no está en línea en Systems Manager. Espera 5 minutos y vuelve a ejecutar este script."; exit 2
fi

echo "4/5 Actualizando la app en la instancia ..."
CMD="$(aws ssm send-command --instance-ids "$INSTANCE" --document-name AWS-RunShellScript --comment 'Actualiza MineTrac' \
  --parameters 'commands=["set -e","cd /opt/minetrac","aws s3 cp s3://'$BUCKET'/deploy/minetrac.zip app.zip --region '$REGION'","unzip -oq app.zip","chown -R ec2-user:ec2-user /opt/minetrac","venv/bin/pip install -q -r requirements.txt","systemctl restart minetrac","sleep 8","systemctl is-active minetrac"]' \
  --query Command.CommandId --output text)"
aws ssm wait command-executed --command-id "$CMD" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --command-id "$CMD" --instance-id "$INSTANCE" --query '{Estado:Status,Salida:StandardOutputContent,Error:StandardErrorContent}' --output text | tail -5

echo "5/5 Verificando el tablero ..."
IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
sleep 5
echo "HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://$IP:8501/_stcore/health) en http://$IP:8501/"
echo "Listo. Abre la dirección, pulsa 'Recargar datos' si hace falta y revisa la pestaña Libreta de taller."
