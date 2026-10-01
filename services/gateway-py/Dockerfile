FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY proto/ /app/proto/
COPY services/gateway-py/ /app/services/gateway-py/
COPY scripts/ /app/scripts/

WORKDIR /app/services/gateway-py
RUN uv sync

WORKDIR /app
RUN ./scripts/generate_proto.sh

WORKDIR /app/services/gateway-py
EXPOSE 50051

CMD ["uv", "run", "python", "-m", "gateway.server", "--host", "0.0.0.0", "--port", "50051"]
