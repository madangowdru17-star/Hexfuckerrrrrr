FROM python:3.12-slim
WORKDIR /app
COPY server.py README.md /app/
RUN touch /app/keys.json /app/requests.log
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python3 /app/server.py --host 0.0.0.0 --port ${PORT:-10000}"]
