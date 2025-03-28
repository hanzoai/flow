# celeryconfig.py
import os

hanzoflow_redis_host = os.environ.get("HANZOFLOW_REDIS_HOST")
hanzoflow_redis_port = os.environ.get("HANZOFLOW_REDIS_PORT")
# broker default user

if hanzoflow_redis_host and hanzoflow_redis_port:
    broker_url = f"redis://{hanzoflow_redis_host}:{hanzoflow_redis_port}/0"
    result_backend = f"redis://{hanzoflow_redis_host}:{hanzoflow_redis_port}/0"
else:
    # RabbitMQ
    mq_user = os.environ.get("RABBITMQ_DEFAULT_USER", "hanzoflow")
    mq_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "hanzoflow")
    broker_url = os.environ.get("BROKER_URL", f"amqp://{mq_user}:{mq_password}@localhost:5672//")
    result_backend = os.environ.get("RESULT_BACKEND", "redis://localhost:6379/0")
# tasks should be json or pickle
accept_content = ["json", "pickle"]
