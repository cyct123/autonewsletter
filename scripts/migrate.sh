#!/usr/bin/env bash
set -euo pipefail
psql "$DATABASE_URL" -f scripts/init-db.sql
