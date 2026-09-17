FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# git: needed for the pip git+https install below, not present in the
# slim base image.
RUN apt-get update && \
    apt-get install --no-install-recommends -y git && \
    rm -rf /var/lib/apt/lists/*

# capsize-voice isn't on PyPI yet, so it's installed from source first
# and the project install below then finds it already satisfied.
ARG CAPSIZE_VOICE_SPEC="capsize-voice @ git+https://github.com/capsize-games/capsize-voice.git@main"

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir "${CAPSIZE_VOICE_SPEC}" && \
    mkdir capsize_persona && touch capsize_persona/__init__.py && \
    pip install --no-cache-dir . && \
    rm -rf capsize_persona

COPY capsize_persona capsize_persona
COPY migrations migrations
COPY alembic.ini ./

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin persona && \
    mkdir -p /data && chown 10001:10001 /data
USER 10001

EXPOSE 8879

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=20s \
    CMD python -c "import urllib.request;\
urllib.request.urlopen('http://127.0.0.1:8879/health')"

CMD ["sh", "-c", "alembic upgrade head && python -m capsize_persona"]
