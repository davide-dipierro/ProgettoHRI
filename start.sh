#!/bin/bash
# =============================================================================
# HRI Poker Experiment - Script di avvio
# =============================================================================

echo "=============================================="
echo "   HRI POKER EXPERIMENT - Avvio Sistema"
echo "=============================================="

# Directory del progetto
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Configurazione predefinita
export SIMULATION_MODE="${SIMULATION_MODE:-true}"
export NAO_IP="${NAO_IP:-127.0.0.1}"
export NAO_PORT="${NAO_PORT:-9559}"

echo ""
echo "Configurazione:"
echo "  - Modalità: $([ "$SIMULATION_MODE" = "true" ] && echo "🔬 SIMULAZIONE" || echo "🤖 ROBOT FISICO")"
echo "  - NAO IP: $NAO_IP:$NAO_PORT"
echo "  - Directory: $PROJECT_DIR"
echo ""

# Attiva venv
if [ -d "$PROJECT_DIR/.venv" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
    echo "✓ Virtual environment attivato"
else
    echo "⚠️  Virtual environment non trovato. Usa Python di sistema."
fi

# Verifica Python
if ! command -v python &> /dev/null; then
    echo "Errore: python non trovato!"
    exit 1
fi

# Verifica Flask
if ! python -c "import flask" 2>/dev/null; then
    echo "Flask non trovato. Installazione..."
    pip install flask
    if ! python -c "import flask" 2>/dev/null; then
        echo "Errore: impossibile installare Flask!"
        exit 1
    fi
fi
echo "Flask disponibile"

# Esporta il percorso Python per i subprocess del server
export PYTHON_PATH="$(which python)"
echo "Python: $PYTHON_PATH"

# Crea cartella dati se non esiste
mkdir -p "$PROJECT_DIR/data"

echo "=============================================="
echo "   Avvio server Flask..."
echo "   Interfacce:"
echo "     Player: http://localhost:5000/player"
echo "     Robot:  http://localhost:5000/robot"
echo "     Admin:  http://localhost:5000/admin"
echo "=============================================="
echo ""

# Avvia il server
python "$PROJECT_DIR/server.py"
