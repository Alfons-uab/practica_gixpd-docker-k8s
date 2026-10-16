# GixPD Practice 2 — Model Training with Docker and Kubernetes

This project contains the implementation of **GixPD Practice 2**, where a machine learning model is trained inside a Docker container and later served through a Flask API deployed with Kubernetes.

The project uses two Docker images:

- `model-train:default`: trains the model and saves it to disk.
- `model-server:default`: loads the trained model and exposes it through a Flask API.

The Kubernetes deployment uses a `ConfigMap`, persistent storage, a training `Job`, a `Deployment` with 3 replicas, and a `Service`.

---

## Architecture

```text
                         ConfigMap
                    MODEL_PATH=/models/model.npy
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          Job model-train      Deployment model-server
                 |                   |
                 |              +----+----+
                 |              |    |    |
                 |             Pod  Pod  Pod
                 |              |    |    |
                 v              +----+----+
             model.npy               |
                 |                   |
                 +----> PVC <---------+
                                      |
                                   Service
                                    :5000
                                      |
                                port-forward
                                      |
                              localhost:5000
```

---

## Project structure

```text
.
├── model-train/
│   ├── Dockerfile
│   ├── main-train.py
│   └── requirements-train.txt
│
├── model-server/
│   ├── Dockerfile
│   ├── main-server.py
│   └── requirements-server.txt
│
├── kubernetes/
│   ├── configmap.yaml
│   ├── pvc.yaml
│   ├── job.yaml
│   ├── deployment.yaml
│   └── service.yaml
│
├── .gitignore
└── README.md
```

Generated models and exported Docker images are not stored in Git.

---

# 1. Dependencies

The following tools are required:

- Docker
- Minikube
- kubectl, or Minikube's integrated kubectl

For this project we use Minikube's kubectl through the following alias:

```bash
alias kubectl="minikube kubectl --"
```

This alias can be stored permanently in `/home/adminp/.bashrc`.

---

# 2. Docker

## 2.1 Build the training image

From the repository root:

```bash
docker build -t model-train:default ./model-train
```

Check that the image exists:

```bash
docker images
```

The training container receives the model destination through the `MODEL_PATH` environment variable.

Create a directory for generated models:

```bash
mkdir -p models
```

Run the training container:

```bash
docker run --rm \
  -e MODEL_PATH=/models/model.npy \
  -v "$(pwd)/models:/models" \
  model-train:default
```

Expected output:

```text
Model trained successfully
Model Score: 0.808...
```

The generated model should now exist at:

```text
models/model.npy
```

---

## 2.2 Build the model server image

Build the Flask server:

```bash
docker build -t model-server:default ./model-server
```

Check both images:

```bash
docker images
```

The following images should exist:

```text
model-train:default
model-server:default
```

Run the model server:

```bash
docker run --rm \
  -e MODEL_PATH=/models/model.npy \
  -v "$(pwd)/models:/models:ro \
  -p 8000:8000 \
  model-server:default
```

The model directory is mounted as read-only because the server only needs to read the trained model.

---

## 2.3 Test the Docker application

Keep the server container running and open another terminal.

Test the documentation endpoint:

```bash
curl http://localhost:8000/
```

Test a model prediction:

```bash
curl "http://localhost:8000/model?minutes=5"
```

Example response:

```json
{"spent":22.879625918118677}
```

`minutes=5` is a query parameter passed to the API.

The server loads `model.npy` and uses the trained model to predict the amount spent for a customer who takes 5 minutes before making a purchase.

At this point the complete local Docker flow is:

```text
model-train
    |
    v
model.npy
    |
    v
model-server
    |
    v
Flask API
    |
    v
/model?minutes=5
```

---

# 3. Kubernetes

## 3.1 Export the Docker images

The Docker images are exported to `.tar` files before loading them into Minikube.

```bash
docker save -o model-train.tar model-train:default
docker save -o model-server.tar model-server:default
```

Check them:

```bash
ls -lh *.tar
```

The `.tar` files are ignored by Git.

---

## 3.2 Start Minikube

Our OpenNebula VM has limited RAM, so Minikube is configured to use 2200 MB:

```bash
minikube config set memory 2200
```

Start the cluster:

```bash
minikube start
```

Check its status:

```bash
minikube status
```

Check the Kubernetes node:

```bash
kubectl get nodes
```

Expected status:

```text
minikube   Ready   control-plane
```

---

## 3.3 Load the images into Minikube

```bash
minikube image load model-train.tar
minikube image load model-server.tar
```

Check that both images are available:

```bash
minikube image ls | grep "model-"
```

Expected images:

```text
docker.io/library/model-train:default
docker.io/library/model-server:default
```

---

# 4. Kubernetes resources

## 4.1 ConfigMap

The ConfigMap stores:

```text
MODEL_PATH=/models/model.npy
```

Apply it:

```bash
kubectl apply -f kubernetes/configmap.yaml
```

Check it:

```bash
kubectl get configmaps
kubectl describe configmap model-config
```

The ConfigMap stores configuration only. It does not contain the model itself.

---

## 4.2 Persistent Volume

The model is stored in a PersistentVolumeClaim named `model-pvc`.

Apply it:

```bash
kubectl apply -f kubernetes/pvc.yaml
```

Check its state:

```bash
kubectl get pvc
```

Expected state:

```text
model-pvc   Bound
```

The PVC allows the model generated by the training Job to be read later by the model server Deployment.

---

## 4.3 Training Job

Apply the training Job:

```bash
kubectl apply -f kubernetes/job.yaml
```

Check its status:

```bash
kubectl get jobs
kubectl get pods
```

