FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY challenge_jar ./challenge_jar
COPY web ./web
RUN pip install --no-cache-dir .
ENV JAR_DATABASE_URL=sqlite:////data/challenge_jar.db JAR_WEB_DIR=/app/web
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "challenge_jar.main:app", "--host", "0.0.0.0", "--port", "8000"]
