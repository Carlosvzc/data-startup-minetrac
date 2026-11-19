#!/usr/bin/env bash
# E3 en AWS. Se ejecuta en CloudShell (us-east-1), con tu usuario IAM, desde la carpeta donde descomprimiste minetrac_e3.zip.
#   bash e3_aws.sh ec2        # 1) construye la imagen y corre la API de modelos en la EC2 (puerto 8010)
#   bash e3_aws.sh apprunner  # 2) sube la imagen a ECR y la despliega en AWS App Runner (contenedor administrado)
#   bash e3_aws.sh lambda     # 3) despliega la clasificación como función serverless (Lambda con URL)
#   bash e3_aws.sh locust     # 4) prueba de carga de 50 usuarios contra la EC2
set -euo pipefail
REGION=us-east-1; BUCKET=minetrac-reales-251869518832-20261026
INSTANCIA=i-081fa473088bece22; ROL=minetrac-e1-reales-ReadRole-XxCmmx32Dnlz
export AWS_DEFAULT_REGION=$REGION
CUENTA=$(aws sts get-caller-identity --query Account --output text)
IP=$(aws ec2 describe-instances --instance-ids $INSTANCIA --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
ssm() { # ejecuta comandos en la EC2, espera hasta 15 minutos y muestra el resultado
  local id est; id=$(aws ssm send-command --instance-ids $INSTANCIA --document-name AWS-RunShellScript --comment "$1" --parameters "commands=$2" --query Command.CommandId --output text)
  for i in $(seq 1 90); do
    sleep 10
    est=$(aws ssm get-command-invocation --command-id "$id" --instance-id $INSTANCIA --query Status --output text 2>/dev/null || echo Pending)
    case "$est" in InProgress|Pending|Delayed) printf '.';; *) break;; esac
  done; echo
  aws ssm get-command-invocation --command-id "$id" --instance-id $INSTANCIA --query '{Estado:Status,Salida:StandardOutputContent,Error:StandardErrorContent}' --output text | tail -12
}
paquete() { aws s3 cp minetrac_e3.zip s3://$BUCKET/deploy/minetrac_e3.zip --only-show-errors; }

case "${1:-}" in
ec2)
  [ -f minetrac_e3.zip ] || { echo "Ejecuta el script desde la carpeta donde está minetrac_e3.zip"; exit 1; }
  echo "1/4 Subiendo paquete"; paquete
  echo "2/4 Permiso de lectura del paquete para la instancia"
  aws iam put-role-policy --role-name $ROL --policy-name minetrac-e3-paquete --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$BUCKET/deploy/minetrac_e3.zip\"}]}"
  echo "3/4 Abriendo el puerto 8010"
  SG=$(aws ec2 describe-instances --instance-ids $INSTANCIA --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 8010 --cidr 0.0.0.0/0 2>/dev/null || echo "(el puerto 8010 ya estaba abierto)"
  echo "4/4 Construyendo y arrancando el contenedor (tarda unos 3 minutos)"
  ssm minetrac-e3 '["set -e","mkdir -p /opt/minetrac-e3 && cd /opt/minetrac-e3","aws s3 cp s3://'$BUCKET'/deploy/minetrac_e3.zip e3.zip --region '$REGION'","unzip -oq e3.zip","docker image prune -f >/dev/null","docker build -q -f Dockerfile.modelos -t minetrac-modelos:1.0 .","docker rm -f minetrac-modelos 2>/dev/null || true","docker run -d --name minetrac-modelos --restart unless-stopped -p 8010:8010 minetrac-modelos:1.0","sleep 8","curl -s localhost:8010/salud"]'
  echo "Prueba:  curl http://$IP:8010/salud   y abre  http://$IP:8010/docs"
  ;;
apprunner)
  echo "1/4 Permisos de la instancia para publicar en ECR"
  aws ecr create-repository --repository-name minetrac-modelos >/dev/null 2>&1 || echo "(el repositorio ECR ya existía)"
  aws iam put-role-policy --role-name $ROL --policy-name minetrac-e3-ecr --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"ecr:GetAuthorizationToken\",\"Resource\":\"*\"},{\"Effect\":\"Allow\",\"Action\":[\"ecr:BatchCheckLayerAvailability\",\"ecr:InitiateLayerUpload\",\"ecr:UploadLayerPart\",\"ecr:CompleteLayerUpload\",\"ecr:PutImage\",\"ecr:BatchGetImage\"],\"Resource\":\"arn:aws:ecr:$REGION:$CUENTA:repository/minetrac-modelos\"}]}"
  sleep 10
  echo "2/4 Publicando la imagen en ECR desde la instancia"
  ECR=$CUENTA.dkr.ecr.$REGION.amazonaws.com
  ssm minetrac-e3-ecr '["set -e","aws ecr get-login-password --region '$REGION' | docker login --username AWS --password-stdin '$ECR'","docker tag minetrac-modelos:1.0 '$ECR'/minetrac-modelos:1.0","docker push -q '$ECR'/minetrac-modelos:1.0"]'
  echo "3/4 Rol de acceso de App Runner a ECR"
  aws iam create-role --role-name minetrac-apprunner-ecr --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null 2>&1 || echo "(el rol ya existía)"
  aws iam attach-role-policy --role-name minetrac-apprunner-ecr --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
  sleep 10
  echo "4/4 Creando el servicio en App Runner"
  aws apprunner create-service --service-name minetrac-modelos \
    --source-configuration "{\"ImageRepository\":{\"ImageIdentifier\":\"$ECR/minetrac-modelos:1.0\",\"ImageRepositoryType\":\"ECR\",\"ImageConfiguration\":{\"Port\":\"8010\"}},\"AuthenticationConfiguration\":{\"AccessRoleArn\":\"arn:aws:iam::$CUENTA:role/minetrac-apprunner-ecr\"},\"AutoDeploymentsEnabled\":false}" \
    --instance-configuration '{"Cpu":"1 vCPU","Memory":"2 GB"}' --health-check-configuration '{"Protocol":"HTTP","Path":"/salud"}' \
    --query 'Service.[ServiceUrl,Status]' --output text
  echo "App Runner tarda ~5 minutos. Revisa:  aws apprunner list-services --query 'ServiceSummaryList[0].[ServiceUrl,Status]' --output text"
  ;;
