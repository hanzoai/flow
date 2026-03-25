# celeryconfig.py
import os

flow_redis_host = os.environ.get("FLOW_REDIS_HOST")
flow_redis_port = os.environ.get("FLOW_REDIS_PORT")
# broker default user

if flow_redis_host and flow_redis_port:
    broker_url = f"redis://{flow_redis_host}:{flow_redis_port}/0"
    result_backend = f"redis://{flow_redis_host}:{flow_redis_port}/0"
else:
    # RabbitMQ
    mq_user = os.environ.get("RABBITMQ_DEFAULT_USER", "flow")
    mq_password = os.environ.get("RABBITMQ_DEFAULT_PASS", "flow")
    broker_url = os.environ.get("BROKER_URL", f"amqp://{mq_user}:{mq_password}@localhost:5672//")
    result_backend = os.environ.get("RESULT_BACKEND", "redis://localhost:6379/0")
# tasks should be json or pickle
accept_content = ["json", "pickle"]
