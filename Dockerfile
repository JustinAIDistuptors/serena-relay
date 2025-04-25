FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY relay.py .

EXPOSE 8080

ENV PORT=8080
ENV LOG_LEVEL=info
ENV UPSTREAM_URL=https://serena-mcp.fly.dev
ENV SERVICE_NAME=serena

CMD ["uvicorn", "relay:app", "--host", "0.0.0.0", "--port", "8080"]
