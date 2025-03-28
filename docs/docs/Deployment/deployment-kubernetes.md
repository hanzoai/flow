---
title: Deploy Hanzoflow on Kubernetes
slug: /deployment-kubernetes
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

This guide demonstrates deploying Hanzoflow on a Kubernetes cluster.

Two charts are available at the [Hanzoflow Helm Charts repository](https://github.com/hanzoflow-ai/hanzoflow-helm-charts):

- Deploy the [Hanzoflow IDE](#deploy-the-hanzoflow-ide) for the complete Hanzoflow development environment.
- Deploy the [Hanzoflow runtime](#deploy-the-hanzoflow-runtime) to deploy a standalone Hanzoflow application in a more secure and stable environment.

## Deploy the Hanzoflow IDE

The Hanzoflow IDE deployment is a complete environment for developers to create, test, and debug their flows. It includes both the API and the UI.

The `hanzoflow-ide` Helm chart is available in the [Hanzoflow Helm Charts repository](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/tree/main/charts/hanzoflow-ide).

### Prerequisites

- A [Kubernetes](https://kubernetes.io/docs/setup/) cluster
- [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)
- [Helm](https://helm.sh/docs/intro/install/)

### Prepare a Kubernetes cluster

This example uses [Minikube](https://minikube.sigs.k8s.io/docs/start/), but you can use any Kubernetes cluster.

1. Create a Kubernetes cluster on Minikube.

	```text
	minikube start
	```

2. Set `kubectl` to use Minikube.

	```text
	kubectl config use-context minikube
	```

### Install the Hanzoflow IDE Helm chart

1. Add the repository to Helm and update it.

	```text
	helm repo add hanzoflow https://hanzoflow-ai.github.io/hanzoflow-helm-charts
	helm repo update
	```

2. Install Hanzoflow with the default options in the `hanzoflow` namespace.

	```text
	helm install hanzoflow-ide hanzoflow/hanzoflow-ide -n hanzoflow --create-namespace
	```

3. Check the status of the pods

	```text
	kubectl get pods -n hanzoflow
	```


	```text
	NAME                                 READY   STATUS    RESTARTS       AGE
	hanzoflow-0                           1/1     Running   0              33s
	hanzoflow-frontend-5d9c558dbb-g7tc9   1/1     Running   0              38s
	```


### Configure port forwarding to access Hanzoflow

Enable local port forwarding to access Hanzoflow from your local machine.

1. To make the Hanzoflow API accessible from your local machine at port 7860:
```text
kubectl port-forward -n hanzoflow svc/hanzoflow-service-backend 7860:7860
```

2. To make the Hanzoflow UI accessible from your local machine at port 8080:
```text
kubectl port-forward -n hanzoflow svc/hanzoflow-service 8080:8080
```

Now you can access:
- The Hanzoflow API at `http://localhost:7860`
- The Hanzoflow UI at `http://localhost:8080`


### Configure the Hanzoflow version

Hanzoflow is deployed with the `latest` version by default.

To specify a different Hanzoflow version, set the `hanzoflow.backend.image.tag` and `hanzoflow.frontend.image.tag` values in the [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-ide/values.yaml) file.


```yaml
hanzoflow:
  backend:
    image:
      tag: "1.0.0a59"
  frontend:
    image:
      tag: "1.0.0a59"

```


### Configure external storage

By default, the chart deploys a SQLite database stored in a local persistent disk.
If you want to use an external PostgreSQL database, you can configure it in two ways:

* Use the built-in PostgreSQL chart:
```yaml
postgresql:
  enabled: true
  auth:
    username: "hanzoflow"
    password: "hanzoflow-postgres"
    database: "hanzoflow-db"
```

* Use an external database:
```yaml
postgresql:
  enabled: false

hanzoflow:
  backend:
    externalDatabase:
      enabled: true
      driver:
        value: "postgresql"
      port:
        value: "5432"
      user:
        value: "hanzoflow"
      password:
        valueFrom:
          secretKeyRef:
            key: "password"
            name: "your-secret-name"
      database:
        value: "hanzoflow-db"
    sqlite:
      enabled: false
```


### Configure scaling

Scale the number of replicas and resources for both frontend and backend services:

```yaml
hanzoflow:
  backend:
    replicaCount: 1
    resources:
      requests:
        cpu: 0.5
        memory: 1Gi
      # limits:
      #   cpu: 0.5
      #   memory: 1Gi

  frontend:
    enabled: true
    replicaCount: 1
    resources:
      requests:
        cpu: 0.3
        memory: 512Mi
      # limits:
      #   cpu: 0.3
      #   memory: 512Mi
```

## Deploy the Hanzoflow runtime

The runtime chart is tailored for deploying applications in a production environment. It is focused on stability, performance, isolation, and security to ensure that applications run reliably and efficiently.

The `hanzoflow-runtime` Helm chart is available in the [Hanzoflow Helm Charts repository](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/tree/main/charts/hanzoflow-runtime).

:::important
By default, the [Hanzoflow runtime Helm chart](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml#L46) enables `readOnlyRootFilesystem: true` as a security best practice. This setting prevents modifications to the container's root filesystem at runtime, which is a recommended security measure in production environments.

Disabling `readOnlyRootFilesystem` reduces the security of your deployment. Only disable this setting if you understand the security implications and have implemented other security measures.

For more information, see the [Kubernetes documentation](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/).
:::

### Prerequisites

- A [Kubernetes](https://kubernetes.io/docs/setup/) server
- [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)
- [Helm](https://helm.sh/docs/intro/install/)

### Install the Hanzoflow runtime Helm chart

1. Add the repository to Helm.

```shell
helm repo add hanzoflow https://hanzoflow-ai.github.io/hanzoflow-helm-charts
helm repo update
```

2. Install the Hanzoflow app with the default options in the `hanzoflow` namespace.

If you have a created a [custom image with packaged flows](/deployment-docker#package-your-flow-as-a-docker-image), you can deploy Hanzoflow by overriding the default [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml) file with the `--set` flag.

* Use a custom image with bundled flows:
```shell
helm install my-hanzoflow-app hanzoflow/hanzoflow-runtime -n hanzoflow --create-namespace --set image.repository=myuser/hanzoflow-hello-world --set image.tag=1.0.0
```

* Alternatively, install the chart and download the flows from a URL with the `--set` flag:
```shell
helm install my-hanzoflow-app-with-flow hanzoflow/hanzoflow-runtime \
  -n hanzoflow \
  --create-namespace \
  --set 'downloadFlows.flows[0].url=https://raw.githubusercontent.com/hanzoflow-ai/hanzoflow/dev/tests/data/basic_example.json'
```

:::important
You may need to escape the square brackets in this command if you are using a shell that requires it:
```shell
helm install my-hanzoflow-app-with-flow hanzoflow/hanzoflow-runtime \
  -n hanzoflow \
  --create-namespace \
  --set 'downloadFlows.flows\[0\].url=https://raw.githubusercontent.com/hanzoflow-ai/hanzoflow/dev/tests/data/basic_example.json'
```
:::

3. Check the status of the pods.
```shell
kubectl get pods -n hanzoflow
```

### Access the Hanzoflow app API

1. Get your service name.
```shell
kubectl get svc -n hanzoflow
```

The service name is your release name followed by `-hanzoflow-runtime`. For example, if you used `helm install my-hanzoflow-app-with-flow` the service name is `my-hanzoflow-app-with-flow-hanzoflow-runtime`.

2. Enable port forwarding to access Hanzoflow from your local machine:

```shell
kubectl port-forward -n hanzoflow svc/my-hanzoflow-app-with-flow-hanzoflow-runtime 7860:7860
```

3. Confirm you can access the API at `http://localhost:7860/api/v1/flows/` and view a list of flows.
```shell
curl -v http://localhost:7860/api/v1/flows/
```

4. Execute the packaged flow.

The following command gets the first flow ID from the flows list and runs the flow.

```shell
# Get flow ID
id=$(curl -s "http://localhost:7860/api/v1/flows/" | jq -r '.[0].id')

# Run flow
curl -X POST \
    "http://localhost:7860/api/v1/run/$id?stream=false" \
    -H 'Content-Type: application/json' \
    -d '{
      "input_value": "Hello!",
      "output_type": "chat",
      "input_type": "chat"
    }'
```

### Configure secrets

To inject secrets and Hanzoflow global variables, use the `secrets` and `env` sections in the [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml) file.

For example, the [example flow JSON](https://raw.githubusercontent.com/hanzoflow-ai/hanzoflow-helm-charts/refs/heads/main/examples/flows/basic-prompting-hello-world.json) uses a global variable that is a secret. When you export the flow as JSON, it's recommended to not include the secret.

Instead, when importing the flow in the Hanzoflow runtime, you can set the global variable in one of the following ways:

<Tabs>
<TabItem value="values" label="Using values.yaml">

```yaml
env:
  - name: openai_key_var
    valueFrom:
      secretKeyRef:
        name: openai-key
        key: openai-key
```

Or directly in the values file (not recommended for secret values):

```yaml
env:
  - name: openai_key_var
    value: "sk-...."
```

</TabItem>
<TabItem value="helm" label="Using Helm Commands">

1. Create the secret:
```shell
kubectl create secret generic openai-credentials \
  --namespace hanzoflow \
  --from-literal=OPENAI_API_KEY=sk...
```

2. Verify the secret exists. The result is encrypted.
```shell
kubectl get secrets -n hanzoflow openai-credentials
```

3. Upgrade the Helm release to use the secret.
```shell
helm upgrade my-hanzoflow-app-image hanzoflow/hanzoflow-runtime -n hanzoflow \
  --reuse-values \
  --set "extraEnv[0].name=OPENAI_API_KEY" \
  --set "extraEnv[0].valueFrom.secretKeyRef.name=openai-credentials" \
  --set "extraEnv[0].valueFrom.secretKeyRef.key=OPENAI_API_KEY"
```

</TabItem>
</Tabs>

### Configure the log level

Set the log level and other Hanzoflow configurations in the [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml) file.

```yaml
env:
  - name: HANZOFLOW_LOG_LEVEL
    value: "INFO"
```

### Configure scaling

To scale the number of replicas for the Hanzoflow appplication, change the `replicaCount` value in the [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml) file.

```yaml
replicaCount: 3
```

To scale the application vertically by increasing the resources for the pods, change the `resources` values in the [values.yaml](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/values.yaml) file.


```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
```

## Deploy Hanzoflow on AWS EKS, Google GKE, or Azure AKS and other examples

For more information, see the [Hanzoflow Helm Charts repository](https://github.com/hanzoflow-ai/hanzoflow-helm-charts).


