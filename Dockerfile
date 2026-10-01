FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY config/ config/
COPY data/ data/
COPY artifacts/models/ artifacts/models/
COPY artifacts/reference_workbook_snapshot.json artifacts/reference_workbook_snapshot.json
COPY docs/ docs/
COPY reports/ reports/
COPY --from=web /web/out frontend/out
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/artifacts/trials && chown -R appuser:appuser /app
USER appuser
ENV PORT=8080 LOKY_MAX_CPU_COUNT=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
EXPOSE 8080
CMD ["sh","-c","exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
