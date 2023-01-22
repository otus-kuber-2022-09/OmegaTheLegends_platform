FROM python:3.7.3-alpine3.9

COPY ./app /app
WORKDIR /app

RUN adduser -u 1001 -D appuser
RUN chown -R appuser.appuser /app
USER appuser

ENTRYPOINT python3 -m http.server 8000
