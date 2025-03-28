---
title: LangWatch
slug: /integrations-langwatch
---



# LangWatch {#938674091aac4d9d9aa4aa6eb5c215b4}


LangWatch is an all-in-one LLMOps platform for monitoring, observability, analytics, evaluations and alerting for getting user insights and improve your LLM workflows.


To integrate with Hanzoflow, just add your LangWatch API as a Hanzoflow environment variable and you are good to go!


## Step-by-step Configuration {#6f1d56ff6063417491d100d522dfcf1a}

1. Obtain your LangWatch API key from [https://app.langwatch.ai/](https://app.langwatch.ai/)
2. Add the following key to Hanzoflow .env file:

```shell
LANGWATCH_API_KEY="your-api-key"
```


or export it in your terminal:


```shell
export LANGWATCH_API_KEY="your-api-key"
```

3. Restart Hanzoflow using `hanzoflow run --env-file .env`
4. Run a project in Hanzoflow.
5. View the LangWatch dashboard for monitoring and observability.

![](/img/langwatch-dashboard.png)

