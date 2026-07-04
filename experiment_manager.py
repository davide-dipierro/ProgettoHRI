#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Manager dell'esperimento HRI Poker.
Gestisce le mani truccate per l'esperimento (establishment, bluff, cooldown) e la fase corrente.
"""

class ExperimentManager:
    PHASE_WAITING = "waiting"
    PHASE_HAND_1 = "hand_1"
    PHASE_HAND_2 = "hand_2"
    PHASE_HAND_3 = "hand_3"
    PHASE_QUESTIONNAIRE = "questionnaire"
    PHASE_END = "end"

    def __init__(self):
        self.reset()

    def reset(self):
        self.phase = self.PHASE_WAITING
        self.current_hand = 0
        self.session_id = None
        self.participant_id = None
        self.user_actions = {1: [], 2: [], 3: []}
        self.user_decision_on_bluff = None
        
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
            3: {  # Cooldown: Utente vince (tris di regine)
                "user": ["queen_of_hearts", "3_of_hearts"],
                "robot": ["jack_of_spades", "6_of_diamonds"],
                "community": ["queen_of_spades", "9_of_clubs", "queen_of_clubs",
                              "7_of_hearts", "2_of_hearts"],
                "robot_wins": False
            }
        }

    def start_hand(self, hand_number):
        self.current_hand = hand_number
        self.phase = "hand_{}".format(hand_number)
        self.user_actions[hand_number] = []
        return self.hands[hand_number]
        
    def log_action(self, action):
        if self.current_hand in self.user_actions:
            self.user_actions[self.current_hand].append(action)

    def set_bluff_decision(self, decision):
        if self.current_hand == 2:
            self.user_decision_on_bluff = decision
