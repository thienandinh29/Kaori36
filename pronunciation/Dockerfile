# Phone recognition and goodness of pronunciation (specs/pronunciation/step-3.2.md). PyTorch CPU build;
# the weights are not in the image: downloaded once into the /models volume and checked against the pins.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.12-slim
RUN useradd --uid 10005 --create-home --shell /usr/sbin/nologin pron \
 && mkdir -p /models && chown pron /models
WORKDIR /srv
COPY --from=build /srv/.venv ./.venv
COPY nodetrail_pron ./nodetrail_pron
ENV PATH=/srv/.venv/bin:$PATH PYTHONUNBUFFERED=1 PRON_HOST=0.0.0.0 PRON_CACHE=/models \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER pron
EXPOSE 8040
# The first start downloads about 1.3 GB; later starts load from the volume in seconds.
HEALTHCHECK --interval=10s --timeout=5s --start-period=20m --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8040/health', timeout=3)"
CMD ["python", "-m", "nodetrail_pron.server"]
