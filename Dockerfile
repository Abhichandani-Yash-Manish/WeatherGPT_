# WeatherGPT as a deployable image.
#
# The workspace is a Python process that serves the built React bundle and answers from local
# SQLite stores. Two things make it deployable rather than merely runnable:
#
#   * it binds loopback by default, which is right on a laptop and useless in a container, so the
#     container passes --host 0.0.0.0 explicitly and announces it at startup;
#   * a public URL can spend this workspace's provider budget, so WEATHERGPT_ACCESS_KEY gates it.
#     The image does not carry a key: the deployment supplies one as a secret.
#
# What is NOT copied in: data/runtime. On a laptop it holds roughly four gigabytes of accumulated
# raw evidence and collected blobs, none of which is needed to start - the workspace re-fetches what
# a question needs and writes new evidence beside it. It belongs on a mounted volume so it survives
# a redeploy, not baked into a layer.

FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# The CPU build of PyTorch, for the same reason CI installs it: sentence-transformers pulls torch,
# torch from PyPI brings the whole CUDA stack, and there is no GPU here.
COPY requirements-foundation.txt requirements-bulletins.txt requirements.txt ./
RUN pip install --upgrade pip \
 && pip install torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r requirements.txt

# The code, the built frontend, and the registries the workspace reads at startup. The React bundle
# is built before the image (npm run build writes web/dist) so node is not needed at runtime.
COPY weathergpt_data/ ./weathergpt_data/
COPY scripts/ ./scripts/
COPY web/dist/ ./web/dist/
COPY data/registry/ ./data/registry/
COPY data/reference/ ./data/reference/

# The geography database carries the thirty-six states, their districts and the place catalogue, and
# the climate tables carry the published 1901-2010 series. Without geography a place cannot be
# resolved at all, so it ships in the image rather than being re-derived on a cold start.
COPY data/processed/geography/ ./data/processed/geography/
COPY data/processed/climate/ ./data/processed/climate/

# The mount point for everything that accumulates. Declared so the container still starts when no
# volume is attached - it will simply collect from scratch and lose it on redeploy.
RUN mkdir -p /app/data/runtime /app/data/raw
VOLUME ["/app/data/runtime"]

EXPOSE 8765

# --host 0.0.0.0 is correct inside a container and nowhere else; --public-host must name the
# hostname this is served under, or the DNS-rebinding guard will refuse every request.
CMD ["sh", "-c", "python3 -m weathergpt_data.workspace --host 0.0.0.0 --port ${PORT:-8765} ${PUBLIC_HOST:+--public-host $PUBLIC_HOST}"]
