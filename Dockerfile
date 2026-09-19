FROM php:8.3-cli
WORKDIR /app
COPY index.php /app/index.php
RUN touch /app/keys.json && chmod 666 /app/keys.json
CMD ["sh", "-c", "php -S 0.0.0.0:${PORT:-8080} -t /app /app/index.php"]
