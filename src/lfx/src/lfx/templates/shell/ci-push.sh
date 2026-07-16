#!/usr/bin/env bash
# ci-push.sh
#
# PURPOSE
#   Push (upsert) Hanzo Flow flow JSON files to a remote Hanzo Flow instance
#   using `lfx push`.  Stable flow IDs mean re-running always converges.
#
# USAGE
#   chmod +x ci-push.sh
#   export FLOW_URL=https://staging.flow.example.com
#   export FLOW_API_KEY=<your-api-key>
#   ./ci-push.sh
#
# ENVIRONMENT VARIABLES — connection (pick one approach)
#
#   Approach A: direct URL + key (simplest)
#     FLOW_URL        URL of the target Hanzo Flow instance.
#     FLOW_API_KEY    API key for that instance.
#
#   Approach B: named environment from a TOML config
#     FLOW_ENV                 Name of the environment block.
#                                  e.g. staging  or  production
#     FLOW_ENVIRONMENTS_FILE   Path to environments TOML.
#                                  Default: flow-environments.toml
#     <api_key_env var>            The env var named in api_key_env inside the
#                                  TOML block.  Must be exported separately.
#
#   The TOML format:
#
#     [environments.staging]
#     url         = "https://staging.flow.example.com"
#     api_key_env  = "FLOW_STAGING_API_KEY"
#
#     [environments.production]
#     url         = "https://flow.example.com"
#     api_key_env  = "FLOW_PROD_API_KEY"
#
# ENVIRONMENT VARIABLES — behaviour
#   FLOWS_DIR            Directory containing flow JSON files.
#                        Default: flows/
#   FLOW_PROJECT     Project (folder) name on the remote instance.
#                        Default: (no project — flows go to the default folder)
#   FLOW_PROJECT_ID  Project UUID.  Takes precedence over FLOW_PROJECT.
#   DRY_RUN              Set to "true" to show what would be pushed without
#                        making any changes.  Default: false
#   LFX_VERSION          lfx PEP 508 version specifier suffix appended directly
#                        to the package name, e.g. ">=0.4,<1" or "==1.2.3".
#                        Default: installs latest.
#
# EXIT CODES
#   0  All flows pushed (or dry-run completed) successfully
#   1  One or more flows failed to push
#
# INTEGRATIONS
#   Jenkins:          sh 'ci-push.sh'
#   CircleCI:         - run: bash ci-push.sh
#   Bitbucket:        - bash ci-push.sh
#   Azure Pipelines:  - script: bash ci-push.sh

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────── #

FLOWS_DIR="${FLOWS_DIR:-flows/}"
FLOW_ENV="${FLOW_ENV:-}"
FLOW_ENVIRONMENTS_FILE="${FLOW_ENVIRONMENTS_FILE:-flow-environments.toml}"
FLOW_URL="${FLOW_URL:-}"
FLOW_API_KEY="${FLOW_API_KEY:-}"
FLOW_PROJECT="${FLOW_PROJECT:-}"
FLOW_PROJECT_ID="${FLOW_PROJECT_ID:-}"
DRY_RUN="${DRY_RUN:-false}"
LFX_VERSION="${LFX_VERSION:-}"

# Normalise LFX_VERSION: if it looks like a bare version (starts with a digit),
# prepend "==" so the pip specifier is valid.
if [[ -n "${LFX_VERSION}" && "${LFX_VERSION}" =~ ^[0-9] ]]; then
  LFX_VERSION="==${LFX_VERSION}"
fi

# ── Install lfx ───────────────────────────────────────────────────────────── #

echo "==> Installing lfx${LFX_VERSION:+ ${LFX_VERSION}} ..."
pip install --quiet "lfx${LFX_VERSION}" flow-sdk

# ── Build environments file if using Approach B ───────────────────────────── #

if [[ -n "${FLOW_ENV}" && ! -f "${FLOW_ENVIRONMENTS_FILE}" ]]; then
  ENV_UPPER="${FLOW_ENV^^}"
  ENV_UPPER="${ENV_UPPER//-/_}"
  URL_VAR="FLOW_${ENV_UPPER}_URL"
  KEY_VAR="FLOW_${ENV_UPPER}_API_KEY"

  echo "==> Writing ${FLOW_ENVIRONMENTS_FILE} for environment '${FLOW_ENV}' ..."
  printf '[environments.%s]\nurl = "%s"\napi_key_env = "%s"\n' \
    "${FLOW_ENV}" \
    "${!URL_VAR:-}" \
    "${KEY_VAR}" \
    > "${FLOW_ENVIRONMENTS_FILE}"
  export FLOW_ENVIRONMENTS_FILE
fi

# ── Build lfx push command ────────────────────────────────────────────────── #

PUSH_CMD=(lfx push --dir "${FLOWS_DIR}")

if [[ -n "${FLOW_ENV}" ]]; then
  PUSH_CMD+=(--env "${FLOW_ENV}")
elif [[ -n "${FLOW_URL}" ]]; then
  PUSH_CMD+=(--target "${FLOW_URL}")
  [[ -n "${FLOW_API_KEY}" ]] && PUSH_CMD+=(--api-key "${FLOW_API_KEY}")
else
  echo "ERROR: set FLOW_ENV (Approach B) or FLOW_URL (Approach A)" >&2
  exit 1
fi

if [[ -n "${FLOW_PROJECT_ID}" ]]; then
  PUSH_CMD+=(--project-id "${FLOW_PROJECT_ID}")
elif [[ -n "${FLOW_PROJECT}" ]]; then
  PUSH_CMD+=(--project "${FLOW_PROJECT}")
fi

[[ "${DRY_RUN}" == "true" ]] && PUSH_CMD+=(--dry-run)

# ── Push ──────────────────────────────────────────────────────────────────── #

echo "==> Pushing flows from ${FLOWS_DIR} ..."
[[ "${DRY_RUN}" == "true" ]] && echo "    (dry run — no changes will be made)"
echo "==> Running: ${PUSH_CMD[*]}"
"${PUSH_CMD[@]}"

echo "==> Done."
