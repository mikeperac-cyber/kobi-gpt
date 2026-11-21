# Backend image. Build context: backend/  (docker build -t kobi-gpt-api backend)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# app code expects <root>/backend/app and writes uploads to <root>/uploads
WORKDIR /srv/backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /srv/uploads

# Mount a persistent disk here, or uploaded photos and PDFs are lost on every redeploy.
VOLUME /srv/uploads
EXPOSE 8000

# --proxy-headers: behind Vercel's rewrite the client IP arrives in X-Forwarded-For (used by the RFQ rate limit).
# shortcut: trusts any proxy, so the header can be spoofed by direct callers; restrict forwarded-allow-ips when the host publishes its proxy IPs.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
