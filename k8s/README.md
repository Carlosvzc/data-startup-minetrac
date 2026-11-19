# Kubernetes (E3)

Con un clúster local (k3d, kind o minikube):

```
docker build -f Dockerfile.modelos -t minetrac-modelos:1.0 .
k3d image import minetrac-modelos:1.0 -c minetrac     # o: kind load docker-image minetrac-modelos:1.0
kubectl apply -f k8s/
kubectl get pods -l app=minetrac-modelos
kubectl port-forward svc/minetrac-modelos 8010:8010
```
