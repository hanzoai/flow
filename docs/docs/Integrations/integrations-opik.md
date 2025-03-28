---
title: Opik
slug: /integrations-opik
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Integrate Opik with Hanzoflow

[Opik](https://www.comet.com/site/products/opik/) is an open-source platform designed for evaluating, testing, and monitoring large language model (LLM) applications. Developed by Comet, it aims to facilitate more intuitive collaboration, testing, and monitoring of LLM-based applications.

This guide walks you through how to configure Hanzoflow to collect [tracing](https://www.comet.com/docs/opik/tracing/log_traces) data about your flow executions and automatically send the data to Opik.

## Prerequisites

- A project in Hanzoflow with a runnable flow
- An Open-Source Opik server or an Opik Cloud account - You can learn more about the differences [here](https://www.comet.com/docs/opik/faq#what-is-the-difference-between-opik-cloud-and-the-open-source-opik-platform-)
- If you are using Opik Cloud, you will also need your [Opik API key](https://www.comet.com/docs/opik/faq#where-can-i-find-my-opik-api-key-)

## Set your Opik configuration as environment variables

Call the CLI `opik configure` to save your Opik configuration in the same environment where you run Hanzoflow.

```bash
opik configure
```

For self-hosted Opik, you can also configure it using the Opik CLI by running the following command:

```bash
opik configure --use_local
```

See the [Opik documentation](https://www.comet.com/docs/opik/tracing/sdk_configuration) for more ways to configure Opik SDKs.

## Start Hanzoflow and run a flow

1. Start Hanzoflow in the same terminal or environment where you set the environment variables:

```bash
uv run hanzoflow run
```

2. In Hanzoflow, open an existing project, and then run a flow.


3. Navigate to your Opik project dashboard and view the collected tracing data.

## Disable the Opik integration

To disable the Opik integration, remove the environment variables you set in the previous steps and restart Hanzoflow.
