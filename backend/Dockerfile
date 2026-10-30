# Postly API image.
#
# libatomic1 is REQUIRED: prisma-client-py downloads a prebuilt Node (26.13.0) and that
# Node fails to start on python:3.13-slim with "libatomic.so.1: cannot open shared
# object file". Verified in T-001.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    HOME=/home/appuser

RUN apt-get update \
 && apt-get install -y --no-install-recommends libatomic1 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps first so the layer caches across code changes; app/ is needed because
# pyproject.toml now declares it as the package.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY . .

# Non-root runtime user. The prisma client is generated into site-packages, so that
# directory must stay writable for `python -m prisma generate` inside the container.
RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid appuser --create-home --home-dir /home/appuser \
      --shell /usr/sbin/nologin appuser \
 && mkdir -p /app/media \
 && chown -R appuser:appuser \
      /home/appuser \
      /app/media \
      /usr/local/lib/python3.13/site-packages/prisma

USER appuser

# generated client lives in site-packages, not in /app
RUN python -m prisma generate

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
