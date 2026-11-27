# Speech recognition for the Speaking test (specs/speaking/step-5.1.md): Whisper small.en through
# faster-whisper (CTranslate2, int8, CPU; no PyTorch). The weights are not in the image: downloaded
# once into the /models volume at a pinned revision and checked against SHA-256 pins at every start.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --uid 10006 --create-home --shell /usr/sbin/nologin asr \
 && mkdir -p /models && chown asr /models
WORKDIR /srv
COPY --from=build /srv/.venv ./.venv
COPY nodetrail_asr ./nodetrail_asr
ENV PATH=/srv/.venv/bin:$PATH PYTHONUNBUFFERED=1 ASR_HOST=0.0.0.0 ASR_CACHE=/models
USER asr
EXPOSE 8050
# The first start downloads about 490 MB; later starts load from the volume in seconds.
HEALTHCHECK --interval=10s --timeout=5s --start-period=15m --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/health', timeout=3)"
CMD ["python", "-m", "nodetrail_asr.server"]
