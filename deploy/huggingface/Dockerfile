# Dockerfile for the Hugging Face Space that runs the DevAscend API.
# Upload THIS file (and README.md from this folder) to your Space.
# The Space downloads the project code from GitHub while it builds, so you never push
# the model files to Hugging Face yourself.
#
# Changed the code on GitHub?  Space -> Settings -> "Factory rebuild" to pull the latest version.

FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Your public GitHub repository (change it if you fork or rename the repo)
ARG REPO_URL=https://github.com/razi-king/Prediction-Model.git
ARG BRANCH=main

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CASS_DRIVER_NO_EXTENSIONS=1 \
    PORT=7860

RUN git clone --depth 1 --branch ${BRANCH} ${REPO_URL} /src

WORKDIR /app
RUN pip install -r /src/api/requirements.txt \
    && mkdir -p ml \
    && cp -r /src/api ./api \
    && cp /src/ml/*.py ./ml/ \
    && cp -r /src/ml/knowledge ./ml/knowledge \
    && cp -r /src/ml/models ./ml/models \
    && rm -rf /src

RUN useradd -m -u 1000 appuser
USER appuser

EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --app-dir api --host 0.0.0.0 --port ${PORT}"]
