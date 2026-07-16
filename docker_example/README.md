# Running Hanzo Flow with Docker

This guide will help you get Hanzo Flow up and running using Docker and Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Steps

1. Clone the Hanzo Flow repository:

   ```sh
   git clone https://github.com/hanzoai/flow.git
   ```

2. Navigate to the `docker_example` directory:

   ```sh
   cd flow/docker_example
   ```

3. Run the Docker Compose file:

   ```sh
   docker compose up
   ```

Hanzo Flow will now be accessible at [http://localhost:7860/](http://localhost:7860/).

## Docker Compose Configuration

The Docker Compose configuration spins up two services: `flow` and `postgres`.

### Hanzo Flow Service

The `flow` service uses the `flowai/flow:latest` Docker image and exposes port 7860. It depends on the `postgres` service.

Environment variables:

- `FLOW_DATABASE_URL`: The connection string for the PostgreSQL database.
- `FLOW_CONFIG_DIR`: The directory where Hanzo Flow stores logs, file storage, monitor data, and secret keys.

Volumes:

- `flow-data`: This volume is mapped to `/app/flow` in the container.

### PostgreSQL Service

The `postgres` service uses the `postgres:16-trixie` Docker image and exposes port 5432. The image is pinned to a specific Debian base (`trixie`, Debian 13) so the `postgres:16` tag cannot silently roll its underlying OS, which would otherwise produce a glibc collation version mismatch warning on existing data volumes.

Environment variables:

- `POSTGRES_USER`: The username for the PostgreSQL database.
- `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
- `POSTGRES_DB`: The name of the PostgreSQL database.

Volumes:

- `flow-postgres`: This volume is mapped to `/var/lib/postgresql/data` in the container.

## Switching to a Specific Version

If you want to use a specific version of Hanzo Flow, you can modify the `image` field under the `flow` service in the Docker Compose file. For example, to use version 1.0-alpha, change `flowai/flow:latest` to `flowai/flow:1.0-alpha`.