lambda)
  [ -f lambda/minetrac_lambda.zip ] || { echo "Falta lambda/minetrac_lambda.zip"; exit 1; }
  echo "1/3 Rol de ejecución"
  aws iam create-role --role-name minetrac-lambda --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null 2>&1 || echo "(el rol ya existía)"
  aws iam attach-role-policy --role-name minetrac-lambda --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  sleep 12
  echo "2/3 Creando la función"
  aws lambda create-function --function-name minetrac-clasificar --runtime python3.12 --handler handler.lambda_handler \
    --role arn:aws:iam::$CUENTA:role/minetrac-lambda --zip-file fileb://lambda/minetrac_lambda.zip --timeout 10 --memory-size 128 --query FunctionArn --output text \
    || aws lambda update-function-code --function-name minetrac-clasificar --zip-file fileb://lambda/minetrac_lambda.zip --query FunctionArn --output text
  echo "3/3 URL pública de la función"
  aws lambda create-function-url-config --function-name minetrac-clasificar --auth-type NONE --query FunctionUrl --output text 2>/dev/null || true
  aws lambda add-permission --function-name minetrac-clasificar --statement-id url-publica --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE >/dev/null 2>&1 || true
  aws lambda add-permission --function-name minetrac-clasificar --statement-id url-invocar --action lambda:InvokeFunction --principal '*' >/dev/null 2>&1 || true
  URL=$(aws lambda get-function-url-config --function-name minetrac-clasificar --query FunctionUrl --output text)
  sleep 5
  echo "Prueba:"; curl -s -X POST "$URL" -H 'content-type: application/json' -d '{"sistema":"motor","mes":3,"dia_semana":2,"dias_desde_previo_equipo":12,"registros_previos_90d":4,"previos_mismo_sistema_90d":1}'; echo
  ;;
locust)
  if python3 -m pip install -q --user locust >/dev/null 2>&1 && PATH=$PATH:$HOME/.local/bin command -v locust >/dev/null; then
    PATH=$PATH:$HOME/.local/bin locust -f tests/carga/locustfile.py --headless -u 50 -r 10 -t 60s --host http://$IP:8010 --csv resultados_locust 2>&1 | tail -22
  else
    echo "(pip no pudo instalar locust; uso la imagen oficial)"
    docker run --rm -v "$PWD/tests/carga:/mnt/locust" -v "$PWD:/out" locustio/locust -f /mnt/locust/locustfile.py --headless -u 50 -r 10 -t 60s --host http://$IP:8010 --csv /out/resultados_locust 2>&1 | tail -22
  fi
  ;;
*) echo "Uso: bash e3_aws.sh ec2|apprunner|lambda|locust"; exit 1;;
esac
