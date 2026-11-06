FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Pango and HarfBuzz are what WeasyPrint needs to render PDFs, including Telugu shaping.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/api
COPY api/requirements.txt /srv/api/requirements.txt
RUN pip install -r /srv/api/requirements.txt

# `lp verify-pack` is available in this image. The heavy geospatial extras are not installed here.
COPY pipeline /srv/pipeline
RUN pip install -e /srv/pipeline

COPY api /srv/api
