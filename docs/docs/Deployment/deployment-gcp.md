---
title: Deploy Hanzoflow on Google Cloud Platform
slug: /deployment-gcp
---

This guide demonstrates deploying Hanzoflow on Google Cloud Platform.

To deploy Hanzoflow on Google Cloud Platform using Cloud Shell, use the below script.

The script guides you through setting up a Debian-based VM with the Hanzoflow package, Nginx, and the necessary configurations to run the Hanzoflow dev environment in GCP.

## Prerequisites

* A [Google Cloud](https://console.cloud.google.com/) project with the necessary permissions to create resources

## Deploy Hanzoflow in GCP

1. Click the following button to launch Cloud Shell:

   [![Deploy to Google Cloud](https://gstatic.com/cloudssh/images/open-btn.svg)](https://console.cloud.google.com/cloudshell/open?git_repo=https://github.com/hanzoflow-ai/hanzoflow&working_dir=scripts/gcp&shellonly=true&tutorial=walkthroughtutorial.md)

2. Click **Trust repo**. Some gcloud commands may not run in an ephemeral Cloud Shell environment.
3. Click **Start** and follow the tutorial to deploy Hanzoflow.

## Pricing

This deployment uses a [spot (preemptible) instance](https://cloud.google.com/compute/docs/instances/preemptible), which is a cost-effective option for running Hanzoflow. However, **due to the nature of spot instances, the VM may be terminated at any time if Google Cloud needs to reclaim the resources**.

For more information, see the [GCP pricing calculator](https://cloud.google.com/products/calculator?hl=en).
