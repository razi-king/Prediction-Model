# DevAscend API as a Docker image (FastAPI + the trained ML models).
# Build and run locally to test:
#   docker build -t devascend-api .
#   docker run -p 7860:7860 devascend-api          -> http://localhost:7860/docs
# Hugging Face Spaces uses deploy/huggingface/Dockerfile (same steps, but it downloads the code from GitHub).

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # install the Cassandra driver in pure-Python mode (no C compiler needed in a slim image)
    CASS_DRIVER_NO_EXTENSIONS=1 \
    PORT=7860

WORKDIR /app

# 1) dependencies first (this layer is cached until requirements.txt changes)
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt

# 2) only what the API needs: its code, the shared ML code, the knowledge base and the trained models
COPY api/ api/
COPY ml/*.py ml/
COPY ml/knowledge/ ml/knowledge/
COPY ml/models/ ml/models/

# run as a normal user (Hugging Face Spaces requires uid 1000)
RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --app-dir api --host 0.0.0.0 --port ${PORT}"]
