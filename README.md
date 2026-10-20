# GixPD Practice 2 — Docker & Kubernetes ML Deployment

Practice project for training and serving a machine learning model using **Docker** and **Kubernetes (Minikube)**.

The application is divided into two main components:

- `model-train`: trains the machine learning model and stores it on disk.
- `model-server`: exposes the trained model through a Flask API.

The final Kubernetes deployment includes persistent storage, configuration through a ConfigMap, a training Job, a Deployment with 3 replicas and a Service.

---

## Architecture

```text
                    ConfigMap
               MODEL_PATH=/models/model.npy
                      |
              +-------+-------+
              |               |
              v               v
       Training Job       Deployment
              |          (3 replicas)
              |           /    |    \
              v         Pod   Pod   Pod
          model.npy       \    |    /
              |                |
              +---- PVC -------+
                               |
                            Service
                               |
                         port-forward
                               |
                        localhost:5000
```

The training Job writes the model to persistent storage and the three server replicas read the same model from that volume.

---

## Project structure

```text
.
├── model-train/
├── model-server/
├── model-train-v2/
├── model-train-custom/
├── model-server-custom/
├── kubernetes/
│   ├── configmap.yaml
│   ├── pvc.yaml
│   ├── job.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── custom/
├── .gitignore
└── README.md
```

Generated models and exported Docker `.tar` files are ignored by Git.

---

## Requirements

- Docker
- Minikube
- kubectl

In our environment, `kubectl` is provided through Minikube:

```bash
alias kubectl="minikube kubectl --"
```

Because the OpenNebula VM has limited memory, Minikube was configured with:

```bash
minikube config set memory 2200
```

---

# Docker

## Build the base images

```bash
docker build -t model-train:default /home/adminp/practica_gixpd-docker-k8s/model-train

docker build -t model-server:default /home/adminp/practica_gixpd-docker-k8s/model-server
```

Train the model:

```bash
docker run --rm \
  -e MODEL_PATH=/models/model.npy \
  -v /home/adminp/practica_gixpd-docker-k8s/models:/models \
  model-train:default
```

Run the Flask server:

```bash
docker run --rm \
  -e MODEL_PATH=/models/model.npy \
  -v /home/adminp/practica_gixpd-docker-k8s/models:/models:ro \
  -p 8000:8000 \
  model-server:default
```

Test the API:

```bash
curl http://localhost:8000/

curl "http://localhost:8000/model?minutes=5"
```

Example prediction:

```json
{"spent":22.879625918118677}
```

---

# Kubernetes

The Docker images are exported and loaded into Minikube:

```bash
docker save -o model-train.tar model-train:default
docker save -o model-server.tar model-server:default

minikube image load model-train.tar
minikube image load model-server.tar
```

Start the cluster:

```bash
minikube start
```

Deploy the application:

```bash
kubectl apply -f /home/adminp/practica_gixpd-docker-k8s/kubernetes/configmap.yaml

kubectl apply -f /home/adminp/practica_gixpd-docker-k8s/kubernetes/pvc.yaml

kubectl apply -f /home/adminp/practica_gixpd-docker-k8s/kubernetes/job.yaml

kubectl apply -f /home/adminp/practica_gixpd-docker-k8s/kubernetes/deployment.yaml

kubectl apply -f /home/adminp/practica_gixpd-docker-k8s/kubernetes/service.yaml
```

Check the deployment:

```bash
kubectl get jobs
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get pvc
```

Expected result:

```text
Training Job        -> Complete
Model PVC           -> Bound
Server Deployment   -> 3/3 replicas
Server Pods         -> Running
```

Access the API:

```bash
kubectl port-forward service/model-server 5000:5000
```

Then, from another terminal:

```bash
curl "http://localhost:5000/model?minutes=5"
```

---

# Model variants

In addition to the model provided for the practice, we created two alternative versions.

## Polynomial V2

The provided model uses polynomial regression of degree 4.

The V2 version modifies the training process to use a polynomial of degree 2:

```python
mymodel = np.poly1d(np.polyfit(train_x, train_y, 2))
```

This allows us to retrain the application and demonstrate that changing the model produces different predictions.

## Custom model — Decision Tree

We also implemented a different machine learning model using:

```python
DecisionTreeRegressor
```

The custom model:

- uses the same input data;
- is trained independently from the provided polynomial model;
- is serialized using `joblib`;
- has its own training and Flask server Docker images;
- is deployed independently in Kubernetes.

The custom pipeline is:

```text
model-train:custom
        |
        v
DecisionTreeRegressor
        |
        v
model-custom.joblib
        |
        v
Kubernetes PVC
        |
        v
model-server:custom
        |
        v
Service
```

For the same input:

```text
minutes = 5
```

the original polynomial model produces approximately:

```text
22.88
```

while the custom Decision Tree produces approximately:

```text
44
```

This demonstrates that the same Docker/Kubernetes infrastructure can be reused with a different machine learning model.

---

# Restarting the environment

After restarting the OpenNebula VM:

```bash
minikube start
```

Check that the resources are available:

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get jobs
kubectl get pvc
```

The Kubernetes resources are preserved by Minikube.

The `port-forward` must be started again:

```bash
kubectl port-forward service/model-server 5000:5000
```

Use:

```bash
minikube stop
```

to stop the cluster without deleting it.

---

# Repository

The repository keeps the complete evolution of the practice through Git commits, including:

- Dockerization of the training application;
- Dockerization of the Flask server;
- Kubernetes configuration;
- persistent storage and training Job;
- 3-replica server Deployment;
- Service and API access;
- modified polynomial model;
- custom Decision Tree model.

The generated models and Docker image exports are excluded from Git.
