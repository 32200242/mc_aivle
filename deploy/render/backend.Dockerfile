FROM python:3.12-slim

WORKDIR /workspace

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

COPY backend/app ./backend/app
COPY backend/data ./backend/data
COPY backend/scripts/build_counseling_dataset.py ./backend/scripts/build_counseling_dataset.py

# The generated SQLite is intentionally absent from Git because it is about
# 166 MB. Bake the deterministic, synthetic demo data into the deployment
# image so a free ephemeral instance can restart without losing it.
RUN python ./backend/scripts/build_counseling_dataset.py --anchor-date 2026-08-10

WORKDIR /workspace/backend
ENV PYTHONUNBUFFERED=1
EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
