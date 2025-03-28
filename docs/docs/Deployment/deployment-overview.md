---
title: Hanzoflow deployment overview
slug: /deployment-overview
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

You have a flow, and want to share it with the world in a production environment.

This page outlines the journey from locally-run flow to a cloud-hosted production server.

More specific instructions are available in the [Docker](/deployment-docker) and [Kubernetes](/deployment-kubernetes) pages.

## Hanzoflow deployment architecture

Hanzoflow can be deployed as an [IDE](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/tree/main/charts/hanzoflow-ide) or as a [runtime](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/tree/main/charts/hanzoflow-runtime).

The **IDE** includes the frontend for visual development of your flow. The default [docker-compose.yml](https://github.com/hanzoflow-ai/hanzoflow/blob/main/docker_example/docker-compose.yml) file hosted in the Hanzoflow repository builds the Hanzoflow IDE image. To deploy the Hanzoflow IDE, see [Docker](/deployment-docker).

The **runtime** is a headless or backend-only mode. The server exposes your flow as an endpoint, and runs only the processes necessary to serve your flow, with PostgreSQL as the database for improved scalability. Use the Hanzoflow **runtime** to deploy your flows, because you don't require the frontend for visual development.

## Package your flow with the Hanzoflow runtime image

To package your flow as a Docker image, copy your flow's `.JSON` file with a command in the Dockerfile.

An example [Dockerfile](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/examples/hanzoflow-runtime/docker/Dockerfile) for bundling flows is hosted in the Hanzoflow Helm Charts repository.

For more on building the Hanzoflow docker image and pushing it to Docker Hub, see [Package your flow as a docker image](/deployment-docker#package-your-flow-as-a-docker-image).

## Deploy to Kubernetes

After your flow is packaged as a Docker image and available on Docker Hub, deploy your application by overriding the values in the [hanzoflow-runtime](https://github.com/hanzoflow-ai/hanzoflow-helm-charts/blob/main/charts/hanzoflow-runtime/Chart.yaml) Helm chart.

For more information, see [Deploy Hanzoflow on Kubernetes](/deployment-kubernetes).





