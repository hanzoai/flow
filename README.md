<!-- markdownlint-disable MD030 -->

![Hanzoflow logo](./docs/static/img/hanzoflow-logo-color-black-solid.svg)

[![Release Notes](https://img.shields.io/github/release/hanzoai/flow?style=flat-square)](https://github.com/hanzoai/flow/releases)
[![PyPI - License](https://img.shields.io/badge/license-MIT-orange)](https://opensource.org/licenses/MIT)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/hanzoflow?style=flat-square)](https://pypistats.org/packages/hanzoflow)

[Hanzoflow](https://hanzoflow.org) is a powerful platform for building and deploying AI-powered agents and workflows. It provides developers with both a visual authoring experience and built-in API and MCP servers that turn every workflow into a tool that can be integrated into applications built on any framework or stack. Hanzoflow comes with batteries included and supports all major LLMs, vector databases and a growing library of AI tools.

## Highlight features

- **Visual builder interface** to quickly get started and iterate.
- **Source code access** lets you customize any component using Python.
- **Interactive playground** to immediately test and refine your flows with step-by-step control.
- **Multi-agent orchestration** with conversation management and retrieval.
- **Deploy as an API** or export as JSON for Python apps.
- **Deploy as an MCP server** and turn your flows into tools for MCP clients.
- **Observability** with LangSmith, LangFuse and other integrations.
- **Enterprise-ready** security and scalability.

## Quickstart

### Install locally (recommended)

Requires Python 3.10-3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended package manager).

#### Install

From a fresh directory, run:
```shell
uv pip install hanzoflow -U
```

#### Run

To start Hanzoflow, run:
```shell
uv run hanzoflow run
```

Hanzoflow starts at http://127.0.0.1:7860.

## Other install options

### Run from source
If you've cloned this repository and want to contribute, run this command from the repository root:
```shell
make run_cli
```
For more information, see [DEVELOPMENT.md](./DEVELOPMENT.md).

### Docker
Start a Hanzoflow container with default settings:
```shell
docker run -p 7860:7860 hanzoai/flow:latest
```
Hanzoflow is available at http://localhost:7860/.

## Deployment

Hanzoflow is completely open source and you can deploy it to all major deployment clouds.

## Contribute

We welcome contributions from developers of all levels. If you'd like to contribute, please check our [contributing guidelines](./CONTRIBUTING.md) and help make Hanzoflow more accessible.

---

Based on [Langflow](https://github.com/langflow-ai/langflow) by DataStax.
