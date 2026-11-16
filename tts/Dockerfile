# The text-to-speech service (specs/speech, S2): Piper on CPU (onnxruntime). The voice is not in the
# image: it is downloaded once into the /models volume and checked against the pinned SHA-256.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --uid 10004 --create-home --shell /usr/sbin/nologin tts \
 && mkdir -p /models && chown tts /models
WORKDIR /srv
COPY --from=build /srv/.venv ./.venv
COPY nodetrail_tts ./nodetrail_tts
ENV PATH=/srv/.venv/bin:$PATH PYTHONUNBUFFERED=1 TTS_HOST=0.0.0.0 TTS_CACHE=/models
USER tts
EXPOSE 8030
# The first start downloads about 115 MB; later starts load from the volume in about a second.
HEALTHCHECK --interval=10s --timeout=5s --start-period=5m --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8030/health', timeout=3)"
CMD ["python", "-m", "nodetrail_tts.server"]
