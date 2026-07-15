FROM python:3.11-slim-bookworm

ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    HOME=/home/fundmaster

RUN groupadd --gid 10001 fundmaster \
    && useradd --uid 10001 --gid fundmaster --create-home fundmaster

WORKDIR /app
COPY --chown=fundmaster:fundmaster ai_agent/fund_llm_engine/ /app/
RUN pip install --upgrade pip setuptools wheel \
    && pip install ".[agent]"

COPY --chown=fundmaster:fundmaster docker/smoke.py /opt/fundmaster/docker/smoke.py

USER fundmaster
EXPOSE 5003

CMD ["python", "app.py"]
