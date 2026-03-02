#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configurazione centralizzata per HRI Poker Experiment.

Carica le variabili dal file .env e configura:
- Connessione robot NAO
- Path SDK Choregraphe (sostituisce sdk_config.py)
- Parametri server Flask
- Parametri di gioco

Uso:
    from config import NAO_IP, SIMULATION_MODE, ...
"""

from __future__ import print_function
import os
import sys
import struct


# =============================================================================
# CARICAMENTO .env
# =============================================================================

def _load_env_file():
    """Carica variabili dal file .env (fallback se python-dotenv non e' installato)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    _load_env_file()


# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ROBOT_SCRIPT = os.path.join(BASE_DIR, "robot_controller.py")


# =============================================================================
# CONNESSIONE ROBOT NAO
# =============================================================================

NAO_IP = os.environ.get("NAO_IP", "127.0.0.1")
NAO_PORT = int(os.environ.get("NAO_PORT", "9559"))
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "true").lower() == "true"

# Python 2.7 per NAOqi SDK (retrocompatibile con vecchio PYTHON_PATH)
PYTHON27_PATH = os.environ.get("PYTHON27_PATH",
                               os.environ.get("PYTHON_PATH", "python"))


# =============================================================================
# SDK CHOREGRAPHE (sostituisce sdk_config.py)
# =============================================================================

NAOQI_SDK_PATH = os.environ.get("NAOQI_SDK_PATH", "")
CHOREGRAPHE_LIB = os.environ.get("CHOREGRAPHE_LIB", "")

_CHOREGRAPHE_PATHS = [
    r"C:\Program Files (x86)\Aldebaran Robotics\Choregraphe Suite 2.1\lib",
    r"C:\Program Files\Aldebaran Robotics\Choregraphe Suite 2.1\lib",
    NAOQI_SDK_PATH,
    CHOREGRAPHE_LIB,
]


def _bits_python():
    return struct.calcsize("P") * 8


SDK_FOUND = False

for _path in _CHOREGRAPHE_PATHS:
    if _path and os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
        try:
            import qi as _qi_test
            SDK_FOUND = True
            print("[SDK] Trovato qi in: {}".format(_path))
            break
        except ImportError:
            pass

if not SDK_FOUND:
    print("[SDK WARN] SDK Choregraphe non trovato automaticamente.")
    print("[SDK WARN] Python {} {} bit".format(sys.version.split()[0], _bits_python()))
    print("[SDK WARN] Imposta NAOQI_SDK_PATH nel file .env")


# =============================================================================
# SERVER FLASK
# =============================================================================

SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "5000"))


# =============================================================================
# PARAMETRI DI GIOCO
# =============================================================================

STARTING_CHIPS = int(os.environ.get("STARTING_CHIPS", "1000"))
SMALL_BLIND = int(os.environ.get("SMALL_BLIND", "10"))
BIG_BLIND = int(os.environ.get("BIG_BLIND", "20"))

ROBOT_THINK_TIME_MIN = float(os.environ.get("ROBOT_THINK_TIME_MIN", "1"))
ROBOT_THINK_TIME_MAX = float(os.environ.get("ROBOT_THINK_TIME_MAX", "2"))


# =============================================================================
# FILE DATI
# =============================================================================

DATA_FILE = os.path.join(DATA_DIR, "experiment_results.csv")
QUESTIONNAIRE_FILE = os.path.join(DATA_DIR, "questionnaire_results.csv")
