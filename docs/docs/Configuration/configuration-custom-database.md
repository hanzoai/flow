---
title: Configure an external PostgreSQL database
slug: /configuration-custom-database
---
Hanzoflow's default database is [SQLite](https://www.sqlite.org/docs.html), but you can configure Hanzoflow to use PostgreSQL instead.

This guide walks you through setting up an external database for Hanzoflow by replacing the default SQLite connection string `sqlite:///./hanzoflow.db` with PostgreSQL.

## Prerequisite

* A [PostgreSQL](https://www.pgadmin.org/download/) database

## Connect Hanzoflow to PostgreSQL

To connect Hanzoflow to PostgreSQL, follow these steps.

1. Find your PostgreSQL database's connection string.
It looks like `postgresql://user:password@host:port/dbname`.

The hostname in your connection string depends on how you're running PostgreSQL.
- If you're running PostgreSQL directly on your machine, use `localhost`.
- If you're running PostgreSQL in Docker Compose, use the service name, such as `postgres`.
- If you're running PostgreSQL in a separate Docker container with `docker run`, use the container's IP address or network alias.

2. Create a `.env` file for configuring Hanzoflow.
```
touch .env
```

3. To set the database URL environment variable, add it to your `.env` file:
```text
HANZOFLOW_DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
```

:::tip
The Hanzoflow project includes a [`.env.example`](https://github.com/hanzoflow-ai/hanzoflow/blob/main/.env.example) file to help you get started.
You can copy the contents of this file into your own `.env` file and replace the example values with your own preferred settings.
Replace the value for `HANZOFLOW_DATABASE_URL` with your PostgreSQL connection string.
:::

4. Run Hanzoflow with the `.env` file:
```bash
uv run hanzoflow run --env-file .env
```

5. In Hanzoflow, create traffic by running a flow.
6. Inspect your PostgreSQL deployment's tables and activity.
New tables and traffic are created.

## Example Hanzoflow and PostgreSQL docker-compose.yml

The Hanzoflow project includes a [docker-compose.yml](https://github.com/hanzoflow-ai/hanzoflow/blob/main/docker_example/docker-compose.yml) file for quick deployment with PostgreSQL.

This configuration launches Hanzoflow and PostgreSQL containers in the same Docker network, ensuring proper connectivity between services. It also sets up persistent volumes for both Hanzoflow and PostgreSQL data.

To start the services, navigate to the `/docker_example` directory, and then run `docker-compose up`.

```yaml
services:
  hanzoflow:
    image: hanzoflowai/hanzoflow:latest    # or another version tag on https://hub.docker.com/r/hanzoflowai/hanzoflow
    pull_policy: always                   # set to 'always' when using 'latest' image
    ports:
      - "7860:7860"
    depends_on:
      - postgres
    environment:
      - HANZOFLOW_DATABASE_URL=postgresql://hanzoflow:hanzoflow@postgres:5432/hanzoflow
      # This variable defines where the logs, file storage, monitor data, and secret keys are stored.
      - HANZOFLOW_CONFIG_DIR=app/hanzoflow
    volumes:
      - hanzoflow-data:/app/hanzoflow

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: hanzoflow
      POSTGRES_PASSWORD: hanzoflow
      POSTGRES_DB: hanzoflow
    ports:
      - "5432:5432"
    volumes:
      - hanzoflow-postgres:/var/lib/postgresql/data

volumes:
  hanzoflow-postgres:    # Persistent volume for PostgreSQL data
  hanzoflow-data:        # Persistent volume for Hanzoflow data
```

:::note
Docker Compose creates an isolated network for all services defined in the docker-compose.yml file. This ensures that the services can communicate with each other using their service names as hostnames, for example, `postgres` in the database URL. If you were to run PostgreSQL separately using `docker run`, it would be in a different network and Hanzoflow wouldn't be able to connect to it using the service name.
:::

## Deploy multiple Hanzoflow instances with a shared database

To configure multiple Hanzoflow instances that share the same PostgreSQL database, modify your `docker-compose.yml` file to include multiple Hanzoflow services.

Use environment variables for more centralized configuration management:

1. Update your `.env` file with values for your PostgreSQL database:
```text
POSTGRES_USER=hanzoflow
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=hanzoflow
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
HANZOFLOW_CONFIG_DIR=app/hanzoflow
HANZOFLOW_PORT_1=7860
HANZOFLOW_PORT_2=7861
HANZOFLOW_HOST=0.0.0.0
```
2. Reference these variables in your `docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - hanzoflow-postgres:/var/lib/postgresql/data

  hanzoflow-1:
    image: hanzoflowai/hanzoflow:latest
    pull_policy: always
    ports:
      - "${HANZOFLOW_PORT_1}:7860"
    depends_on:
      - postgres
    environment:
      - HANZOFLOW_DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
      - HANZOFLOW_CONFIG_DIR=${HANZOFLOW_CONFIG_DIR}
      - HANZOFLOW_HOST=${HANZOFLOW_HOST}
      - PORT=7860
    volumes:
      - hanzoflow-data-1:/app/hanzoflow

  hanzoflow-2:
    image: hanzoflowai/hanzoflow:latest
    pull_policy: always
    ports:
      - "${HANZOFLOW_PORT_2}:7860"
    depends_on:
      - postgres
    environment:
      - HANZOFLOW_DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
      - HANZOFLOW_CONFIG_DIR=${HANZOFLOW_CONFIG_DIR}
      - HANZOFLOW_HOST=${HANZOFLOW_HOST}
      - PORT=7860
    volumes:
      - hanzoflow-data-2:/app/hanzoflow

volumes:
  hanzoflow-postgres:
  hanzoflow-data-1:
  hanzoflow-data-2:
```

3. Deploy the file with `docker-compose up`.
You can access the first Hanzoflow instance at `http://localhost:7860`, and the second Hanzoflow instance at `http://localhost:7861`.

4. To confirm both instances are using the same database, run the `docker exec` command to start `psql` in your PostgreSQL container.
Your container name may vary.
```bash
docker exec -it docker-test-postgres-1 psql -U hanzoflow -d hanzoflow
```

5. Query the database for active connections:
```sql
hanzoflow=# SELECT * FROM pg_stat_activity WHERE datname = 'hanzoflow';
```

6. Examine the query results for multiple connections with different `client_addr` values, for example `172.21.0.3` and `172.21.0.4`.

Since each Hanzoflow instance runs in its own container on the Docker network, using different incoming IP addresses confirms that both instances are actively connected to the PostgreSQL database.

7. To quit psql, type `quit`.