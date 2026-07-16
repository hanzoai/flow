FROM flowai/flow:1.0-alpha

CMD ["python", "-m", "flow", "run", "--host", "0.0.0.0", "--port", "7860"]
