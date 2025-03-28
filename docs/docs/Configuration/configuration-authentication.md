---
title: Authentication
slug: /configuration-authentication
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

The login functionality in Hanzoflow serves to authenticate users and protect sensitive routes in the application.

## Create a superuser and new users in Hanzoflow

Learn how to create a new superuser, log in to Hanzoflow, and add new users.

1. Create a `.env` file and open it in your preferred editor.

2. Add the following environment variables to your file.

```bash
HANZOFLOW_AUTO_LOGIN=False
HANZOFLOW_SUPERUSER=admin
HANZOFLOW_SUPERUSER_PASSWORD=securepassword
HANZOFLOW_SECRET_KEY=randomly_generated_secure_key
HANZOFLOW_NEW_USER_IS_ACTIVE=False
```

For more information, see [Authentication configuration values](#values).

:::tip
The Hanzoflow project includes a [`.env.example`](https://github.com/hanzoflow-ai/hanzoflow/blob/main/.env.example) file to help you get started.
You can copy the contents of this file into your own `.env` file and replace the example values with your own preferred settings.
:::

3. Save your `.env` file.
4. Run Hanzoflow with the configured environment variables.

```bash
python -m hanzoflow run --env-file .env
```

5. Sign in with your username `admin` and password `securepassword`.
6. To open the **Admin Page**, click your user profile image, and then select **Admin Page**.
   You can also go to `http://127.0.0.1:7861/admin`.
7. To add a new user, click **New User**, and then add the **Username** and **Password**.
8. To activate the new user, select **Active**.
   The user can only sign in if you select them as **Active**.
9. To give the user `superuser` privileges, click **Superuser**.
10. Click **Save**.
11. To confirm your new user has been created, sign out of Hanzoflow, and then sign back in using your new **Username** and **Password**.

## Manage Superuser with the Hanzoflow CLI

Hanzoflow provides a command-line utility for interactively creating superusers:

1. Enter the CLI command:

```bash
hanzoflow superuser
```

2. Hanzoflow prompts you for a **Username** and **Password**:

```
hanzoflow superuser
Username: new_superuser_1
Password:
Default folder created successfully.
Superuser created successfully.
```

3. To confirm your new superuser was created successfully, go to the **Admin Page** at `http://127.0.0.1:7861/admin`.

## Authentication configuration values {#values}

The following table lists the available authentication configuration variables, their descriptions, and default values:

| Variable                      | Description                           | Default |
| ----------------------------- | ------------------------------------- | ------- |
| `HANZOFLOW_AUTO_LOGIN`         | Enables automatic login               | `True`  |
| `HANZOFLOW_SUPERUSER`          | Superuser username                    | -       |
| `HANZOFLOW_SUPERUSER_PASSWORD` | Superuser password                    | -       |
| `HANZOFLOW_SECRET_KEY`         | Key for encrypting superuser password | -       |
| `HANZOFLOW_NEW_USER_IS_ACTIVE` | Automatically activates new users     | `False` |

### HANZOFLOW_AUTO_LOGIN

By default, this variable is set to `True`. When enabled, Hanzoflow operates as it did in versions prior to 0.5, including automatic login without requiring explicit user authentication.

To disable automatic login and enforce user authentication:

```shell
HANZOFLOW_AUTO_LOGIN=False
```

### HANZOFLOW_SUPERUSER and HANZOFLOW_SUPERUSER_PASSWORD

These environment variables are only relevant when HANZOFLOW_AUTO_LOGIN is set to False. They specify the username and password for the superuser, which is essential for administrative tasks.
To create a superuser manually:

```bash
HANZOFLOW_SUPERUSER=admin
HANZOFLOW_SUPERUSER_PASSWORD=securepassword
```

### HANZOFLOW_SECRET_KEY

This environment variable holds a secret key used for encrypting sensitive data like API keys.

```bash
HANZOFLOW_SECRET_KEY=dBuuuB_FHLvU8T9eUNlxQF9ppqRxwWpXXQ42kM2_fb
```

Hanzoflow uses the [Fernet](https://pypi.org/project/cryptography/) library for secret key encryption.

### Create a HANZOFLOW_SECRET_KEY

The `HANZOFLOW_SECRET_KEY` is used for encrypting sensitive data. It must be:
- At least 32 bytes long
- URL-safe base64 encoded

1. To create a `HANZOFLOW_SECRET_KEY`, run the following command:

<Tabs>
<TabItem value="unix" label="macOS/Linux">

```bash
# Copy to clipboard (macOS)
python3 -c "from secrets import token_urlsafe; print(f'HANZOFLOW_SECRET_KEY={token_urlsafe(32)}')" | pbcopy

# Copy to clipboard (Linux)
python3 -c "from secrets import token_urlsafe; print(f'HANZOFLOW_SECRET_KEY={token_urlsafe(32)}')" | xclip -selection clipboard

# Or just print
python3 -c "from secrets import token_urlsafe; print(f'HANZOFLOW_SECRET_KEY={token_urlsafe(32)}')"
```
</TabItem>

<TabItem value="windows" label="Windows">

```bash
# Copy to clipboard
python -c "from secrets import token_urlsafe; print(f'HANZOFLOW_SECRET_KEY={token_urlsafe(32)}')" | clip

# Or just print
python -c "from secrets import token_urlsafe; print(f'HANZOFLOW_SECRET_KEY={token_urlsafe(32)}')"
```

</TabItem>
</Tabs>

The command generates a secure key like `dBuuuB_FHLvU8T9eUNlxQF9ppqRxwWpXXQ42kM2_fbg`.
Treat the generated secure key as you would an application access token. Do not commit the key to code and keep it in a safe place.

2. Create a `.env` file with the following configuration, and include your generated secret key value.
```bash
HANZOFLOW_AUTO_LOGIN=False
HANZOFLOW_SUPERUSER=admin
HANZOFLOW_SUPERUSER_PASSWORD=securepassword
HANZOFLOW_SECRET_KEY=dBuuuB_FHLvU8T9eUNlxQF9ppqRxwWpXXQ42kM2_fbg  # Your generated key
HANZOFLOW_NEW_USER_IS_ACTIVE=False
```

3. Start Hanzoflow with the values from your `.env` file.
```bash
uv run hanzoflow run --env-file .env
```

The generated secret key value is now used to encrypt your global variables.

If no key is provided, Hanzoflow will automatically generate a secure key. This is not recommended for production environments, because in a multi-instance deployment like Kubernetes, auto-generated keys won't be able to decrypt data encrypted by other instances. Instead, you should explicitly set the `HANZOFLOW_SECRET_KEY` environment variable in the deployment configuration to be the same across all instances.

### Rotate the HANZOFLOW_SECRET_KEY

To rotate the key, follow these steps.

1. Create a new `HANZOFLOW_SECRET_KEY` with the command in [Create a HANZOFLOW_SECRET_KEY](#create-a-hanzoflow_secret_key).
2. Stop your Hanzoflow instance.
3. Update the `HANZOFLOW_SECRET_KEY` in your `.env` file with the new key.
4. Restart Hanzoflow with the updated environment file:
```bash
hanzoflow run --env-file .env
```

### HANZOFLOW_NEW_USER_IS_ACTIVE

By default, this variable is set to `False`. When enabled, new users are automatically activated and can log in without requiring explicit activation by the superuser.

```bash
HANZOFLOW_NEW_USER_IS_ACTIVE=False
```