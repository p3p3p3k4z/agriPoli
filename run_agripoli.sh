#!/usr/bin/env bash
# ==============================================================================
# AgriPoli - Script de Inicio Unificado (Frontend Gruvbox + API Machine Learning)
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo -e "\033[1;33m"
cat << "EOF"
    ___              _ ____       ___ 
   /   |  ____ _____(_) __ \____ / (_)
  / /| | / __ `/ __/ / /_/ / __ \/ /  
 / ___ |/ /_/ / / / / ____/ /_/ / /   
/_/  |_|\__, /_/ /_/_/    \____/_/    
       /____/                         
EOF
echo -e "\033[0m"
echo -e "\033[1;32m[AgriPoli]\033[0m Iniciando entorno completo con estética Gruvbox..."

# 1. Comprobar puertos en uso
check_port() {
    local port=$1
    if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1 || fuser $port/tcp >/dev/null 2>&1; then
        echo -e "\033[1;33m[Aviso]\033[0m El puerto $port ya está en uso. Intentando liberar o reutilizar..."
        fuser -k $port/tcp >/dev/null 2>&1 || true
        sleep 1
    fi
}

check_port 8040
check_port 8000

# 2. Levantar API de Machine Learning (FastAPI en puerto 8040)
echo -e "\033[1;34m[ML API]\033[0m Iniciando servidor de Machine Learning en puerto 8040..."
if command -v uv >/dev/null 2>&1; then
    uv run --with fastapi,uvicorn,scikit-learn,pandas,numpy,matplotlib \
        uvicorn app:app --app-dir "$DIR/ML/polinizadores_app" --host 0.0.0.0 --port 8040 > /tmp/agripoli_ml.log 2>&1 &
    ML_PID=$!
else
    python3 -m uvicorn app:app --app-dir "$DIR/ML/polinizadores_app" --host 0.0.0.0 --port 8040 > /tmp/agripoli_ml.log 2>&1 &
    ML_PID=$!
fi

# 3. Levantar Servidor HTTP para el Frontend (puerto 8000)
echo -e "\033[1;34m[Frontend]\033[0m Iniciando servidor web en puerto 8000..."
python3 -m http.server 8000 --directory "$DIR" > /tmp/agripoli_front.log 2>&1 &
FRONT_PID=$!

cleanup() {
    echo ""
    echo -e "\033[1;31m[Deteniendo]\033[0m Apagando servicios de AgriPoli..."
    kill $ML_PID 2>/dev/null || true
    kill $FRONT_PID 2>/dev/null || true
    echo -e "\033[1;32m[Listo]\033[0m Servicios detenidos correctamente."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Esperar a que los servicios respondan
sleep 2

echo ""
echo -e "\033[1;32m===================================================================\033[0m"
echo -e "\033[1;32m  Plataforma AgriPoli lista y operando\033[0m"
echo -e "\033[1;32m===================================================================\033[0m"
echo ""
echo -e "  [Portal Principal]       \033[4;36mhttp://localhost:8000\033[0m"
echo -e "  [Dashboard]              \033[4;36mhttp://localhost:8000/frontend/dashboard.html\033[0m"
echo -e "  [Consulta por Clima]     \033[4;36mhttp://localhost:8000/frontend/maching_learning.html\033[0m"
echo -e "  [Docs API (Swagger)]     \033[4;36mhttp://localhost:8040/docs\033[0m"
echo ""
echo -e "  \033[1;33mLogs:\033[0m"
echo -e "  - ML API:   \033[37m/tmp/agripoli_ml.log\033[0m"
echo -e "  - Frontend: \033[37m/tmp/agripoli_front.log\033[0m"
echo ""
echo -e "\033[1;30mPresiona [Ctrl + C] para detener todos los servidores.\033[0m"
echo ""

wait
