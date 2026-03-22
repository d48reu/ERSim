FROM node:20-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ERSIM_CURATED_DEMO=1

# Python package (see pyproject.toml) + case bundle required at runtime
COPY pyproject.toml llm.py run.py test_output.json ./
COPY api ./api
COPY shift ./shift
COPY cases ./cases
COPY residents ./residents

RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -e .

RUN test -f /app/test_output.json \
    && python -c "import api.main; import shift.shift"

RUN rm -rf /app/api/static && mkdir -p /app/api/static
COPY --from=frontend-build /app/frontend/dist/ /app/api/static/

CMD ["sh", "-c", "python run.py --host 0.0.0.0 --port ${PORT:-8000}"]
