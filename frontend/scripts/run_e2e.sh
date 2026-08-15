#!/usr/bin/env bash
set -e

export E2E_DATABASE_URL="postgresql+psycopg://booking_e2e_user:booking_e2e_password@127.0.0.1:5434/booking_e2e"

# 1. Validar URL de base de datos E2E de forma estructurada con make_url
if ! (cd ../backend && uv run python -c "from sqlalchemy.engine import make_url; url = make_url('$E2E_DATABASE_URL'); assert url.host == '127.0.0.1' and url.port == 5434 and url.database == 'booking_e2e'" 2>/dev/null); then
  echo "Error: E2E_DATABASE_URL no cumple con host 127.0.0.1, puerto 5434 y base booking_e2e." >&2
  exit 1
fi

EXIT_CODE=1
BACKEND_PID=""
PREVIEW_PID=""

cleanup() {
  trap - EXIT INT TERM
  echo "Ejecutando cleanup y teardown de E2E..."

  # 1. Terminar y esperar procesos backend y preview PRIMERO antes de tocar el schema
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Terminando backend (PID: $BACKEND_PID)..."
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi

  if [ -n "$PREVIEW_PID" ] && kill -0 "$PREVIEW_PID" 2>/dev/null; then
    echo "Terminando preview (PID: $PREVIEW_PID)..."
    kill -TERM "$PREVIEW_PID" 2>/dev/null || true
    wait "$PREVIEW_PID" 2>/dev/null || true
  fi

  # 2. Ejecutar teardown de base de datos validada DESPUÉS de que no queden conexiones activas
  if [ -n "$E2E_DATABASE_URL" ]; then
    (cd ../backend && DATABASE_URL="$E2E_DATABASE_URL" uv run python scripts/teardown_e2e.py) || true
  fi
}
trap cleanup EXIT INT TERM

echo "1. Levantando contenedor db_e2e..."
(cd .. && docker compose up -d db_e2e)

echo "2. Esperando disponibilidad de PostgreSQL en puerto 5434..."
PG_READY=0
for i in {1..30}; do
  if (cd ../backend && uv run python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 5434)); s.close()" 2>/dev/null); then
    echo "PostgreSQL en puerto 5434 está listo."
    PG_READY=1
    break
  fi
  sleep 1
done

if [ "$PG_READY" -ne 1 ]; then
  echo "Error: Timeout esperando PostgreSQL en 127.0.0.1:5434" >&2
  exit 1
fi

echo "3. Ejecutando setup_e2e.py..."
(cd ../backend && DATABASE_URL="$E2E_DATABASE_URL" PYTHONPATH=. uv run python scripts/setup_e2e.py)

echo "4. Iniciando backend en puerto 8001..."
(cd ../backend && APP_ENV=e2e EMAIL_PROVIDER=noop FRONTEND_URL="http://127.0.0.1:4173" SESSION_SECRET="e2e-session-secret-key-test-32-bytes" DATABASE_URL="$E2E_DATABASE_URL" RATE_LIMIT_SECRET="e2e-secret-key-test-32-bytes" PYTHONPATH=. uv run uvicorn app.main:app --host 127.0.0.1 --port 8001) &
BACKEND_PID=$!

echo "5. Esperando salud del backend en http://127.0.0.1:8001/health..."
BACKEND_READY=0
for i in {1..20}; do
  if (cd ../backend && uv run python -c "import urllib.request; res = urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=1); exit(0 if res.getcode() == 200 else 1)" 2>/dev/null); then
    echo "Backend está listo y saludable."
    BACKEND_READY=1
    break
  fi
  sleep 1
done

if [ "$BACKEND_READY" -ne 1 ]; then
  echo "Error: Timeout esperando backend en http://127.0.0.1:8001/health" >&2
  exit 1
fi

echo "6. Construyendo frontend..."
VITE_API_BASE_URL="http://127.0.0.1:8001/api" npm run build

echo "7. Iniciando preview del frontend en puerto 4173..."
npm run preview -- --host 127.0.0.1 --port 4173 &
PREVIEW_PID=$!

echo "8. Esperando preview en http://127.0.0.1:4173..."
PREVIEW_READY=0
for i in {1..20}; do
  if (cd ../backend && uv run python -c "import urllib.request; res = urllib.request.urlopen('http://127.0.0.1:4173', timeout=1); exit(0 if res.getcode() == 200 else 1)" 2>/dev/null); then
    echo "Frontend preview está listo."
    PREVIEW_READY=1
    break
  fi
  sleep 1
done

if [ "$PREVIEW_READY" -ne 1 ]; then
  echo "Error: Timeout esperando frontend preview en http://127.0.0.1:4173" >&2
  exit 1
fi


echo "9. Ejecutando suite Playwright..."
set +e
npx playwright test --workers=1
EXIT_CODE=$?
set -e

echo "Suite Playwright finalizó con código: $EXIT_CODE"
exit "$EXIT_CODE"
