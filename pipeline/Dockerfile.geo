# Separate geospatial worker image; keep GDAL/raster dependencies out of the transactional API.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libproj-dev proj-data proj-bin libgeos-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/pipeline
COPY pipeline/pyproject.toml /srv/pipeline/pyproject.toml
COPY pipeline/lake_protect /srv/pipeline/lake_protect
RUN pip install --upgrade pip && pip install -e '.[geo,dev]'
ENTRYPOINT ["lp-geo"]
