---
title: Security best practices
slug: /configuration-security-best-practices
---

This guide outlines security best practices for deploying and managing Hanzoflow.

## Secret key protection

The secret key is critical for encrypting sensitive data in Hanzoflow. Follow these guidelines:

- Always use a custom secret key in production:

  ```bash
  HANZOFLOW_SECRET_KEY=your-secure-secret-key
  ```

- Store the secret key securely:

  - Use environment variables or secure secret management systems.
  - Never commit the secret key to version control.
  - Regularly rotate the secret key.

- Use the default secret key locations:
  - macOS: `~/Library/Caches/hanzoflow/secret_key`
  - Linux: `~/.cache/hanzoflow/secret_key`
  - Windows: `%USERPROFILE%\AppData\Local\hanzoflow\secret_key`

## API keys and credentials

- Store API keys and credentials as encrypted global variables.
- Use the Credential type for sensitive information.
- Implement proper access controls for users who can view/edit credentials.
- Regularly audit and rotate API keys.

## Database file protection

- Store the database in a secure location:

   ```bash
   HANZOFLOW_SAVE_DB_IN_CONFIG_DIR=true
   HANZOFLOW_CONFIG_DIR=/secure/path/to/config
   ```

- Use the default database locations:
   - macOS/Linux: `PYTHON_LOCATION/site-packages/hanzoflow/hanzoflow.db`
   - Windows: `PYTHON_LOCATION\Lib\site-packages\hanzoflow\hanzoflow.db`
