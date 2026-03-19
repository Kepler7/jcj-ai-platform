# JCJ Smoke Test Toolkit

This toolkit validates the JCJ platform after infrastructure changes, migrations, or deployments.

## Files

smoke_infra.sh  
Validates infrastructure:
- Docker containers running
- Database tables exist
- Alembic migration version
- Backend/Frontend endpoints
- Logs for critical errors

smoke_app.sh  
Validates application data and flows:
- Students exist
- Classes exist
- Reports exist
- AI jobs exist
- AI reports exist

seed_test_data.py  
Creates minimal test data:

- Smoke Test School
- Admin user
- Teacher user
- Test student
- Test class

This script is idempotent (safe to run multiple times).

## Requirements

- Docker
- Docker Compose
- curl
- psql
- Python environment with project dependencies

## Usage

Seed data

python scripts/smoke/seed_test_data.py

Run infrastructure tests

bash scripts/smoke/smoke_infra.sh

Run application tests

bash scripts/smoke/smoke_app.sh

## Scope

Tests verify:

Infrastructure health  
Database schema integrity  
Backend availability  
Basic data consistency  

## Not Included

AI output quality  
UX validation  
Performance testing  
Security auditing