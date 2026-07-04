#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Motore per le regole del Poker.
Gestisce chips, puntate, street e logica di base del Texas Hold'em.
"""

from config import STARTING_CHIPS, SMALL_BLIND, BIG_BLIND

class PokerEngine:
    STREET_PREFLOP = "preflop"
    STREET_FLOP = "flop"
    STREET_TURN = "turn"
    STREET_RIVER = "river"
    STREET_SHOWDOWN = "showdown"

    def __init__(self):
        self.reset()

    def reset(self):
        self.user_chips = STARTING_CHIPS
        self.robot_chips = STARTING_CHIPS
        self.pot = 0
        self.user_bet = 0
        self.robot_bet = 0
        self.current_bet = 0
        self.street = self.STREET_PREFLOP
        self.turn = None
        self.hand_over = False
        self.winner = None
        
        self.user_cards = []
        self.robot_cards = []
        self.community_cards = []
        self.revealed_community = 0
        self.show_robot_cards = False
        
        self.last_action = None
        self.last_action_by = None
        
    def start_hand(self, user_cards, robot_cards, community_cards):
        self.user_cards = user_cards
        self.robot_cards = robot_cards
        self.community_cards = community_cards
        
        self.street = self.STREET_PREFLOP
        self.revealed_community = 0
        self.pot = 0
        self.user_bet = 0
        self.robot_bet = 0
        self.current_bet = 0
        self.hand_over = False
        self.winner = None
        self.show_robot_cards = False
        self.last_action = None
        self.last_action_by = None
        
        self._post_blinds()

    def _post_blinds(self):
        sb = min(SMALL_BLIND, self.user_chips)
        bb = min(BIG_BLIND, self.robot_chips)

        self.user_chips -= sb
        self.user_bet = sb
        self.robot_chips -= bb
        self.robot_bet = bb

        self.pot = sb + bb
        self.current_bet = bb
        self.turn = "user"

    def can_check(self, player):
        bet = self.user_bet if player == "user" else self.robot_bet
        return self.current_bet == bet

    def can_raise(self, player):
        my_chips = self.user_chips if player == "user" else self.robot_chips
        opponent_chips = self.robot_chips if player == "user" else self.user_chips
        return my_chips > 0 and opponent_chips > 0

    def call_amount(self, player):
        bet = self.user_bet if player == "user" else self.robot_bet
        return self.current_bet - bet

    def advance_street(self):
        streets = [self.STREET_PREFLOP, self.STREET_FLOP, self.STREET_TURN, self.STREET_RIVER]
        if self.street not in streets:
            return False

        idx = streets.index(self.street)
        if idx < len(streets) - 1:
            self.street = streets[idx + 1]
            self.user_bet = 0
            self.robot_bet = 0
            self.current_bet = 0
            self.turn = "user"
            
            if self.street == self.STREET_FLOP:
                self.revealed_community = 3
            elif self.street == self.STREET_TURN:
                self.revealed_community = 4
            elif self.street == self.STREET_RIVER:
                self.revealed_community = 5
            return True
        return False
