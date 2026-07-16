FROM python:3.11-slim-bookworm AS builder

ARG DEBIAN_MIRROR=http://deb.debian.org/debian
ARG DEBIAN_SECURITY_MIRROR=http://deb.debian.org/debian-security
ARG PIP_INDEX_URL=https://pypi.org/simple

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    VIRTUAL_ENV=/opt/venv

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
        -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY docker/requirements/market.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /tmp/requirements.txt \
    && openbb-build

FROM python:3.11-slim-bookworm

ARG DEBIAN_MIRROR=http://deb.debian.org/debian
ARG DEBIAN_SECURITY_MIRROR=http://deb.debian.org/debian-security

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HOME=/home/fundmaster

RUN sed -i \
        -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
        -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 fundmaster \
    && useradd --uid 10001 --gid fundmaster --create-home fundmaster

COPY --from=builder /opt/venv /opt/venv
RUN mkdir -p /opt/venv/lib/python3.11/site-packages/efinance/data \
    && chown -R fundmaster:fundmaster \
        /opt/venv/lib/python3.11/site-packages/efinance \
        /opt/venv/lib/python3.11/site-packages/candlelite

WORKDIR /app
COPY --chown=fundmaster:fundmaster backend/market_backend/ /app/
# Local config.ini files are deliberately excluded from the build context.
COPY --chown=fundmaster:fundmaster docker/market-config.container /app/apis/config.ini

USER fundmaster
EXPOSE 5001

CMD ["python", "-c", "from app import create_app; create_app().run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)"]
