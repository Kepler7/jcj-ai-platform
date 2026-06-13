#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/ihui"
COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_SCRIPT="${APP_DIR}/scripts/backup_postgres.sh"
RUNTIME_BACKUP_DIR="/tmp/ihui-runtime-backup"
DEPLOY_LOG_DIR="/opt/ihui-deployments"

TARGET_SHA="${1:-}"

if [[ -z "${TARGET_SHA}" ]]; then
  echo "ERROR: Debes indicar el commit a desplegar."
  echo "Uso: ./scripts/deploy_prod.sh <commit-sha>"
  exit 1
fi

cd "${APP_DIR}"

mkdir -p "${DEPLOY_LOG_DIR}"
mkdir -p "${RUNTIME_BACKUP_DIR}"

PREVIOUS_SHA="$(git rev-parse HEAD)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEPLOY_RECORD="${DEPLOY_LOG_DIR}/deploy_${TIMESTAMP}.env"

echo "PREVIOUS_SHA=${PREVIOUS_SHA}" > "${DEPLOY_RECORD}"
echo "TARGET_SHA=${TARGET_SHA}" >> "${DEPLOY_RECORD}"
echo "STARTED_AT=$(date --iso-8601=seconds)" >> "${DEPLOY_RECORD}"

restore_runtime_files() {
  mkdir -p "${APP_DIR}/data/ihui3"

  for filename in \
    ihui3_knowledge.normalized.jsonl \
    ihui3_sync_status.json
  do
    if [[ -f "${RUNTIME_BACKUP_DIR}/${filename}" ]]; then
      cp "${RUNTIME_BACKUP_DIR}/${filename}" \
        "${APP_DIR}/data/ihui3/${filename}"
    fi
  done
}

rollback_code() {
  echo "Deploy falló. Iniciando rollback de código a ${PREVIOUS_SHA}..."

  cd "${APP_DIR}"

  git reset --hard "${PREVIOUS_SHA}"
  restore_runtime_files

  docker compose -f "${COMPOSE_FILE}" build backend worker frontend

  docker compose -f "${COMPOSE_FILE}" up -d \
    --no-deps \
    backend worker frontend

  sleep 10

  if curl -fsS https://app.ihui.info/health >/dev/null \
    && curl -fsS https://app.ihui.info/health/deps >/dev/null \
    && curl -fsS https://app.ihui.info >/dev/null
  then
    echo "ROLLBACK_STATUS=success" >> "${DEPLOY_RECORD}"
    echo "Rollback de código completado correctamente."
  else
    echo "ROLLBACK_STATUS=failed" >> "${DEPLOY_RECORD}"
    echo "ERROR: El rollback también falló. Se requiere revisión manual."
  fi
}

on_error() {
  local exit_code=$?

  echo "DEPLOY_STATUS=failed" >> "${DEPLOY_RECORD}"
  echo "FAILED_AT=$(date --iso-8601=seconds)" >> "${DEPLOY_RECORD}"

  rollback_code

  exit "${exit_code}"
}

trap on_error ERR

echo "Creando backup de Postgres..."
"${BACKUP_SCRIPT}"

echo "Respaldando archivos de conocimiento IHUI 3.0..."
rm -rf "${RUNTIME_BACKUP_DIR}"
mkdir -p "${RUNTIME_BACKUP_DIR}"

for filename in \
  ihui3_knowledge.normalized.jsonl \
  ihui3_sync_status.json
do
  if [[ -f "${APP_DIR}/data/ihui3/${filename}" ]]; then
    cp "${APP_DIR}/data/ihui3/${filename}" \
      "${RUNTIME_BACKUP_DIR}/${filename}"
  fi
done

echo "Descargando commit ${TARGET_SHA}..."
git fetch origin main

if ! git cat-file -e "${TARGET_SHA}^{commit}" 2>/dev/null; then
  echo "ERROR: El commit ${TARGET_SHA} no existe en el repositorio."
  exit 1
fi

git reset --hard "${TARGET_SHA}"
restore_runtime_files

echo "Construyendo imágenes..."
docker compose -f "${COMPOSE_FILE}" build \
  backend worker frontend

echo "Levantando backend..."
docker compose -f "${COMPOSE_FILE}" up -d \
  --no-deps \
  backend

echo "Aplicando migraciones..."
docker compose -f "${COMPOSE_FILE}" exec -T backend \
  alembic upgrade head

echo "Levantando worker y frontend..."
docker compose -f "${COMPOSE_FILE}" up -d \
  --no-deps \
  worker frontend

echo "Esperando inicio de servicios..."
sleep 12

echo "Verificando backend..."
curl -fsS https://app.ihui.info/health >/dev/null

echo "Verificando dependencias..."
curl -fsS https://app.ihui.info/health/deps >/dev/null

echo "Verificando frontend..."
curl -fsS https://app.ihui.info >/dev/null

echo "DEPLOY_STATUS=success" >> "${DEPLOY_RECORD}"
echo "FINISHED_AT=$(date --iso-8601=seconds)" >> "${DEPLOY_RECORD}"

trap - ERR

echo "Deploy completado correctamente."
echo "Commit anterior: ${PREVIOUS_SHA}"
echo "Commit desplegado: ${TARGET_SHA}"
