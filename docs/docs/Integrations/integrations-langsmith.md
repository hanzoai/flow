---
title: LangSmith
slug: /integrations-langsmith
---



LangSmith is a full-lifecycle DevOps service from LangChain that provides monitoring and observability. To integrate with Hanzoflow, just add your LangChain API key as a Hanzoflow environment variable and you are good to go!


## Step-by-step Configuration {#b912579a43984f9a92921232b67c885d}


---

1. Obtain your LangChain API key from [https://smith.langchain.com](https://smith.langchain.com/)
2. Add the following keys to Hanzoflow .env file:

`LANGCHAIN_API_KEY="your-api-key"LANGCHAIN_PROJECT="your-project-name"`


or export the environment variables in your terminal:


`export LANGCHAIN_API_KEY="your-api-key"export LANGCHAIN_PROJECT="your-project-name"`

3. Restart Hanzoflow using `hanzoflow run --env-file .env`
4. Run a project in Hanzoflow.
5. View the Langsmith dashboard for monitoring and observability.

![](/img/langsmith-dashboard.png)

