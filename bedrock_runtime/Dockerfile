FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY bedrock_runtime /app/bedrock_runtime
COPY agent /app/agent

EXPOSE 8001
CMD ["uvicorn", "bedrock_runtime.app:app", "--host", "0.0.0.0", "--port", "8001"]
