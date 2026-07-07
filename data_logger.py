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

from config import DATA_DIR, DATA_FILE, QUESTIONNAIRE_FILE, HAND_RESULTS_FILE, ACTION_LOG_FILE


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
                "session_id", "participant_id", "timestamp",
                "user_decision_on_bluff",
                "user_actions_hand1", "user_actions_hand2", "user_actions_hand3",
                "bluff_successful", "final_user_chips", "final_robot_chips",
                "session_duration_s", "avg_reaction_time_ms", "robot_mode"
            ])

    if not os.path.exists(QUESTIONNAIRE_FILE):
        with _open_csv(QUESTIONNAIRE_FILE, 'w') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "timestamp",
                "q1_trust", "q2_pressure", "q3_robot_competence",
                "q4_decision_confidence", "q5_would_play_again", "comments"
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


def log_experiment_result(session_id, participant_id, decision,
                          user_actions, user_chips, robot_chips,
                          session_duration_s=None, avg_reaction_time_ms=None,
                          robot_mode=""):
    """Salva il risultato della mano di bluff."""
    try:
        actions_h1 = " -> ".join(user_actions.get(1, [])) if user_actions else ""
        actions_h2 = " -> ".join(user_actions.get(2, [])) if user_actions else ""
        actions_h3 = " -> ".join(user_actions.get(3, [])) if user_actions else ""
        with _open_csv(DATA_FILE, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                participant_id or "anonimo",
                datetime.now().isoformat(),
                decision,
                actions_h1,
                actions_h2,
                actions_h3,
                "yes" if decision == "fold" else "no",
                user_chips,
                robot_chips,
                session_duration_s or "",
                avg_reaction_time_ms or "",
                robot_mode
            ])
        print("[DATA] Risultato salvato")
    except Exception as e:
        print("[DATA] Errore: {}".format(e))


def log_questionnaire(session_id, data):
    """Salva le risposte al questionario."""
    try:
        with _open_csv(QUESTIONNAIRE_FILE, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id, datetime.now().isoformat(),
                data.get("q1", ""), data.get("q2", ""), data.get("q3", ""),
                data.get("q4", ""), data.get("q5", ""), data.get("comments", "")
            ])
    except Exception as e:
        print("[DATA] Errore questionario: {}".format(e))


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
