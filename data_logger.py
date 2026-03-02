#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging dei risultati dell'esperimento su CSV.

Gestisce:
- Inizializzazione dei file CSV (con header)
- Salvataggio risultati della mano di bluff
- Salvataggio risposte al questionario
"""

from __future__ import print_function
import os
import csv
from datetime import datetime

from config import DATA_DIR, DATA_FILE, QUESTIONNAIRE_FILE


def init_data_files():
    """Crea la cartella dati e inizializza i file CSV se non esistono."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "participant_id", "timestamp",
                "user_decision_on_bluff", "reaction_time_ms",
                "bluff_successful", "final_user_chips", "final_robot_chips"
            ])

    if not os.path.exists(QUESTIONNAIRE_FILE):
        with open(QUESTIONNAIRE_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "timestamp",
                "q1_trust", "q2_pressure", "q3_robot_competence",
                "q4_decision_confidence", "q5_would_play_again", "comments"
            ])


def log_experiment_result(session_id, participant_id, decision,
                          reaction_time_ms, user_chips, robot_chips):
    """Salva il risultato della mano di bluff."""
    try:
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id,
                participant_id or "anonimo",
                datetime.now().isoformat(),
                decision,
                round(reaction_time_ms, 2) if reaction_time_ms else 0,
                "yes" if decision == "fold" else "no",
                user_chips,
                robot_chips
            ])
        print("[DATA] Risultato salvato")
    except Exception as e:
        print("[DATA] Errore: {}".format(e))


def log_questionnaire(session_id, data):
    """Salva le risposte al questionario."""
    try:
        with open(QUESTIONNAIRE_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                session_id, datetime.now().isoformat(),
                data.get("q1", ""), data.get("q2", ""), data.get("q3", ""),
                data.get("q4", ""), data.get("q5", ""), data.get("comments", "")
            ])
    except Exception as e:
        print("[DATA] Errore questionario: {}".format(e))
