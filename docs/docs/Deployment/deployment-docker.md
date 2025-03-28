---
title: Deploy Hanzoflow on Docker
slug: /deployment-docker
---

This guide demonstrates deploying Hanzoflow with Docker and Docker Compose.

## Prerequisites

* [Docker](https://docs.docker.com/)
* [Docker Compose](https://docs.docker.com/compose/)

## Clone the repo and build the Hanzoflow Docker container

1. Clone the Hanzoflow repository:

	`git clone https://github.com/hanzoflow-ai/hanzoflow.git`

2. Navigate to the `docker_example` directory:

	`cd hanzoflow/docker_example`

3. Run the Docker Compose file:

	`docker compose up`


Hanzoflow is now accessible at `http://localhost:7860/`.

## Configure Docker services

The Docker Compose configuration spins up two services: `hanzoflow` and `postgres`.

To configure values for these services at container startup, include them in your `.env` file.

An example `.env` file is available in the [project repository](https://github.com/hanzoflow-ai/hanzoflow/blob/main/.env.example).

To pass the `.env` values at container startup, include the flag in your `docker run` command:

```
docker run -it --rm \
    -p 7860:7860 \
    --env-file .env \
    hanzoflowai/hanzoflow:latest
```

### Hanzoflow service

The `hanzoflow`service serves both the backend API and frontend UI of the Hanzoflow web application.

The `hanzoflow` service uses the `hanzoflowai/hanzoflow:latest` Docker image and exposes port `7860`. It depends on the `postgres` service.

Environment variables:

* `HANZOFLOW_DATABASE_URL`: The connection string for the PostgreSQL database.
* `HANZOFLOW_CONFIG_DIR`: The directory where Hanzoflow stores logs, file storage, monitor data, and secret keys.

Volumes:

* `hanzoflow-data`: This volume is mapped to `/app/hanzoflow` in the container.

### PostgreSQL service

The `postgres` service is a database that stores Hanzoflow's persistent data including flows, users, and settings.

The service runs on port 5432 and includes a dedicated volume for data storage.

The `postgres` service uses the `postgres:16` Docker image.

Environment variables:

* `POSTGRES_USER`: The username for the PostgreSQL database.
* `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
* `POSTGRES_DB`: The name of the PostgreSQL database.

Volumes:

* `hanzoflow-postgres`: This volume is mapped to `/var/lib/postgresql/data` in the container.

### Deploy a specific Hanzoflow version with Docker Compose

If you want to deploy a specific version of Hanzoflow, you can modify the `image` field under the `hanzoflow` service in the Docker Compose file. For example, to use version `1.0-alpha`, change `hanzoflowai/hanzoflow:latest` to `hanzoflowai/hanzoflow:1.0-alpha`.

## Package your flow as a Docker image

You can include your Hanzoflow flow with the application image.
When you build the image, your saved flow `.JSON` flow is included.
This enables you to serve a flow from a container, push the image to Docker Hub, and deploy on Kubernetes.

An example flow is available in the [Hanzoflow Helm Charts](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/tree/main/examples/flows) repository, or you can provide your own `JSON` file.

1. Create a project directory:
```shell
mkdir hanzoflow-custom && cd hanzoflow-custom
```

2. Download the example flow or include your flow's `.JSON` file in the `hanzoflow-custom` directory.

```shell
wget https://raw.githubusercontent.com/hanzoflow-ai/hanzoflow-helm-charts/refs/heads/main/examples/flows/basic-prompting-hello-world.json
```

3. Create a Dockerfile:
```dockerfile
FROM hanzoflowai/hanzoflow-backend:latest
RUN mkdir /app/flows
COPY ./*json /app/flows/.
```
The `COPY ./*json` command copies all JSON files in your current directory to the `/flows` folder.

4. Build and run the image locally.
```shell
docker build -t myuser/hanzoflow-hello-world:1.0.0 .
docker run -p 7860:7860 myuser/hanzoflow-hello-world:1.0.0
```

5. Build and push the image to Docker Hub.
Replace `myuser` with your Docker Hub username.
```shell
docker build -t myuser/hanzoflow-hello-world:1.0.0 .
docker push myuser/hanzoflow-hello-world:1.0.0
```

To deploy the image with Helm, see [Hanzoflow runtime deployment](/deployment-kubernetes#deploy-the-hanzoflow-runtime).

