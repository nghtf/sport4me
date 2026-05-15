FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=sqlite:///data/activity_bot.db

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --root-user-action=ignore -r requirements.txt

COPY bot ./bot

RUN mkdir -p /app/data && chown -R app:app /app

USER app

VOLUME ["/app/data"]

CMD ["python", "-m", "bot.main"]
