#!/bin/bash
# First start only: the application role and database (the role owns the database, so it can
# create its schemas and the trusted extensions pg_trgm/unaccent itself).
set -euo pipefail
psql -v ON_ERROR_STOP=1 -U postgres -v pw="$NUTRITION_DB_PASSWORD" <<'SQL'
create role nutrition login password :'pw';
create database nutrition owner nutrition;
SQL
