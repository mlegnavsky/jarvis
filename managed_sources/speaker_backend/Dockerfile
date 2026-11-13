FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
RUN pip install --no-cache-dir numpy==2.2.6 sherpa-onnx==2.0.1
WORKDIR /app
COPY app /app
RUN python /app/fetch_assets.py
CMD ["python", "/app/main.py"]
