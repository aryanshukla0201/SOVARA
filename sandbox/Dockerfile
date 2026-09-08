FROM python:3.11-slim

WORKDIR /sandbox

RUN useradd -m -u 1000 sandboxuser \
    && chown -R sandboxuser:sandboxuser /sandbox

USER sandboxuser

CMD ["python", "--version"]
