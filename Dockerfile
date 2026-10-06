FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY coin135.py .
COPY experiments ./experiments
COPY benchmarks ./benchmarks
ENV PYTHONPATH=/app/src PORT=3001
EXPOSE 3001
CMD ["python", "-m", "coin.node", "--port", "3001"]
