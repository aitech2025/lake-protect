"""Statewide platform API package.

The additive schema is managed by Alembic and accessed through explicit SQL. Do not
register duplicate ORM mappings here: the legacy application already maps some
geospatial tables such as land_parcels.
"""
