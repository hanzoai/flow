# CI/CD Pipeline Templates

Ready-to-use workflow files for the Flow DevOps Toolkit.
Copy the files you need into your project's CI configuration.

## GitHub Actions

| File | Trigger | Secrets needed |
|------|---------|----------------|
| [`github-actions/flow-validate.yml`](github-actions/flow-validate.yml) | PR touching `flows/**/*.json` | None |
| [`github-actions/flow-test.yml`](github-actions/flow-test.yml) | PR touching flows or tests | `FLOW_STAGING_API_KEY` |
| [`github-actions/flow-push.yml`](github-actions/flow-push.yml) | Push to `main` touching flows | `FLOW_PROD_API_KEY` |

### Quick start

```bash
mkdir -p .github/workflows
cp github-actions/flow-validate.yml \
   github-actions/flow-test.yml \
   github-actions/flow-push.yml \
   .github/workflows/
```

Configure these in **Settings → Environments**:

**`staging`** environment (used by `flow-test.yml`):
| Name | Type | Value |
|------|------|-------|
| `FLOW_STAGING_URL` | Variable | `https://staging.flow.example.com` |
| `FLOW_STAGING_API_KEY` | Secret | your staging API key |

**`production`** environment (used by `flow-push.yml`):
| Name | Type | Value |
|------|------|-------|
| `FLOW_PROD_URL` | Variable | `https://flow.example.com` |
| `FLOW_PROD_API_KEY` | Secret | your production API key |
| `FLOW_PROJECT_NAME` | Variable | `Production Flows` *(optional)* |

Add **Required reviewers** to the `production` environment to gate every deploy
behind a manual approval step.

---

## GitLab CI

| File | Description |
|------|-------------|
| [`gitlab-ci/flow.yml`](gitlab-ci/flow.yml) | Three-stage template: validate → test → deploy |

### Quick start

```bash
mkdir -p .gitlab/ci
cp gitlab-ci/flow.yml .gitlab/ci/
```

Add to your `.gitlab-ci.yml`:

```yaml
include:
  - local: .gitlab/ci/flow.yml
```

Configure these in **Settings → CI/CD → Variables**:

| Variable | Protected | Masked | Description |
|----------|-----------|--------|-------------|
| `FLOW_STAGING_URL` | ✓ | ✗ | Staging instance URL |
| `FLOW_STAGING_API_KEY` | ✓ | ✓ | Staging API key |
| `FLOW_PROD_URL` | ✓ | ✗ | Production instance URL |
| `FLOW_PROD_API_KEY` | ✓ | ✓ | Production API key |
| `FLOW_PROJECT_NAME` | ✗ | ✗ | Project folder name *(optional)* |

---

## Shell scripts (`ci/`)

The `shell/` templates (`ci-validate.sh`, `ci-test.sh`, `ci-push.sh`) work with
any CI system (Jenkins, CircleCI, Bitbucket Pipelines, Azure Pipelines, etc.).
They are copied to `ci/` by `lfx init`.

### Environment variables

#### `ci-validate.sh`

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOWS_DIR` | `flows/` | Directory containing flow JSON files |
| `VALIDATE_LEVEL` | `4` | Validation depth (1–4) |
| `VALIDATE_FORMAT` | `text` | Output format: `text` or `json` |
| `LFX_VERSION` | *(latest)* | PEP 508 version specifier for `lfx`, e.g. `>=0.4,<1` or `==1.2.3` |

#### `ci-test.sh`

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOW_URL` | — | URL of target Hanzo Flow instance (Approach A) |
| `FLOW_API_KEY` | — | API key for target instance (Approach A) |
| `FLOW_ENV` | — | Environment name from config (Approach B) |
| `FLOW_ENVIRONMENTS_FILE` | `flow-environments.toml` | Path to environments config (Approach B) |
| `TESTS_DIR` | `tests/` | Directory containing test files |
| `PYTEST_MARKERS` | `integration` | Markers passed to `pytest -m` |
| `PYTEST_ARGS` | — | Extra arguments forwarded verbatim to pytest |
| `SDK_VERSION` | *(latest)* | PEP 508 version specifier for `flow-sdk` |

#### `ci-push.sh`

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOW_URL` | — | URL of target Hanzo Flow instance (Approach A) |
| `FLOW_API_KEY` | — | API key for target instance (Approach A) |
| `FLOW_ENV` | — | Environment name from config (Approach B) |
| `FLOW_ENVIRONMENTS_FILE` | `flow-environments.toml` | Path to environments config (Approach B) |
| `FLOWS_DIR` | `flows/` | Directory containing flow JSON files |
| `FLOW_PROJECT` | — | Project (folder) name on the remote instance |
| `FLOW_PROJECT_ID` | — | Project UUID (takes precedence over `FLOW_PROJECT`) |
| `DRY_RUN` | `false` | Set to `true` to preview without making changes |
| `LFX_VERSION` | *(latest)* | PEP 508 version specifier for `lfx` |

---

## How it all fits together

```
PR opened
  │
  ├── flow-validate  ──── lfx validate flows/ --level 4
  │                           ↳ blocks merge if any flow is malformed
  │
  └── flow-test  ──────── pytest tests/ --flow-env staging
                              ↳ skips gracefully if staging is unavailable

Merge to main
  │
  └── flow-push  ──────── lfx push --dir flows/ --env production
                              ↳ upserts every flow by stable ID
                              ↳ idempotent: safe to re-run
```

## Writing integration tests

Install the testing extra:

```bash
pip install "flow-sdk[testing]"
```

Create `tests/test_flows.py`:

```python
def test_rag_flow(flow_runner):
    response = flow_runner("rag-endpoint", "What is Hanzo Flow?")
    assert "Hanzo Flow" in response.first_text_output()

async def test_async_flow(async_flow_runner):
    response = await async_flow_runner("my-endpoint", "Hello!")
    assert response.first_text_output() is not None
```

Run locally against staging:

```bash
FLOW_URL=https://staging.flow.example.com \
FLOW_API_KEY=<key> \
pytest tests/ -m integration
```