The training Pod should transition from:

```text
Running
```

to:

```text
Completed
```

This is expected because a Kubernetes Job performs a task and terminates.

Check the training logs:

```bash
kubectl logs job/model-train
```

Example output:

```text
Model trained successfully
Model Score: 0.8086921460343587
```

The Job:

- uses the `model-train:default` image;
- receives `MODEL_PATH` from the ConfigMap;
- mounts the persistent volume at `/models`;
- trains the model;
- writes `model.npy` to persistent storage;
- defines CPU and memory requests and limits.

---

## 4.4 Model Server Deployment

Apply the Deployment:

```bash
kubectl apply -f kubernetes/deployment.yaml
```

Check it:

```bash
kubectl get deployments
kubectl get pods
```

Expected Deployment state:

```text
model-server   3/3
```

Three server Pods should be running:

```text
model-server-...   1/1   Running
model-server-...   1/1   Running
model-server-...   1/1   Running
```

The Deployment:

- runs 3 replicas of `model-server:default`;
- obtains `MODEL_PATH` from the ConfigMap;
- mounts the trained model as read-only;
- defines CPU and memory requests and limits;
- defines readiness and liveness probes.

The readiness probe checks whether a Pod is ready to receive traffic.

The liveness probe checks whether the application is still healthy and should continue running.

---

## 4.5 Service

The three model-server Pods are exposed through a Kubernetes Service.

Apply it:

```bash
kubectl apply -f kubernetes/service.yaml
```

Check it:

```bash
kubectl get services
kubectl describe service model-server
```

The Service exposes port `5000` and forwards requests to port `8000` on the Flask containers:

```text
Service :5000
     |
     v
Pod :8000
```

The Service selector automatically finds Pods with:

```text
app=model-server
```

---

# 5. Accessing the API

The Kubernetes Service uses `ClusterIP`, so it is accessible from inside the cluster.

To access it from the VM, use port forwarding:

```bash
kubectl port-forward service/model-server 5000:5000
```

Keep this terminal open.

In another terminal, test the API.

Documentation endpoint:

```bash
curl http://localhost:5000/
```

Prediction endpoint:

```bash
curl "http://localhost:5000/model?minutes=5"
```

Example response:

```json
{"spent":22.879625918118677}
```

Complete request flow:

```text
curl
 |
 v
localhost:5000
 |
 | port-forward
 v
Kubernetes Service :5000
 |
 v
one of the 3 model-server Pods :8000
 |
 v
Flask
 |
 v
model.npy
 |
 v
JSON prediction
```

---

# 6. Restarting the environment

If the OpenNebula VM is stopped or restarted, it is normally not necessary to deploy everything again.

Start the existing Minikube cluster:

```bash
minikube start
```

Check Minikube:

```bash
minikube status
```

Check the node:

```bash
kubectl get nodes
```

Check the Kubernetes resources:

```bash
kubectl get configmaps
kubectl get pvc
kubectl get jobs
kubectl get deployments
kubectl get pods
kubectl get services
```

Expected state:

```text
model-config        available
model-pvc           Bound
model-train         Complete
model-server        3/3
model-server Pods   Running
model-server        Service available
```

The Deployment automatically recreates/restarts its Pods when the Kubernetes cluster starts again.

The port-forward is temporary and must be started again:

```bash
kubectl port-forward service/model-server 5000:5000
```

Then the API can be tested again:

```bash
curl http://localhost:5000/
curl "http://localhost:5000/model?minutes=5"
```

---

## Re-running the training Job

A completed Job does not run again automatically.

To train the model again:

```bash
kubectl delete job model-train
```

Then recreate it:

```bash
kubectl apply -f kubernetes/job.yaml
```

Check the new execution:

```bash
kubectl get pods
kubectl logs job/model-train
```

---

## Stopping Minikube

To stop the cluster without deleting it:

```bash
minikube stop
```

It can later be restored using:

```bash
minikube start
```

Avoid using:

```bash
minikube delete
```

unless the intention is to completely delete the Kubernetes cluster and recreate it from scratch.

---

# 7. Useful commands

```bash
# Minikube
minikube start
minikube stop
minikube status

# General Kubernetes status
kubectl get nodes
kubectl get pods
kubectl get deployments
kubectl get jobs
kubectl get services
kubectl get configmaps
kubectl get pvc

# Detailed information
kubectl describe configmap model-config
kubectl describe pvc model-pvc
kubectl describe job model-train
kubectl describe deployment model-server
kubectl describe service model-server

# Logs
kubectl logs job/model-train
kubectl logs deployment/model-server

# API access
kubectl port-forward service/model-server 5000:5000
```

---

# 8. Troubleshooting

## Minikube cannot connect

If commands such as:

```bash
kubectl get pods
```

return an error similar to:

```text
connect: no route to host
```

check Minikube:

```bash
minikube status
```

If it is stopped:

```bash
minikube start
```

---

## Minikube requests too much memory

Our VM originally failed with:

```text
Docker has only 3394MB memory but you specified 9001MB
```

The configured memory was reduced to:

```bash
minikube config set memory 2200
```

After that Minikube started correctly.

---

# 9. Possible extensions

The basic Docker and Kubernetes deployment is complete.

Possible improvements for the final version include:

- replacing the provided model with our own machine learning model;
- modifying the training model and demonstrating that executing the Kubernetes Job changes the predictions returned by the API;
- improving the API validation and error handling;
- improving the project documentation;
- maintaining a clear Git commit history showing the evolution of the project.

These extensions can be used to demonstrate a deeper understanding of the complete training and deployment pipeline.
