#!/usr/bin/env bash

# ---------------------------------------------
# IHUI Platform - Infrastructure Smoke Test
# ---------------------------------------------

set -e

COMPOSE="docker compose -f docker-compose.dev.yml"

echo "===================================="
echo "IHUI INFRASTRUCTURE SMOKE TEST"
echo "===================================="

echo "1. Checking Docker services..."
$COMPOSE ps

echo ""
echo "2. Checking database tables..."
$COMPOSE exec -T postgres psql -U jcj -d jcjdb -c "\dt"

echo ""
echo "3. Checking Alembic version..."
$COMPOSE exec -T postgres psql -U jcj -d jcjdb -c "SELECT * FROM alembic_version;"

echo ""
echo "4. Checking backend endpoint..."
curl -fsS http://localhost:8000/docs > /dev/null && echo "Backend OK"

echo ""
echo "5. Checking frontend endpoint..."
curl -fsS http://localhost:5173 > /dev/null && echo "Frontend OK"

echo ""
echo "6. Checking logs for critical errors..."

echo "Backend errors:"
$COMPOSE logs backend --tail=100 | grep -E "UndefinedTable|ForeignKeyViolation|IntegrityError" || echo "No critical backend errors"

echo ""
echo "Worker errors:"
$COMPOSE logs worker --tail=100 | grep -E "Traceback|ERROR" || echo "No worker errors"

echo ""
echo "Chroma errors:"
$COMPOSE logs chroma --tail=100 | grep -E "KeyError|ERROR" || echo "No chroma errors"

echo ""
echo "===================================="
echo "INFRA SMOKE TEST COMPLETE"
echo "===================================="