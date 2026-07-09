#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging dei risultati dell'esperimento su CSV.

Gestisce:
- Inizializzazione dei file CSV (con header)
- Salvataggio risultati della mano di bluff
- Salvataggio risposte al questionario
- Salvataggio risultati per ogni singola mano
- Log dettagliato di ogni azione con timestamp
"""

from __future__ import print_function
import os
import csv
import sys
from datetime import datetime
from config import DATA_DIR, DATA_FILE, HAND_RESULTS_FILE, ACTION_LOG_FILE


PY2 = sys.version_info[0] == 2


def _open_csv(path, mode):
    """Apre file CSV in modo compatibile tra Python 2 e 3."""
    if PY2:
        # In Python 2 csv richiede file binari per evitare righe vuote/TypeError.
        if 'b' not in mode:
            mode = mode + 'b'
        return open(path, mode)
    return open(path, mode, newline='')


def init_data_files():
    """Crea la cartella dati e inizializza i file CSV se non esistono."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(DATA_FILE):
        with _open_csv(DATA_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "nome", "timestamp",
                "vincitore mano 1", "vincitore mano 2", "vincitore mano 3",
                "durata totale dell'esperimento"
            ])

    if not os.path.exists(HAND_RESULTS_FILE):
        with _open_csv(HAND_RESULTS_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "participant_id", "timestamp",
                "hand_number", "hand_type",
                "winner", "user_chips_end", "robot_chips_end",
                "hand_duration_s", "action_count",
                "avg_reaction_time_ms", "robot_mode"
            ])

    if not os.path.exists(ACTION_LOG_FILE):
        with _open_csv(ACTION_LOG_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "timestamp",
                "hand_number", "street", "actor", "action",
                "reaction_time_ms"
            ])


def log_experiment_result(session_id, participant_id, winners, session_duration_s):
    """Salva il risultato dell'esperimento."""
    try:
        with _open_csv(DATA_FILE, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                participant_id or "anonimo",
                datetime.now().isoformat(),
                winners.get(1, ""),
                winners.get(2, ""),
                winners.get(3, ""),
                session_duration_s or ""
            ])
        print("[DATA] Risultato esperimento salvato")
    except Exception as e:
        print("[DATA] Errore: {}".format(e))


def log_hand_result(session_id, participant_id, hand_number, hand_type,
                    winner, user_chips, robot_chips,
                    hand_duration_s=None, action_count=0,
                    avg_reaction_time_ms=None, robot_mode=""):
    """Salva il risultato di una singola mano (tutte, non solo bluff)."""
    try:
        with _open_csv(HAND_RESULTS_FILE, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                participant_id or "anonimo",
                datetime.now().isoformat(),
                hand_number,
                hand_type,
                winner,
                user_chips,
                robot_chips,
                hand_duration_s or "",
                action_count,
                avg_reaction_time_ms or "",
                robot_mode
            ])
        print("[DATA] Risultato mano {} salvato".format(hand_number))
    except Exception as e:
        print("[DATA] Errore log mano: {}".format(e))


def log_action(session_id, hand_number, street, actor, action,
               reaction_time_ms=None):
    """Salva una singola azione nel log dettagliato con timestamp."""
    try:
        with _open_csv(ACTION_LOG_FILE, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                datetime.now().isoformat(),
                hand_number,
                street,
                actor,
                action,
                reaction_time_ms or ""
            ])
    except Exception as e:
        print("[DATA] Errore log azione: {}".format(e))
