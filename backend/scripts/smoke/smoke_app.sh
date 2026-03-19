#!/usr/bin/env bash

# ---------------------------------------------
# Ihui Platform - Application Smoke Test
# ---------------------------------------------

set -e

echo "===================================="
echo "IHUI APPLICATION SMOKE TEST"
echo "===================================="

echo "1. Testing backend availability"
curl -I http://localhost:8000/docs

echo ""
echo "2. Checking students exist"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U jcj -d jcjdb -c "SELECT id, full_name FROM students LIMIT 5;"

echo ""
echo "3. Checking classes exist"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U jcj -d jcjdb -c "SELECT id, name FROM classes LIMIT 5;"

echo ""
echo "4. Checking student reports"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U jcj -d jcjdb -c "SELECT id, student_id FROM student_reports ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "5. Checking AI jobs"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U jcj -d jcjdb -c "SELECT id, status FROM ai_jobs ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "6. Checking AI reports"
docker compose -f docker-compose.dev.yml exec -T postgres psql -U jcj -d jcjdb -c "SELECT id, student_id FROM ai_reports ORDER BY created_at DESC LIMIT 5;"

echo ""
echo "===================================="
echo "APPLICATION SMOKE TEST COMPLETE"
echo "===================================="