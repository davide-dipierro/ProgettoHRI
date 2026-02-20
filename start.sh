#!/bin/bash
# =============================================================================
# HRI Poker Experiment - Script di avvio (Linux/Mac)
# =============================================================================
#
# UTILIZZO:
#   ./start.sh                          -> Modalita' SIMULAZIONE (default)
#   ./start.sh simulate                 -> Modalita' SIMULAZIONE
#   ./start.sh robot                    -> Modalita' ROBOT (Choregraphe locale)
#   ./start.sh robot 192.168.1.100      -> Robot fisico su IP specifico
#
# =============================================================================

set -e

MODE="${1:-simulate}"
NAO_IP_ARG="${2:-127.0.0.1}"
NAO_PORT_ARG="${3:-65022}"

# Path di Python 2.7 (necessario per il controller robot con qi SDK)
PYTHON27="${PYTHON27:-python2.7}"

# Path dell'SDK Choregraphe (modifica se necessario)
NAOQI_SDK="${NAOQI_SDK_PATH:-}"

echo ""
echo "==============================================="
echo "   HRI POKER EXPERIMENT - Avvio Sistema"
echo "==============================================="
echo ""

# Directory del progetto
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Configurazione modalita'
if [ "$MODE" = "simulate" ]; then
    export SIMULATION_MODE="true"
    echo "  Modalita':  SIMULAZIONE (senza robot)"
else
    export SIMULATION_MODE="false"
    echo "  Modalita':  ROBOT (collegamento Choregraphe/NAO)"
fi

export NAO_IP="$NAO_IP_ARG"
export NAO_PORT="$NAO_PORT_ARG"
export PYTHON_PATH="$PYTHON27"
if [ -n "$NAOQI_SDK" ]; then
    export NAOQI_SDK_PATH="$NAOQI_SDK"
fi

echo "  NAO IP:     $NAO_IP:$NAO_PORT"
echo "  Python 2.7: $PYTHON27"
echo "  SDK Path:   ${NAOQI_SDK_PATH:-non impostato}"
echo "  Directory:  $PROJECT_DIR"
echo ""

# --- Virtual environment ---
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo "[OK] Virtual environment attivato"
else
    echo "[!] Virtual environment non trovato in .venv/"
    echo "    Creo il venv e installo le dipendenze..."
    python3 -m venv "$PROJECT_DIR/.venv"
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# --- Verifica Python 2.7 (solo modalita' robot) ---
if [ "$MODE" = "robot" ]; then
    if command -v "$PYTHON27" &> /dev/null; then
        echo "[OK] Python 2.7 trovato: $PYTHON27"
        if $PYTHON27 -c "import qi" 2>/dev/null; then
            echo "[OK] Modulo qi (NAOqi SDK) disponibile"
        else
            echo "[!] ATTENZIONE: modulo qi non trovato."
            echo "    Imposta NAOQI_SDK_PATH con il percorso della lib dell'SDK."
        fi
    else
        echo "[!] ATTENZIONE: Python 2.7 non trovato ($PYTHON27)"
        echo "    Il server partira' ma i comandi robot falliranno."
    fi
fi

# --- Verifica Flask ---
if python -c "import flask" 2>/dev/null; then
    FLASK_VER=$(python -c "import flask; print(flask.__version__)")
    echo "[OK] Flask $FLASK_VER"
else
    echo "[!] Flask non trovato. Installazione in corso..."
    pip install flask
fi

# --- Crea cartella dati ---
mkdir -p "$PROJECT_DIR/data"

# --- Avvio ---
echo ""
echo "==============================================="
echo "   Avvio server Flask..."
echo ""
echo "   Interfacce:"
echo "     Player:  http://localhost:5000/player"
echo "     Robot:   http://localhost:5000/robot"
echo "     Admin:   http://localhost:5000/admin"
echo ""
if [ "$MODE" = "robot" ]; then
    echo "   Assicurati che Choregraphe sia aperto"
    echo "   con un robot virtuale su $NAO_IP:$NAO_PORT"
    echo ""
fi
echo "   Premi Ctrl+C per fermare il server"
echo "==============================================="
echo ""

python "$PROJECT_DIR/server.py"
