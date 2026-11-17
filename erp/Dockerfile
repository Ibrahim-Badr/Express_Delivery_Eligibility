FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10002 erpgroup \
    && useradd --uid 10002 --gid erpgroup --shell /usr/sbin/nologin --no-create-home erpuser

COPY --chown=erpuser:erpgroup *.py ./erp/

USER erpuser

CMD ["python", "-m", "erp.erp_simulator"]
