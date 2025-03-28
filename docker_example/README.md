# Running LangFlow with Docker

This guide will help you get LangFlow up and running using Docker and Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Steps

1. Clone the LangFlow repository:

   ```sh
   git clone https://github.com/hanzoflow-ai/hanzoflow.git
   ```

2. Navigate to the `docker_example` directory:

   ```sh
   cd hanzoflow/docker_example
   ```

3. Run the Docker Compose file:

   ```sh
   docker compose up
   ```

LangFlow will now be accessible at [http://localhost:7860/](http://localhost:7860/).

## Docker Compose Configuration

The Docker Compose configuration spins up two services: `hanzoflow` and `postgres`.

### LangFlow Service

The `hanzoflow` service uses the `hanzoflowai/hanzoflow:latest` Docker image and exposes port 7860. It depends on the `postgres` service.

Environment variables:

- `HANZOFLOW_DATABASE_URL`: The connection string for the PostgreSQL database.
- `HANZOFLOW_CONFIG_DIR`: The directory where LangFlow stores logs, file storage, monitor data, and secret keys.

Volumes:

- `hanzoflow-data`: This volume is mapped to `/app/hanzoflow` in the container.

### PostgreSQL Service

The `postgres` service uses the `postgres:16` Docker image and exposes port 5432.

Environment variables:

- `POSTGRES_USER`: The username for the PostgreSQL database.
- `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
- `POSTGRES_DB`: The name of the PostgreSQL database.

Volumes:

- `hanzoflow-postgres`: This volume is mapped to `/var/lib/postgresql/data` in the container.

## Switching to a Specific LangFlow Version

If you want to use a specific version of LangFlow, you can modify the `image` field under the `hanzoflow` service in the Docker Compose file. For example, to use version 1.0-alpha, change `hanzoflowai/hanzoflow:latest` to `hanzoflowai/hanzoflow:1.0-alpha`.
