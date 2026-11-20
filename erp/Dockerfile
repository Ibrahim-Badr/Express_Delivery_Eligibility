FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools>=80.0.0 wheel>=0.46.2 \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -rf /usr/local/lib/python3.11/site-packages/setuptools/_vendor/*.dist-info \
    && groupadd --gid 10002 erpgroup \
    && useradd --uid 10002 --gid erpgroup --shell /usr/sbin/nologin --no-create-home erpuser

COPY --chown=erpuser:erpgroup *.py ./erp/

USER erpuser

CMD ["python", "-m", "erp.erp_simulator"]
