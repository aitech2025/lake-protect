# The screen from space as a container: `lp screen` on a schedule (CONTEXT.md section 11, one
# scheduled worker per job). rasterio's wheels carry GDAL, so no system GDAL is needed.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LP_CACHE_DIR=/var/lp/cache
WORKDIR /srv/pipeline
COPY pipeline/pyproject.toml ./
COPY pipeline/lake_protect ./lake_protect
RUN pip install --no-cache-dir ".[geo,osm,ml,integrations]" "planetary-computer>=1.0,<2"
# Chips are labelled with the same Noto Sans the desk and evidence packs use.
COPY api/app/assets/fonts /srv/api/app/assets/fonts
WORKDIR /srv/repo
CMD ["lp", "screen", "--repeat-hours", "168"]
