FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/fundmaster

RUN groupadd --gid 10001 fundmaster \
    && useradd --uid 10001 --gid fundmaster --create-home fundmaster

COPY docker/requirements/portfolio.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt

WORKDIR /app
COPY --chown=fundmaster:fundmaster backend/portfolio_backend/ /app/

USER fundmaster
EXPOSE 5002

CMD ["python", "-c", "from app import create_app; create_app().run(host='0.0.0.0', port=5002, debug=False, use_reloader=False)"]
