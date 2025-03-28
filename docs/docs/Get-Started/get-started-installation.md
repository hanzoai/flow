---
title: Install Hanzoflow
slug: /get-started-installation
---

You can deploy Hanzoflow either locally or as a hosted service with [**Datastax Hanzoflow**](#datastax-hanzoflow).

## Install Hanzoflow locally

Install Hanzoflow locally with [uv (recommended)](https://docs.astral.sh/uv/getting-started/installation/), [pip](https://pypi.org/project/pip/), or [pipx](https://pipx.pypa.io/stable/installation/).

### Prerequisites

- [Python 3.10 to 3.13](https://www.python.org/downloads/release/python-3100/) installed
- [uv](https://docs.astral.sh/uv/getting-started/installation/), [pip](https://pypi.org/project/pip/), or [pipx](https://pipx.pypa.io/stable/installation/) installed
- Before installing Hanzoflow, we recommend creating a virtual environment to isolate your Python dependencies with [uv](https://docs.astral.sh/uv/pip/environments), [venv](https://docs.python.org/3/library/venv.html), or [conda](https://anaconda.org/anaconda/conda)

### Install Hanzoflow with pip or pipx

Install Hanzoflow with uv:

```bash
uv pip install hanzoflow
```

Install Hanzoflow with pip:

```bash
python -m pip install hanzoflow
```

Install Hanzoflow with pipx using the Python 3.10 executable:

```bash
pipx install hanzoflow --python python3.10
```

## Run Hanzoflow

1. To run Hanzoflow with uv, enter the following command.

```bash
uv run hanzoflow run
```

2. To run Hanzoflow with pip, enter the following command.

```bash
python -m hanzoflow run
```

3. Confirm that a local Hanzoflow instance starts by visiting `http://127.0.0.1:7860` in a Chromium-based browser.

Now that Hanzoflow is running, follow the [Quickstart](/get-started-quickstart) to create your first flow.

## Manage Hanzoflow versions

To upgrade Hanzoflow to the latest version with uv, use the uv pip upgrade command.

```bash
uv pip install hanzoflow -U
```

To upgrade Hanzoflow to the latest version, use the pip upgrade command.

```bash
python -m pip install hanzoflow -U
```

To install a specific version of the Hanzoflow package, add the required version to the command.

```bash
python -m pip install hanzoflow==1.1
```

To reinstall Hanzoflow and all of its dependencies, add the `--force-reinstall` flag to the command.

```bash
python -m pip install hanzoflow --force-reinstall
```

## DataStax Hanzoflow {#datastax-hanzoflow}

**DataStax Hanzoflow** is a hosted version of Hanzoflow integrated with [Astra DB](https://www.datastax.com/products/datastax-astra). Be up and running in minutes with no installation or setup required. [Sign up for free](https://astra.datastax.com/signup?type=hanzoflow).

## Common installation issues

This is a list of possible issues that you may encounter when installing and running Hanzoflow.

### No `hanzoflow.__main__` module

When you try to run Hanzoflow with the command `hanzoflow run`, you encounter the following error:

```bash
> No module named 'hanzoflow.__main__'
```

1. Run `python -m hanzoflow run` instead of `hanzoflow run`.
2. If that doesn't work, reinstall the latest Hanzoflow version with `python -m pip install hanzoflow -U`.
3. If that doesn't work, reinstall Hanzoflow and its dependencies with `python -m pip install hanzoflow --pre -U --force-reinstall`.

### Hanzoflow runTraceback

When you try to run Hanzoflow using the command `hanzoflow run`, you encounter the following error:

```bash
> hanzoflow runTraceback (most recent call last): File ".../hanzoflow", line 5, in <module>  from hanzoflow.__main__ import mainModuleNotFoundError: No module named 'hanzoflow.__main__'
```

There are two possible reasons for this error:

1. You've installed Hanzoflow using `pip install hanzoflow` but you already had a previous version of Hanzoflow installed in your system. In this case, you might be running the wrong executable. To solve this issue, run the correct executable by running `python -m hanzoflow run` instead of `hanzoflow run`. If that doesn't work, try uninstalling and reinstalling Hanzoflow with `python -m pip install hanzoflow --pre -U`.
2. Some version conflicts might have occurred during the installation process. Run `python -m pip install hanzoflow --pre -U --force-reinstall` to reinstall Hanzoflow and its dependencies.

### Something went wrong running migrations

```bash
> Something went wrong running migrations. Please, run 'hanzoflow migration --fix'
```

Clear the cache by deleting the contents of the cache folder.

This folder can be found at:

- **Linux or WSL2 on Windows**: `home/<username>/.cache/hanzoflow/`
- **MacOS**: `/Users/<username>/Library/Caches/hanzoflow/`

This error can occur during Hanzoflow upgrades when the new version can't override `hanzoflow-pre.db` in `.cache/hanzoflow/`. Clearing the cache removes this file but also erases your settings.

If you wish to retain your files, back them up before clearing the folder.

### Hanzoflow installation freezes at pip dependency resolution

Installing Hanzoflow with `pip install hanzoflow` slowly fails with this error message:

```plain
pip is looking at multiple versions of <<library>> to determine which version is compatible with other requirements. This could take a while.
```

To work around this issue, install Hanzoflow with [`uv`](https://docs.astral.sh/uv/getting-started/installation/) instead of `pip`.

```plain
uv pip install hanzoflow
```

To run Hanzoflow with uv:

```plain
uv run hanzoflow run
```
