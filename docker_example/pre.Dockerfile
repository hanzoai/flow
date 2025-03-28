FROM hanzoflowai/hanzoflow:1.0-alpha

CMD ["python", "-m", "hanzoflow", "run", "--host", "0.0.0.0", "--port", "7860"]
