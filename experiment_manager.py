#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manager dell'esperimento HRI Poker.
Gestisce le mani truccate per l'esperimento (establishment, bluff 1, bluff 2) e la fase corrente.
Traccia anche i dati temporali: durata sessione, durata mani, tempi di reazione.
"""

from datetime import datetime


class ExperimentManager:
    PHASE_WAITING = "waiting"
    PHASE_HAND_1 = "hand_1"
    PHASE_HAND_2 = "hand_2"
    PHASE_HAND_3 = "hand_3"
    PHASE_QUESTIONNAIRE = "questionnaire"
    PHASE_END = "end"

    def __init__(self):
        self.robot_mode = "simulation"  # "simulation" / "real" / "disabled"
        self.reset()

    def reset(self):
        self.phase = self.PHASE_WAITING
        self.current_hand = 0
        self.session_id = None
        self.participant_id = None
        self.user_actions = {1: [], 2: [], 3: []}
        self.user_decision_on_bluff = None
        self.winners = {1: None, 2: None, 3: None}
        
        # --- Timing ---
        self.session_start_time = None
        self.hand_start_times = {}
        self.hand_end_times = {}
        self.turn_start_time = None
        self.reaction_times = {1: [], 2: [], 3: []}  # {hand: [(street, ms), ...]}
        self.action_count = {1: 0, 2: 0, 3: 0}
        
        self.hands = {
            1: {  # Establishment: Utente vince (tris di 10)
                "user": ["10_of_hearts", "10_of_spades"],
                "robot": ["ace_of_spades", "king_of_hearts"],
                "community": ["7_of_clubs", "3_of_spades", "jack_of_diamonds",
                              "10_of_diamonds", "5_of_clubs"],
                "robot_wins": False
            },
            2: {  # BLUFF: Utente ha mano fortissima (tris di re), robot bluffa
                "user": ["king_of_spades", "king_of_diamonds"],
                "robot": ["3_of_clubs", "5_of_hearts"],
                "community": ["9_of_hearts", "4_of_diamonds", "2_of_spades",
                              "king_of_clubs", "8_of_clubs"],
                "robot_wins": False
            },
            3: {  # BLUFF 2: Utente ha mano fortissima (tris di assi), robot bluffa
                "user": ["ace_of_hearts", "ace_of_diamonds"],
                "robot": ["4_of_clubs", "6_of_hearts"],
                "community": ["ace_of_clubs", "jack_of_hearts", "7_of_spades",
                              "8_of_diamonds", "2_of_clubs"],
                "robot_wins": False
            }
        }

    # --- Session timing ---

    def start_session(self):
        """Registra il timestamp di inizio esperimento."""
        self.session_start_time = datetime.now()

    def get_session_duration_s(self):
        """Ritorna la durata della sessione in secondi, o None."""
        if self.session_start_time is None:
            return None
        delta = datetime.now() - self.session_start_time
        return round(delta.total_seconds(), 1)

    # --- Hand timing ---

    def start_hand(self, hand_number):
        self.current_hand = hand_number
        self.phase = "hand_{}".format(hand_number)
        self.user_actions[hand_number] = []
        self.hand_start_times[hand_number] = datetime.now()
        self.reaction_times[hand_number] = []
        self.action_count[hand_number] = 0
        return self.hands[hand_number]

    def end_hand(self):
        """Registra il timestamp di fine della mano corrente."""
        if self.current_hand:
            self.hand_end_times[self.current_hand] = datetime.now()

    def get_hand_duration_s(self, hand_number):
        """Ritorna la durata di una mano in secondi, o None."""
        start = self.hand_start_times.get(hand_number)
        end = self.hand_end_times.get(hand_number)
        if start is None:
            return None
        if end is None:
            # Mano in corso: calcola dal tempo corrente
            delta = datetime.now() - start
        else:
            delta = end - start
        return round(delta.total_seconds(), 1)

    # --- Reaction time ---

    def start_user_turn(self):
        """Registra il timestamp dell'inizio del turno dell'utente."""
        self.turn_start_time = datetime.now()

    def record_reaction_time(self, street):
        """Calcola il tempo di reazione dall'inizio del turno utente e lo salva."""
        if self.turn_start_time is None or self.current_hand == 0:
            return None
        delta_ms = round((datetime.now() - self.turn_start_time).total_seconds() * 1000)
        self.reaction_times[self.current_hand].append((street, delta_ms))
        self.turn_start_time = None  # Reset per la prossima azione
        return delta_ms

    def get_avg_reaction_time_ms(self, hand_number=None):
        """Ritorna il tempo di reazione medio in ms per una mano o l'intera sessione."""
        if hand_number is not None:
            times = self.reaction_times.get(hand_number, [])
            if not times:
                return None
            return round(sum(t[1] for t in times) / len(times))
        # Media globale
        all_times = []
        for h in self.reaction_times.values():
            all_times.extend(t[1] for t in h)
        if not all_times:
            return None
        return round(sum(all_times) / len(all_times))

    def get_last_reaction_time_ms(self):
        """Ritorna l'ultimo tempo di reazione registrato, o None."""
        hand_times = self.reaction_times.get(self.current_hand, [])
        if hand_times:
            return hand_times[-1][1]
        return None

    # --- Action counting ---

    def log_action(self, action):
        if self.current_hand in self.user_actions:
            self.user_actions[self.current_hand].append(action)
        if self.current_hand in self.action_count:
            self.action_count[self.current_hand] += 1

    def set_bluff_decision(self, decision):
        if self.current_hand in (2, 3):
            self.user_decision_on_bluff = decision
