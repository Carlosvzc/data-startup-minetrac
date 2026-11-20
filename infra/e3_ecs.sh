#!/usr/bin/env bash
# E3 · contenedor administrado en AWS ECS Fargate (misma imagen de ECR). Se ejecuta en CloudShell, us-east-1.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""
CUENTA=$(aws sts get-caller-identity --query Account --output text)
INSTANCIA=i-081fa473088bece22
IMG=$CUENTA.dkr.ecr.us-east-1.amazonaws.com/minetrac-modelos:1.0
SUBRED=$(aws ec2 describe-instances --instance-ids $INSTANCIA --query 'Reservations[0].Instances[0].SubnetId' --output text)
SG=$(aws ec2 describe-instances --instance-ids $INSTANCIA --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
echo "1/4 Rol de ejecución y registros"
aws iam create-role --role-name minetrac-ecs-exec --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null 2>&1 || echo "(el rol ya existía)"
aws iam attach-role-policy --role-name minetrac-ecs-exec --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws logs create-log-group --log-group-name /ecs/minetrac-modelos >/dev/null 2>&1 || true
sleep 10
echo "2/4 Clúster y definición de la tarea"
aws ecs create-cluster --cluster-name minetrac >/dev/null
cat > /tmp/tarea.json <<T
{"family":"minetrac-modelos","networkMode":"awsvpc","requiresCompatibilities":["FARGATE"],"cpu":"1024","memory":"2048",
 "executionRoleArn":"arn:aws:iam::$CUENTA:role/minetrac-ecs-exec",
 "containerDefinitions":[{"name":"modelos","image":"$IMG","essential":true,"portMappings":[{"containerPort":8010}],
  "logConfiguration":{"logDriver":"awslogs","options":{"awslogs-group":"/ecs/minetrac-modelos","awslogs-region":"us-east-1","awslogs-stream-prefix":"modelos"}}}]}
T
aws ecs register-task-definition --cli-input-json file:///tmp/tarea.json --query taskDefinition.taskDefinitionArn --output text
echo "3/4 Servicio (1 tarea con IP pública, puerto 8010)"
aws ecs create-service --cluster minetrac --service-name minetrac-modelos --task-definition minetrac-modelos --desired-count 1 --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBRED],securityGroups=[$SG],assignPublicIp=ENABLED}" --query service.status --output text
echo "4/4 Esperando a que la tarea quede en ejecución (2 a 4 minutos)"
aws ecs wait services-stable --cluster minetrac --services minetrac-modelos
TAREA=$(aws ecs list-tasks --cluster minetrac --service-name minetrac-modelos --query 'taskArns[0]' --output text)
ENI=$(aws ecs describe-tasks --cluster minetrac --tasks "$TAREA" --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)
IPF=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI" --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
echo "Estado: $(aws ecs describe-services --cluster minetrac --services minetrac-modelos --query 'services[0].[runningCount,desiredCount]' --output text)"
sleep 5; echo "Prueba:"; curl -s --max-time 15 http://$IPF:8010/salud; echo; echo "Abre  http://$IPF:8010/docs"
