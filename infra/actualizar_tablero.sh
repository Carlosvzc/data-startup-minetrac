#!/usr/bin/env bash
# Actualiza SOLO el tablero de MineTrac en la EC2 existente (alcance: camiones).
# Se ejecuta en AWS CloudShell, con tu usuario IAM (no la cuenta raiz), desde la carpeta donde descomprimiste el paquete:
#     unzip minetrac_actualizacion_camiones.zip && cd minetrac_actualizacion_camiones && bash actualizar_tablero.sh
# No sube datos ni claves. Para volver a mostrar la libreta y la prediccion de toda la flota: MINETRAC_ALCANCE=flota en la unidad del servicio.
set -euo pipefail
BUCKET="minetrac-reales-251869518832-20261026"; REGION="us-east-1"; INSTANCE="i-081fa473088bece22"
export AWS_DEFAULT_REGION="$REGION"
ARN="$(aws sts get-caller-identity --query Arn --output text)"; echo "Identidad: $ARN"
case "$ARN" in *:root) echo "Usa un usuario IAM individual, no la cuenta raiz."; exit 1;; esac
[ -f deploy/minetrac.zip ] || { echo "Falta deploy/minetrac.zip: ejecuta el script desde la carpeta descomprimida."; exit 1; }

echo "1/4 Subiendo el paquete del tablero"
aws s3 cp deploy/minetrac.zip "s3://$BUCKET/deploy/minetrac.zip" --only-show-errors

echo "2/4 Comprobando que la instancia esta en linea en Systems Manager"
ST="$(aws ssm describe-instance-information --filters Key=InstanceIds,Values=$INSTANCE --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null || true)"
[ "$ST" = "Online" ] || { echo "La instancia no esta en linea (estado: $ST). Revisa que este encendida y vuelve a intentar."; exit 2; }

echo "3/4 Actualizando el tablero"
CMD="$(aws ssm send-command --instance-ids "$INSTANCE" --document-name AWS-RunShellScript --comment 'Tablero MineTrac solo camiones' \
 --parameters 'commands=["set -e","D=$(systemctl show minetrac -p WorkingDirectory --value)","echo carpeta: $D","cd $D","aws s3 cp s3://'$BUCKET'/deploy/minetrac.zip app.zip --region '$REGION'","unzip -oq app.zip","chown -R ec2-user:ec2-user $D","systemctl restart minetrac","sleep 10","systemctl is-active minetrac"]' \
 --query Command.CommandId --output text)"
aws ssm wait command-executed --command-id "$CMD" --instance-id "$INSTANCE" || true
aws ssm get-command-invocation --command-id "$CMD" --instance-id "$INSTANCE" --query '{Estado:Status,Salida:StandardOutputContent,Error:StandardErrorContent}' --output text | tail -6

echo "4/4 Verificando"
IP="$(aws ec2 describe-instances --instance-ids "$INSTANCE" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
sleep 5
echo "HTTP $(curl -s -o /dev/null -w '%{http_code}' --max-time 20 http://$IP:8501/_stcore/health) en http://$IP:8501/"
echo "Listo. Abre esa direccion, pulsa 'Recargar datos' y comprueba que hay 6 pestanas (sin Libreta ni Prediccion)."
