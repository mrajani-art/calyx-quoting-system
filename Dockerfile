FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# Install API + ML dependencies (renamed dest to bust Docker layer cache)
COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r api-requirements.txt

# Copy API code
COPY api/ /app/api/

# Copy ML models, source, and config from repo root
COPY models/ /app/models/
COPY src/ /app/src/
COPY config/ /app/config/

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
