---
title: Environment variables
slug: /environment-variables
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import Link from '@docusaurus/Link';


Hanzoflow lets you configure a number of settings using environment variables.

## Configure environment variables

Hanzoflow recognizes [supported environment variables](#supported-variables) from the following sources:

- Environment variables that you've set in your terminal.
- Environment variables that you've imported from a `.env` file using the `--env-file` option in the Hanzoflow CLI.

You can choose to use one source exclusively, or use both sources together.
If you choose to use both sources together, be aware that environment variables imported from a `.env` file take [precedence](#precedence) over those set in your terminal.

### Set environment variables in your terminal {#configure-variables-terminal}

Run the following commands to set environment variables for your current terminal session:

<Tabs>

<TabItem value="linux-macos" label="Linux or macOS" default>
```bash
export VARIABLE_NAME='VALUE'
```
</TabItem>

<TabItem value="windows" label="Windows" default>
```
set VARIABLE_NAME='VALUE'
```
</TabItem>

<TabItem value="docker" label="Docker" default>
```bash
docker run -it --rm \
    -p 7860:7860 \
    -e VARIABLE_NAME='VALUE' \
    hanzoflowai/hanzoflow:latest
```
</TabItem>

</Tabs>

When you start Hanzoflow, it looks for environment variables that you've set in your terminal.
If it detects a supported environment variable, then it automatically adopts the specified value, subject to [precedence rules](#precedence).

### Import environment variables from a .env file {#configure-variables-env-file}

1. Create a `.env` file and open it in your preferred editor.

2. Add your environment variables to the file:

    ```plaintext title=".env"
    VARIABLE_NAME='VALUE'
    VARIABLE_NAME='VALUE'
    ```

    :::tip
    The Hanzoflow project includes a [`.env.example`](https://github.com/hanzoflow-ai/hanzoflow/blob/main/.env.example) file to help you get started.
    You can copy the contents of this file into your own `.env` file and replace the example values with your own preferred settings.
    :::

3. Save and close the file.

4. Start Hanzoflow using the `--env-file` option to define the path to your `.env` file:

   <Tabs>

    <TabItem value="local" label="Local" default>
    ```bash
    python -m hanzoflow run --env-file .env
    ```
    </TabItem>

    <TabItem value="docker" label="Docker" default>
    ```bash
    docker run -it --rm \
        -p 7860:7860 \
        --env-file .env \
        hanzoflowai/hanzoflow:latest
    ```
    </TabItem>

    </Tabs>

On startup, Hanzoflow imports the environment variables from your `.env` file, as well as any that you [set in your terminal](#configure-variables-terminal), and adopts their specified values.

## Precedence {#precedence}

Environment variables [defined in the .env file](#configure-variables-env-file) take precedence over those [set in your terminal](#configure-variables-terminal).
That means, if you happen to set the same environment variable in both your terminal and your `.env` file, Hanzoflow adopts the value from the the `.env` file.

:::info[CLI precedence]
[Hanzoflow CLI options](./configuration-cli.md) override the value of corresponding environment variables defined in the `.env` file as well as any environment variables set in your terminal.
:::

## Supported environment variables {#supported-variables}

The following table lists the environment variables supported by Hanzoflow.

| Variable | Format / Values | Default | Description |
|----------|---------------|---------|-------------|
| <Link id="DO_NOT_TRACK"/>`DO_NOT_TRACK` | Boolean | `false` | If enabled, Hanzoflow will not track telemetry. |
| <Link id="HANZOFLOW_AUTO_LOGIN"/>`HANZOFLOW_AUTO_LOGIN` | Boolean | `true` | Enable automatic login for Hanzoflow. Set to `false` to disable automatic login and require the login form to log into the Hanzoflow UI. Setting to `false` requires [`HANZOFLOW_SUPERUSER`](#HANZOFLOW_SUPERUSER) and [`HANZOFLOW_SUPERUSER_PASSWORD`](environment-variables.md#HANZOFLOW_SUPERUSER_PASSWORD) to be set. |
| <Link id="HANZOFLOW_AUTO_SAVING"/>`HANZOFLOW_AUTO_SAVING` | Boolean | `true` | Enable flow auto-saving.<br/>See [`--auto-saving` option](./configuration-cli.md#run-auto-saving). |
| <Link id="HANZOFLOW_AUTO_SAVING_INTERVAL"/>`HANZOFLOW_AUTO_SAVING_INTERVAL` | Integer | `1000` | Set the interval for flow auto-saving in milliseconds.<br/>See [`--auto-saving-interval` option](./configuration-cli.md#run-auto-saving-interval). |
| <Link id="HANZOFLOW_BACKEND_ONLY"/>`HANZOFLOW_BACKEND_ONLY` | Boolean | `false` | Only run Hanzoflow's backend server (no frontend).<br/>See [`--backend-only` option](./configuration-cli.md#run-backend-only). |
| <Link id="HANZOFLOW_CACHE_TYPE"/>`HANZOFLOW_CACHE_TYPE` | `async`<br/>`redis`<br/>`memory`<br/>`disk`<br/>`critical` | `async` | Set the cache type for Hanzoflow.<br/>If you set the type to `redis`, then you must also set the following environment variables: [`HANZOFLOW_REDIS_HOST`](#HANZOFLOW_REDIS_HOST), [`HANZOFLOW_REDIS_PORT`](#HANZOFLOW_REDIS_PORT), [`HANZOFLOW_REDIS_DB`](#HANZOFLOW_REDIS_DB), and [`HANZOFLOW_REDIS_CACHE_EXPIRE`](#HANZOFLOW_REDIS_CACHE_EXPIRE). |
| <Link id="HANZOFLOW_COMPONENTS_PATH"/>`HANZOFLOW_COMPONENTS_PATH` | String | `hanzoflow/components` | Path to the directory containing custom components.<br/>See [`--components-path` option](./configuration-cli.md#run-components-path). |
| <Link id="HANZOFLOW_CONFIG_DIR"/>`HANZOFLOW_CONFIG_DIR` | String | **Linux/WSL**: `~/.cache/hanzoflow/`<br/>**macOS**: `/Users/<username>/Library/Caches/hanzoflow/`<br/>**Windows**: `%LOCALAPPDATA%\hanzoflow\hanzoflow\Cache` | Set the Hanzoflow configuration directory where files, logs, and the Hanzoflow database are stored. |
| <Link id="HANZOFLOW_DATABASE_URL"/>`HANZOFLOW_DATABASE_URL` | String | Not set | Set the database URL for Hanzoflow. If not provided, Hanzoflow will use a SQLite database. |
| <Link id="HANZOFLOW_DATABASE_CONNECTION_RETRY"/>`HANZOFLOW_DATABASE_CONNECTION_RETRY` | Boolean | `false` | If True, Hanzoflow will retry to connect to the database if it fails. |
| <Link id="HANZOFLOW_DB_POOL_SIZE"/>`HANZOFLOW_DB_POOL_SIZE` | Integer | `10` | **DEPRECATED:** Use `HANZOFLOW_DB_CONNECTION_SETTINGS` instead. The number of connections to keep open in the connection pool. |
| <Link id="HANZOFLOW_DB_MAX_OVERFLOW"/>`HANZOFLOW_DB_MAX_OVERFLOW` | Integer | `20` | **DEPRECATED:** Use `HANZOFLOW_DB_CONNECTION_SETTINGS` instead. The number of connections to allow that can be opened beyond the pool size. |
| <Link id="HANZOFLOW_DB_CONNECT_TIMEOUT"/>`HANZOFLOW_DB_CONNECT_TIMEOUT` | Integer | `20` | The number of seconds to wait before giving up on a lock to be released or establishing a connection to the database. |
| <Link id="HANZOFLOW_DB_CONNECTION_SETTINGS"/>`HANZOFLOW_DB_CONNECTION_SETTINGS` | JSON | Not set | A JSON dictionary to centralize database connection parameters. Example: `{"pool_size": 10, "max_overflow": 20}` |
| <Link id="HANZOFLOW_DEV"/>`HANZOFLOW_DEV` | Boolean | `false` | Run Hanzoflow in development mode (may contain bugs).<br/>See [`--dev` option](./configuration-cli.md#run-dev). |
| <Link id="HANZOFLOW_FALLBACK_TO_ENV_VAR"/>`HANZOFLOW_FALLBACK_TO_ENV_VAR` | Boolean | `true` | If enabled, [global variables](../Configuration/configuration-global-variables.md) set in the Hanzoflow UI fall back to an environment variable with the same name when Hanzoflow fails to retrieve the variable value. |
| <Link id="HANZOFLOW_FRONTEND_PATH"/>`HANZOFLOW_FRONTEND_PATH` | String | `./frontend` | Path to the frontend directory containing build files. This is for development purposes only.<br/>See [`--frontend-path` option](./configuration-cli.md#run-frontend-path). |
| <Link id="HANZOFLOW_HEALTH_CHECK_MAX_RETRIES"/>`HANZOFLOW_HEALTH_CHECK_MAX_RETRIES` | Integer | `5` | Set the maximum number of retries for the health check.<br/>See [`--health-check-max-retries` option](./configuration-cli.md#run-health-check-max-retries). |
| <Link id="HANZOFLOW_HOST"/>`HANZOFLOW_HOST` | String | `127.0.0.1` | The host on which the Hanzoflow server will run.<br/>See [`--host` option](./configuration-cli.md#run-host). |
| <Link id="HANZOFLOW_LANGCHAIN_CACHE"/>`HANZOFLOW_LANGCHAIN_CACHE` | `InMemoryCache`<br/>`SQLiteCache` | `InMemoryCache` | Type of cache to use.<br/>See [`--cache` option](./configuration-cli.md#run-cache). |
| <Link id="HANZOFLOW_LOG_LEVEL"/>`HANZOFLOW_LOG_LEVEL` | `DEBUG`<br/>`INFO`<br/>`WARNING`<br/>`ERROR`<br/>`CRITICAL` | `INFO` | Set the logging level for Hanzoflow. |
| <Link id="HANZOFLOW_LOG_FILE"/>`HANZOFLOW_LOG_FILE` | String | Not set | Path to the log file. If not set, logs will be written to stdout. |
| <Link id="HANZOFLOW_MAX_FILE_SIZE_UPLOAD"/>`HANZOFLOW_MAX_FILE_SIZE_UPLOAD` | Integer | `100` | Set the maximum file size for the upload in megabytes.<br/>See [`--max-file-size-upload` option](./configuration-cli.md#run-max-file-size-upload). |
| <Link id="HANZOFLOW_MCP_SERVER_ENABLED"/>`HANZOFLOW_MCP_SERVER_ENABLED` | Boolean | `true` | If set to False, Hanzoflow will not enable the MCP server. |
| <Link id="HANZOFLOW_MCP_SERVER_ENABLE_PROGRESS_NOTIFICATIONS"/>`HANZOFLOW_MCP_SERVER_ENABLE_PROGRESS_NOTIFICATIONS` | Boolean | `false` | If set to True, Hanzoflow will send progress notifications in the MCP server. |
| <Link id="HANZOFLOW_NEW_USER_IS_ACTIVE"/>`HANZOFLOW_NEW_USER_IS_ACTIVE` | Boolean | `false` | When enabled, new users are automatically activated and can log in without requiring explicit activation by the superuser. |
| <Link id="HANZOFLOW_OPEN_BROWSER"/>`HANZOFLOW_OPEN_BROWSER` | Boolean | `false` | Open the system web browser on startup.<br/>See [`--open-browser` option](./configuration-cli.md#run-open-browser). |
| <Link id="HANZOFLOW_PORT"/>`HANZOFLOW_PORT` | Integer | `7860` | The port on which the Hanzoflow server will run. The server automatically selects a free port if the specified port is in use.<br/>See [`--port` option](./configuration-cli.md#run-port). |
| <Link id="HANZOFLOW_PROMETHEUS_ENABLED"/>`HANZOFLOW_PROMETHEUS_ENABLED` | Boolean | `false` | Expose Prometheus metrics. |
| <Link id="HANZOFLOW_PROMETHEUS_PORT"/>`HANZOFLOW_PROMETHEUS_PORT` | Integer | `9090` | Set the port on which Hanzoflow exposes Prometheus metrics. |
| <Link id="HANZOFLOW_REDIS_CACHE_EXPIRE"/>`HANZOFLOW_REDIS_CACHE_EXPIRE` | Integer | `3600` | See [`HANZOFLOW_CACHE_TYPE`](#HANZOFLOW_CACHE_TYPE). |
| <Link id="HANZOFLOW_REDIS_DB"/>`HANZOFLOW_REDIS_DB` | Integer | `0` | See [`HANZOFLOW_CACHE_TYPE`](#HANZOFLOW_CACHE_TYPE). |
| <Link id="HANZOFLOW_REDIS_HOST"/>`HANZOFLOW_REDIS_HOST` | String | `localhost` | See [`HANZOFLOW_CACHE_TYPE`](#HANZOFLOW_CACHE_TYPE). |
| <Link id="HANZOFLOW_REDIS_PORT"/>`HANZOFLOW_REDIS_PORT` | String | `6379` | See [`HANZOFLOW_CACHE_TYPE`](#HANZOFLOW_CACHE_TYPE). |
| <Link id="HANZOFLOW_REMOVE_API_KEYS"/>`HANZOFLOW_REMOVE_API_KEYS` | Boolean | `false` | Remove API keys from the projects saved in the database.<br/>See [`--remove-api-keys` option](./configuration-cli.md#run-remove-api-keys). |
| <Link id="HANZOFLOW_SAVE_DB_IN_CONFIG_DIR"/>`HANZOFLOW_SAVE_DB_IN_CONFIG_DIR` | Boolean | `false` | Save the Hanzoflow database in [`HANZOFLOW_CONFIG_DIR`](#HANZOFLOW_CONFIG_DIR) instead of in the Hanzoflow package directory. Note, when this variable is set to default (`false`), the database isn't shared between different virtual environments and the database is deleted when you uninstall Hanzoflow. |
| <Link id="HANZOFLOW_SECRET_KEY"/>`HANZOFLOW_SECRET_KEY` | String | Auto-generated | Key used for encrypting sensitive data like API keys. If not provided, a secure key will be auto-generated. For production environments with multiple instances, you should explicitly set this to ensure consistent encryption across instances. |
| <Link id="HANZOFLOW_STORE"/>`HANZOFLOW_STORE` | Boolean | `true` | Enable the Hanzoflow Store.<br/>See [`--store` option](./configuration-cli.md#run-store). |
| <Link id="HANZOFLOW_STORE_ENVIRONMENT_VARIABLES"/>`HANZOFLOW_STORE_ENVIRONMENT_VARIABLES` | Boolean | `true` | Store environment variables as [global variables](../Configuration/configuration-global-variables.md) in the database. |
| <Link id="HANZOFLOW_SUPERUSER"/>`HANZOFLOW_SUPERUSER` | String | `hanzoflow` | Set the name for the superuser. Required if [`HANZOFLOW_AUTO_LOGIN`](#HANZOFLOW_AUTO_LOGIN) is set to `false`.<br/>See [`superuser --username` option](./configuration-cli.md#superuser-username). |
| <Link id="HANZOFLOW_SUPERUSER_PASSWORD"/>`HANZOFLOW_SUPERUSER_PASSWORD` | String | `hanzoflow` | Set the password for the superuser. Required if [`HANZOFLOW_AUTO_LOGIN`](#HANZOFLOW_AUTO_LOGIN) is set to `false`.<br/>See [`superuser --password` option](./configuration-cli.md#superuser-password). |
| <Link id="HANZOFLOW_VARIABLES_TO_GET_FROM_ENVIRONMENT"/>`HANZOFLOW_VARIABLES_TO_GET_FROM_ENVIRONMENT` | String | Not set | Comma-separated list of environment variables to get from the environment and store as [global variables](../Configuration/configuration-global-variables.md). |
| <Link id="HANZOFLOW_LOAD_FLOWS_PATH"/>`HANZOFLOW_LOAD_FLOWS_PATH` | String | Not set | Path to a directory containing flow JSON files to be loaded on startup. Note that this feature only works if `HANZOFLOW_AUTO_LOGIN` is enabled. |
| <Link id="HANZOFLOW_WORKER_TIMEOUT"/>`HANZOFLOW_WORKER_TIMEOUT` | Integer | `300` | Worker timeout in seconds.<br/>See [`--worker-timeout` option](./configuration-cli.md#run-worker-timeout). |
| <Link id="HANZOFLOW_WORKERS"/>`HANZOFLOW_WORKERS` | Integer | `1` | Number of worker processes.<br/>See [`--workers` option](./configuration-cli.md#run-workers). |

## Configure .env, override.conf, and tasks.json files

The following examples show how to configure Hanzoflow using environment variables in different scenarios.

<Tabs>
<TabItem value="env" label=".env File" default>

The `.env` file is a text file that contains key-value pairs of environment variables.

Create or edit a file named `.env` in your project root directory and add your configuration:

```plaintext title=".env"
DO_NOT_TRACK=true
HANZOFLOW_AUTO_LOGIN=false
HANZOFLOW_AUTO_SAVING=true
HANZOFLOW_AUTO_SAVING_INTERVAL=1000
HANZOFLOW_BACKEND_ONLY=false
HANZOFLOW_CACHE_TYPE=async
HANZOFLOW_COMPONENTS_PATH=/path/to/components/
HANZOFLOW_CONFIG_DIR=/path/to/config/
HANZOFLOW_DATABASE_URL=postgresql://user:password@localhost:5432/hanzoflow
HANZOFLOW_DEV=false
HANZOFLOW_FALLBACK_TO_ENV_VAR=false
HANZOFLOW_HEALTH_CHECK_MAX_RETRIES=5
HANZOFLOW_HOST=127.0.0.1
HANZOFLOW_LANGCHAIN_CACHE=InMemoryCache
HANZOFLOW_MAX_FILE_SIZE_UPLOAD=10000
HANZOFLOW_LOG_LEVEL=error
HANZOFLOW_OPEN_BROWSER=false
HANZOFLOW_PORT=7860
HANZOFLOW_REMOVE_API_KEYS=false
HANZOFLOW_SAVE_DB_IN_CONFIG_DIR=true
HANZOFLOW_SECRET_KEY=somesecretkey
HANZOFLOW_STORE=true
HANZOFLOW_STORE_ENVIRONMENT_VARIABLES=true
HANZOFLOW_SUPERUSER=adminuser
HANZOFLOW_SUPERUSER_PASSWORD=adminpass
HANZOFLOW_WORKER_TIMEOUT=60000
HANZOFLOW_WORKERS=3
```

</TabItem>
<TabItem value="systemd" label="Systemd service">

A systemd service configuration file configures Linux system services.

To add environment variables, create or edit a service configuration file and add an `override.conf` file. This file allows you to override the default environment variables for the service.

```ini title="override.conf"
[Service]
Environment="DO_NOT_TRACK=true"
Environment="HANZOFLOW_AUTO_LOGIN=false"
Environment="HANZOFLOW_AUTO_SAVING=true"
Environment="HANZOFLOW_AUTO_SAVING_INTERVAL=1000"
Environment="HANZOFLOW_BACKEND_ONLY=false"
Environment="HANZOFLOW_CACHE_TYPE=async"
Environment="HANZOFLOW_COMPONENTS_PATH=/path/to/components/"
Environment="HANZOFLOW_CONFIG_DIR=/path/to/config"
Environment="HANZOFLOW_DATABASE_URL=postgresql://user:password@localhost:5432/hanzoflow"
Environment="HANZOFLOW_DEV=false"
Environment="HANZOFLOW_FALLBACK_TO_ENV_VAR=false"
Environment="HANZOFLOW_HEALTH_CHECK_MAX_RETRIES=5"
Environment="HANZOFLOW_HOST=127.0.0.1"
Environment="HANZOFLOW_LANGCHAIN_CACHE=InMemoryCache"
Environment="HANZOFLOW_MAX_FILE_SIZE_UPLOAD=10000"
Environment="HANZOFLOW_LOG_ENV=container_json"
Environment="HANZOFLOW_LOG_FILE=logs/hanzoflow.log"
Environment="HANZOFLOW_LOG_LEVEL=error"
Environment="HANZOFLOW_OPEN_BROWSER=false"
Environment="HANZOFLOW_PORT=7860"
Environment="HANZOFLOW_REMOVE_API_KEYS=false"
Environment="HANZOFLOW_SAVE_DB_IN_CONFIG_DIR=true"
Environment="HANZOFLOW_SECRET_KEY=somesecretkey"
Environment="HANZOFLOW_STORE=true"
Environment="HANZOFLOW_STORE_ENVIRONMENT_VARIABLES=true"
Environment="HANZOFLOW_SUPERUSER=adminuser"
Environment="HANZOFLOW_SUPERUSER_PASSWORD=adminpass"
Environment="HANZOFLOW_WORKER_TIMEOUT=60000"
Environment="HANZOFLOW_WORKERS=3"
```

For more information on systemd, see the [Red Hat documentation](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/using_systemd_unit_files_to_customize_and_optimize_your_system/assembly_working-with-systemd-unit-files_working-with-systemd#assembly_working-with-systemd-unit-files_working-with-systemd).

</TabItem>
<TabItem value="vscode" label="VSCode tasks.json">

The `tasks.json` file located in `.vscode/tasks.json` is a configuration file for development environments using Visual Studio Code.

Create or edit the `.vscode/tasks.json` file in your project root:

```json title=".vscode/tasks.json"
{
    "version": "2.0.0",
    "options": {
        "env": {
            "DO_NOT_TRACK": "true",
            "HANZOFLOW_AUTO_LOGIN": "false",
            "HANZOFLOW_AUTO_SAVING": "true",
            "HANZOFLOW_AUTO_SAVING_INTERVAL": "1000",
            "HANZOFLOW_BACKEND_ONLY": "false",
            "HANZOFLOW_CACHE_TYPE": "async",
            "HANZOFLOW_COMPONENTS_PATH": "D:/path/to/components/",
            "HANZOFLOW_CONFIG_DIR": "D:/path/to/config/",
            "HANZOFLOW_DATABASE_URL": "postgresql://postgres:password@localhost:5432/hanzoflow",
            "HANZOFLOW_DEV": "false",
            "HANZOFLOW_FALLBACK_TO_ENV_VAR": "false",
            "HANZOFLOW_HEALTH_CHECK_MAX_RETRIES": "5",
            "HANZOFLOW_HOST": "localhost",
            "HANZOFLOW_LANGCHAIN_CACHE": "InMemoryCache",
            "HANZOFLOW_MAX_FILE_SIZE_UPLOAD": "10000",
            "HANZOFLOW_LOG_ENV": "container_csv",
            "HANZOFLOW_LOG_FILE": "hanzoflow.log",
            "HANZOFLOW_LOG_LEVEL": "error",
            "HANZOFLOW_OPEN_BROWSER": "false",
            "HANZOFLOW_PORT": "7860",
            "HANZOFLOW_REMOVE_API_KEYS": "true",
            "HANZOFLOW_SAVE_DB_IN_CONFIG_DIR": "false",
            "HANZOFLOW_SECRET_KEY": "somesecretkey",
            "HANZOFLOW_STORE": "true",
            "HANZOFLOW_STORE_ENVIRONMENT_VARIABLES": "true",
            "HANZOFLOW_SUPERUSER": "adminuser",
            "HANZOFLOW_SUPERUSER_PASSWORD": "adminpass",
            "HANZOFLOW_WORKER_TIMEOUT": "60000",
            "HANZOFLOW_WORKERS": "3"
        }
    },
    "tasks": [
        {
            "label": "hanzoflow backend",
            "type": "shell",
            "command": ". ./hanzoflownightly/Scripts/activate && hanzoflow run",
            "isBackground": true,
            "problemMatcher": []
        }
    ]
}
```

To run Hanzoflow using the above VSCode `tasks.json` file, in the VSCode command palette, select **Tasks: Run Task** > **hanzoflow backend**.

</TabItem>
</Tabs>
