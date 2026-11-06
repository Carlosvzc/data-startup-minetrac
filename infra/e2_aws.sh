#!/usr/bin/env bash
# E2 en AWS (ejecutar en CloudShell, región us-east-1). SIN PROBAR desde el entorno de desarrollo: revisa la salida de cada paso.
# Crea la cola SQS (con cola de mensajes muertos), da permisos al rol de la instancia y levanta en la EC2 existente:
# PostgreSQL (contenedor), ingesta (puerto 8000) y worker. El tablero sigue en el puerto 8501.
set -euo pipefail
REGION=us-east-1; BUCKET=minetrac-reales-251869518832-20261026
INSTANCIA=i-081fa473088bece22; ROL=minetrac-e1-reales-ReadRole-XxCmmx32Dnlz
ZIP=${1:-minetrac_e2.zip}
[ -f "$ZIP" ] || { echo "Falta $ZIP (el paquete que te envié). Súbelo a CloudShell con Actions > Upload file."; exit 1; }

echo "1/5 Subiendo paquete"; aws s3 cp "$ZIP" s3://$BUCKET/deploy/minetrac_e2.zip --region $REGION


echo "2/5 Cola SQS + mensajes muertos"
DLQ=$(aws sqs create-queue --queue-name minetrac-eventos-muertos --region $REGION --query QueueUrl --output text)
DLQARN=$(aws sqs get-queue-attributes --queue-url "$DLQ" --attribute-names QueueArn --region $REGION --query Attributes.QueueArn --output text)
cat > /tmp/attr.json <<A
{"VisibilityTimeout":"30","RedrivePolicy":"{\"deadLetterTargetArn\":\"$DLQARN\",\"maxReceiveCount\":\"3\"}"}
A
aws sqs create-queue --queue-name minetrac-eventos --region $REGION --attributes file:///tmp/attr.json >/dev/null

echo "3/5 Permisos del rol de la instancia (SQS y escritura en ingesta/)"
cat > /tmp/pol.json <<P
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["sqs:*"],"Resource":"arn:aws:sqs:$REGION:*:minetrac-eventos*"},
 {"Effect":"Allow","Action":["s3:PutObject","s3:GetObject"],"Resource":"arn:aws:s3:::$BUCKET/ingesta/*"}]}
P
aws iam put-role-policy --role-name $ROL --policy-name minetrac-e2 --policy-document file:///tmp/pol.json

echo "4/5 Abrir puerto 8000 de la ingesta"
SG=$(aws ec2 describe-instances --instance-ids $INSTANCIA --region $REGION --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $REGION 2>/dev/null || echo "(puerto 8000 ya estaba abierto)"

echo "5/5 Levantando servicios en la instancia"
aws ssm send-command --region $REGION --instance-ids $INSTANCIA --document-name AWS-RunShellScript --comment minetrac-e2 --parameters 'commands=[
 "set -e",
 "command -v docker >/dev/null || (dnf install -y docker && systemctl enable --now docker)",
 "mkdir -p /opt/minetrac-e2 && cd /opt/minetrac-e2",
 "aws s3 cp s3://'$BUCKET'/deploy/minetrac_e2.zip e2.zip && unzip -oq e2.zip",
 "curl -sSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose",
 "S3_BUCKET='$BUCKET' docker-compose -f infra/docker-compose.aws.yml up -d --build"]' --query Command.CommandId --output text
echo "Listo. Espera ~5 min y prueba:  curl http://54.204.60.100:8000/salud   y abre  http://54.204.60.100:8000/docs"
