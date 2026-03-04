#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stato del gioco e logica di decisione per HRI Poker Experiment.

Contiene la classe GameState che gestisce:
- Stato completo della partita (chips, carte, turni)
- Mani predeterminate per l'esperimento overtrust
- Logica AI del robot (strategia per ogni mano)
- Avanzamento delle fasi di gioco
- Gestione azioni utente e admin
"""

from __future__ import print_function
import time
import random
import threading
from datetime import datetime

from config import (
    STARTING_CHIPS, SMALL_BLIND, BIG_BLIND,
    ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX,
)
from data_logger import log_experiment_result, log_questionnaire


class GameState:
    """Gestisce lo stato completo del gioco e la logica di decisione."""

    # Fasi dell'esperimento
    PHASE_WAITING = "waiting"
    PHASE_HAND_1 = "hand_1"
    PHASE_HAND_2 = "hand_2"
    PHASE_HAND_3 = "hand_3"
    PHASE_QUESTIONNAIRE = "questionnaire"
    PHASE_END = "end"

    # Street del poker
    STREET_PREFLOP = "preflop"
    STREET_FLOP = "flop"
    STREET_TURN = "turn"
    STREET_RIVER = "river"
    STREET_SHOWDOWN = "showdown"

    def __init__(self):
        self._trigger_robot = lambda action: print("[ROBOT] {}".format(action))
        self.reset()

    def set_robot_trigger(self, fn):
        """Imposta la funzione per inviare comandi al robot."""
        self._trigger_robot = fn

    def trigger_robot(self, action):
        """Invia un comando al robot."""
        return self._trigger_robot(action)

    # =========================================================================
    # GESTIONE STATO
    # =========================================================================

    def reset(self):
        """Reset completo dello stato di gioco."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.participant_id = None
        self.phase = self.PHASE_WAITING
        self.current_hand = 0

        self.user_chips = STARTING_CHIPS
        self.robot_chips = STARTING_CHIPS

        self.street = None
        self.pot = 0
        self.user_bet = 0
        self.robot_bet = 0
        self.current_bet = 0

        self.turn = None
        self.hand_over = False
        self.winner = None
        self.last_action = None
        self.last_action_by = None
        self._last_street_announced = None

        self.user_cards = []
        self.robot_cards = []
        self.community_cards = []
        self.revealed_community = 0
        self.show_robot_cards = False

        # Dati esperimento
        self.user_decision_on_bluff = None
        self.user_actions = {1: [], 2: [], 3: []}

        # Robot thinking
        self.robot_thinking = False

        self._setup_rigged_hands()

    def _setup_rigged_hands(self):
        """Mani predeterminate per l'esperimento."""
        self.hands = {
            1: {  # Establishment: Utente vince - costruisce fiducia
                "user": ["10_of_hearts", "10_of_spades"],
                "robot": ["ace_of_spades", "king_of_hearts"],
                "community": ["7_of_clubs", "3_of_spades", "jack_of_diamonds",
                              "10_of_diamonds", "5_of_clubs"],
                "robot_wins": False
            },
            2: {  # BLUFF: Utente ha mano fortissima, robot bluffa
                "user": ["king_of_spades", "king_of_diamonds"],
                "robot": ["3_of_clubs", "5_of_hearts"],
                "community": ["9_of_hearts", "4_of_diamonds", "2_of_spades",
                              "king_of_clubs", "8_of_clubs"],
                "robot_wins": False
            },
            3: {  # Cooldown: Utente vince
                "user": ["queen_of_hearts", "3_of_hearts"],
                "robot": ["jack_of_hearts", "10_of_diamonds"],
                "community": ["queen_of_spades", "5_of_clubs", "queen_of_clubs",
                              "7_of_clubs", "2_of_hearts"],
                "robot_wins": False
            }
        }

    def start_hand(self, hand_number):
        """Inizia una nuova mano."""
        self.current_hand = hand_number
        self.phase = "hand_{}".format(hand_number)

        hand_data = self.hands[hand_number]
        self.user_cards = hand_data["user"]
        self.robot_cards = hand_data["robot"]
        self.community_cards = hand_data["community"]

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
        self._last_street_announced = None

        self.user_actions[hand_number] = []

        self._post_blinds()

    def _post_blinds(self):
        """Posta i blind automaticamente."""
        sb = min(SMALL_BLIND, self.user_chips)
        bb = min(BIG_BLIND, self.robot_chips)

        self.user_chips -= sb
        self.user_bet = sb
        self.robot_chips -= bb
        self.robot_bet = bb

        self.pot = sb + bb
        self.current_bet = bb
        self.turn = "user"

    # =========================================================================
    # QUERY STATO (per le interfacce)
    # =========================================================================

    def get_player_state(self):
        """Stato per l'interfaccia player (utente)."""
        return {
            "session_id": self.session_id,
            "hand_number": self.current_hand,
            "total_hands": 3,
            "user_chips": self.user_chips,
            "robot_chips": self.robot_chips,
            "pot": self.pot,
            "user_bet": self.user_bet,
            "robot_bet": self.robot_bet,
            "current_bet": self.current_bet,
            "my_cards": self.user_cards,
            "opponent_cards": self.robot_cards if self.show_robot_cards else [],
            "community_cards": self.community_cards[:self.revealed_community],
            "street": self.street,
            "is_my_turn": self.turn == "user" and not self.hand_over,
            "hand_over": self.hand_over,
            "winner": self.winner,
            "i_won": self.winner == "user" if self.winner else None,
            "can_check": self.current_bet == self.user_bet,
            "call_amount": self.current_bet - self.user_bet,
            "min_raise": self.current_bet + BIG_BLIND,
            "can_raise": self.robot_chips > 0,
            "opponent_is_allin": self.robot_chips == 0,
            "phase": "playing" if self.phase.startswith("hand") else self.phase,
            "last_action": self.last_action,
            "last_action_by": self.last_action_by,
            "opponent_thinking": self.robot_thinking,
            "show_opponent_cards": self.show_robot_cards
        }

    def get_robot_state(self):
        """Stato per l'interfaccia robot (speculare)."""
        return {
            "session_id": self.session_id,
            "hand_number": self.current_hand,
            "total_hands": 3,
            "user_chips": self.robot_chips,
            "robot_chips": self.user_chips,
            "pot": self.pot,
            "user_bet": self.robot_bet,
            "robot_bet": self.user_bet,
            "current_bet": self.current_bet,
            "my_cards": self.robot_cards,
            "opponent_cards": self.user_cards if self.show_robot_cards else [],
            "community_cards": self.community_cards[:self.revealed_community],
            "street": self.street,
            "is_my_turn": self.turn == "robot" and not self.hand_over,
            "hand_over": self.hand_over,
            "winner": self.winner,
            "i_won": self.winner == "robot" if self.winner else None,
            "can_check": self.current_bet == self.robot_bet,
            "call_amount": self.current_bet - self.robot_bet,
            "min_raise": self.current_bet + BIG_BLIND,
            "phase": "playing" if self.phase.startswith("hand") else self.phase,
            "last_action": self.last_action,
            "last_action_by": ("opponent" if self.last_action_by == "user"
                               else ("me" if self.last_action_by == "robot"
                                     else None)),
            "opponent_thinking": False,
            "show_opponent_cards": self.show_robot_cards
        }

    def get_admin_state(self):
        """Stato completo per l'interfaccia admin."""
        return {
            "session_id": self.session_id,
            "participant_id": self.participant_id,
            "phase": self.phase,
            "phase_name": {
                "waiting": "In Attesa",
                "hand_1": "Mano 1 (Establishment)",
                "hand_2": "Mano 2 (BLUFF)",
                "hand_3": "Mano 3 (Cooldown)",
                "questionnaire": "Questionario",
                "end": "Fine"
            }.get(self.phase, self.phase),
            "current_hand": self.current_hand,
            "is_bluff_hand": self.current_hand == 2,
            "street": self.street,
            "user_chips": self.user_chips,
            "robot_chips": self.robot_chips,
            "pot": self.pot,
            "user_bet": self.user_bet,
            "robot_bet": self.robot_bet,
            "current_bet": self.current_bet,
            "user_cards": self.user_cards,
            "robot_cards": self.robot_cards,
            "community_cards": self.community_cards,
            "revealed_community": self.revealed_community,
            "turn": self.turn,
            "hand_over": self.hand_over,
            "winner": self.winner,
            "last_action": self.last_action,
            "last_action_by": self.last_action_by,
            "robot_thinking": self.robot_thinking,
            "user_decision_on_bluff": self.user_decision_on_bluff,
            "user_actions": self.user_actions
        }

    # =========================================================================
    # AZIONI DEL PLAYER
    # =========================================================================

    def handle_player_action(self, action, amount=0):
        """Gestisce un'azione dell'utente. Restituisce un dict di risposta."""
        action = action.lower()
        print("\n[PLAYER] Azione: {}".format(action))

        if self.turn != "user" or self.hand_over:
            return {"success": False, "error": "Non e' il tuo turno"}

        handlers = {
            "fold":  self._player_fold,
            "check": self._player_check,
            "call":  self._player_call,
            "raise": lambda: self._player_raise(amount),
            "allin": self._player_allin,
        }

        handler = handlers.get(action)
        if handler:
            return handler()
        return {"success": False, "error": "Azione non valida"}

    def _player_fold(self):
        self.hand_over = True
        self.winner = "robot"
        self.robot_chips += self.pot
        self.pot = 0
        self.last_action = "fold"
        self.last_action_by = "user"

        self.user_actions[self.current_hand].append("fold")
        if self.current_hand == 2:
            self.user_decision_on_bluff = "fold"
            self._log_bluff_result()
            self.trigger_robot("bluff_success")
        else:
            self.trigger_robot("react_user_fold")

        return {"success": True, "action": "fold"}

    def _player_check(self):
        if self.current_bet > self.user_bet:
            return {"success": False, "error": "Non puoi fare check"}

        self.last_action = "check"
        self.last_action_by = "user"

        self.user_actions[self.current_hand].append("check")

        self.turn = "robot"

        self.trigger_robot("react_user_check")
        self.robot_make_decision()
        return {"success": True, "action": "check"}

    def _player_call(self):
        call_amount = self.current_bet - self.user_bet
        if call_amount <= 0:
            return {"success": False, "error": "Niente da chiamare"}

        actual_call = min(call_amount, self.user_chips)
        self.user_chips -= actual_call
        self.user_bet += actual_call
        self.pot += actual_call

        self.last_action = "call {}".format(actual_call)
        self.last_action_by = "user"

        self.user_actions[self.current_hand].append("call")
        # Tracciamento decisione bluff (mano 2)
        if self.current_hand == 2:
            self.user_decision_on_bluff = "call"

        # Reazione del robot (skip preflop e momenti di showdown)
        if (self.street not in [self.STREET_PREFLOP, self.STREET_RIVER]
                and self.robot_chips > 0 and self.user_chips > 0):
            self.trigger_robot("react_user_call")

        # Risolvi stato
        if self.robot_chips == 0 or self.user_chips == 0:
            self._do_showdown()
        elif self.street == self.STREET_PREFLOP and self.current_bet == BIG_BLIND:
            self.turn = "robot"
            self.robot_make_decision()
        elif self.street == self.STREET_RIVER and self.user_bet == self.robot_bet:
            self._do_showdown()
        elif self.user_bet == self.robot_bet:
            self._check_advance_street()
        else:
            self.turn = "robot"
            self.robot_make_decision()

        return {"success": True, "action": "call", "amount": actual_call}

    def _player_raise(self, amount):
        if self.robot_chips == 0:
            return {"success": False,
                    "error": "Non puoi rilanciare, l'avversario e' all-in. "
                             "Puoi solo chiamare o foldare."}

        min_raise = self.current_bet + BIG_BLIND
        if amount < min_raise:
            return {"success": False,
                    "error": "Rilancio minimo: {}".format(min_raise)}

        actual_raise = min(amount, self.user_chips + self.user_bet)
        chips_needed = actual_raise - self.user_bet

        self.user_chips -= chips_needed
        self.pot += chips_needed
        self.user_bet = actual_raise
        self.current_bet = actual_raise

        self.last_action = "raise {}".format(actual_raise)
        self.last_action_by = "user"

        self.user_actions[self.current_hand].append("raise {}".format(actual_raise))

        self.turn = "robot"

        self.trigger_robot("react_user_raise")
        self.robot_make_decision()
        return {"success": True, "action": "raise", "amount": actual_raise}

    def _player_allin(self):
        allin_amount = self.user_chips
        self.user_chips = 0
        self.pot += allin_amount
        new_total = self.user_bet + allin_amount

        if new_total > self.current_bet:
            self.current_bet = new_total
        self.user_bet = new_total

        self.last_action = "ALL-IN {}".format(allin_amount)
        self.last_action_by = "user"

        self.user_actions[self.current_hand].append("allin")
        # Tracciamento bluff
        if self.current_hand == 2:
            self.user_decision_on_bluff = "allin"

        self.trigger_robot("react_user_allin")

        if self.robot_chips == 0:
            self._do_showdown()
        elif self.user_bet <= self.robot_bet:
            self._do_showdown()
        else:
            self.turn = "robot"
            self.robot_make_decision()

        return {"success": True, "action": "allin", "amount": allin_amount}

    # =========================================================================
    # AZIONI ADMIN
    # =========================================================================

    def handle_admin_action(self, action, data):
        """Gestisce un'azione dell'amministratore."""
        action = action.lower()
        print("\n[ADMIN] Azione: {}".format(action))

        if action == "start_experiment":
            self.reset()
            self.participant_id = data.get("participant_id", "")
            self.trigger_robot("intro")
            return {"success": True, "message": "Esperimento iniziato"}

        elif action == "start_hand":
            hand_num = data.get("hand_number", self.current_hand + 1)
            if hand_num < 1 or hand_num > 3:
                return {"success": False, "error": "Numero mano non valido"}
            self.start_hand(hand_num)
            self._announce_hand_start(hand_num)
            return {"success": True,
                    "message": "Mano {} iniziata".format(hand_num)}

        elif action == "next_hand":
            next_hand = self.current_hand + 1
            if next_hand > 3:
                self.phase = self.PHASE_QUESTIONNAIRE
                return {"success": True, "message": "Questionario"}
            self.start_hand(next_hand)
            self._announce_hand_start(next_hand)
            return {"success": True,
                    "message": "Mano {} iniziata".format(next_hand)}

        elif action == "show_questionnaire":
            self.phase = self.PHASE_QUESTIONNAIRE
            return {"success": True}

        elif action == "reset":
            self.reset()
            return {"success": True, "message": "Reset completato"}

        elif action == "trigger_robot":
            behavior = data.get("behavior", "")
            self.trigger_robot(behavior)
            return {"success": True}

        return {"success": False, "error": "Azione non valida"}

    def _announce_hand_start(self, hand_num):
        """Annuncia l'inizio di una mano (mano 3 gestita da cooldown)."""
        if hand_num == 1:
            self.trigger_robot("hand_start_1")
        elif hand_num == 2:
            self.trigger_robot("hand_start_2")

    def handle_questionnaire(self, questionnaire_data):
        """Gestisce l'invio del questionario."""
        log_questionnaire(self.session_id, questionnaire_data)
        self.phase = self.PHASE_END
        return {"success": True}

    # =========================================================================
    # ROBOT AI - DECISIONI AUTOMATICHE
    # =========================================================================

    def robot_make_decision(self):
        """Il robot prende una decisione (eseguita in background)."""
        if self.turn != "robot" or self.hand_over:
            return

        self.robot_thinking = True
        think_time = random.uniform(ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX)

        def delayed_action():
            time.sleep(think_time)
            self._execute_robot_decision()
            self.robot_thinking = False

        thread = threading.Thread(target=delayed_action)
        thread.daemon = True
        thread.start()

    def _execute_robot_decision(self):
        """Esegue la decisione del robot basata sulla strategia per mano."""
        hand = self.current_hand
        street = self.street
        call_amount = self.current_bet - self.robot_bet
        user_is_allin = self.user_chips == 0

        print("[ROBOT AI] Mano {}, Street {}, Bet: {}, Robot bet: {}, "
              "User all-in: {}".format(
                  hand, street, self.current_bet, self.robot_bet, user_is_allin))

        # Annuncio nuove carte comuni (solo mani non-bluff)
        if street != self._last_street_announced and hand != 2:
            if street == self.STREET_FLOP:
                self._last_street_announced = street
                self.trigger_robot("new_flop")
            elif street == self.STREET_TURN:
                self._last_street_announced = street
                self.trigger_robot("new_turn")
            elif street == self.STREET_RIVER:
                self._last_street_announced = street
                self.trigger_robot("new_river")

        # Strategia per mano
        if hand == 1:
            self._ai_hand_1(call_amount, user_is_allin, street)
        elif hand == 2:
            self._ai_hand_2(call_amount, user_is_allin, street)
        elif hand == 3:
            self._ai_hand_3(call_amount, user_is_allin, street)

    # --- Strategia per mano ---

    def _ai_hand_1(self, call_amount, user_is_allin, street):
        """Mano 1 - Establishment: Robot ha A-K, gioca credibile ma perde."""
        if user_is_allin and call_amount > 0:
            self._do_robot_fold()
        elif call_amount > 0:
            if call_amount > self.robot_chips * 0.5:
                self._do_robot_fold()
                return
            self._do_robot_call()
            self._check_advance_street()
        elif street == self.STREET_PREFLOP and self.robot_bet == BIG_BLIND:
            self._do_robot_raise(BIG_BLIND)
        elif street == self.STREET_RIVER:
            self._do_robot_raise(30)
        else:
            self._do_robot_check()
            self._check_advance_street()

    def _ai_hand_2(self, call_amount, user_is_allin, street):
        """Mano 2 - BLUFF: puntate crescenti + ALL-IN al river."""
        if user_is_allin and call_amount > 0:
            self._do_robot_call()
            self._do_showdown()
        elif call_amount > 0:
            # Quando l'utente rilancia, il robot ri-rilancia aggressivamente
            # (tranne al preflop dove chiama e basta)
            if street == self.STREET_FLOP:
                reraise = max(BIG_BLIND * 2, self.robot_chips // 7)
                self._do_robot_raise(reraise, "robot_raise_bluff_1")
            elif street == self.STREET_TURN:
                reraise = max(BIG_BLIND * 3, self.robot_chips // 4)
                self._do_robot_raise(reraise, "robot_raise_bluff_2")
            elif street == self.STREET_RIVER:
                self.trigger_robot("bluff")
                self._do_robot_allin(announce_action=None)
            else:
                self._do_robot_call()
                self._check_advance_street()
        elif street == self.STREET_PREFLOP:
            self._do_robot_check()
            self._check_advance_street()
        elif street == self.STREET_FLOP:
            bet_amount = max(BIG_BLIND * 2, self.robot_chips // 7)
            self._do_robot_raise(bet_amount, "robot_raise_bluff_1")
        elif street == self.STREET_TURN:
            bet_amount = max(BIG_BLIND * 3, self.robot_chips // 4)
            self._do_robot_raise(bet_amount, "robot_raise_bluff_2")
        elif street == self.STREET_RIVER:
            self.trigger_robot("bluff")
            self._do_robot_allin(announce_action=None)
        else:
            self._do_robot_check()
            self._check_advance_street()

    def _ai_hand_3(self, call_amount, user_is_allin, street):
        """Mano 3 - Cooldown: gioca passivo."""
        if street == self.STREET_PREFLOP and self.robot_bet == BIG_BLIND:
            self.trigger_robot("cooldown")

        if user_is_allin and call_amount > 0:
            if call_amount > self.robot_chips // 2:
                self._do_robot_fold()
            else:
                self._do_robot_call()
                self._do_showdown()
            return
        elif call_amount > 0:
            if call_amount > self.robot_chips // 2:
                self._do_robot_fold()
            else:
                self._do_robot_call()
                self._check_advance_street()
        else:
            self._do_robot_check()
            self._check_advance_street()

    # =========================================================================
    # AZIONI DEL ROBOT (mutazioni di stato)
    # =========================================================================

    def _do_robot_check(self):
        self.last_action = "check"
        self.last_action_by = "robot"
        self.trigger_robot("robot_check")
        self.turn = "user"
        print("[ROBOT AI] Check")

    def _do_robot_call(self):
        call_amount = self.current_bet - self.robot_bet
        actual_call = min(call_amount, self.robot_chips)

        self.robot_chips -= actual_call
        self.robot_bet += actual_call
        self.pot += actual_call

        if self.robot_chips == 0:
            self.last_action = "ALL-IN (call {})".format(actual_call)
            self.trigger_robot("robot_call_allin")
        else:
            self.last_action = "call {}".format(actual_call)
            self.trigger_robot("robot_call")
        self.last_action_by = "robot"
        self.turn = "user"
        print("[ROBOT AI] Call {} (chips: {})".format(actual_call,
                                                      self.robot_chips))

    def _do_robot_raise(self, amount, robot_action=None):
        total_bet = self.current_bet + amount
        chips_needed = total_bet - self.robot_bet
        actual_chips = min(chips_needed, self.robot_chips)

        self.robot_chips -= actual_chips
        self.pot += actual_chips
        self.robot_bet += actual_chips
        self.current_bet = self.robot_bet

        self.last_action = "raise {}".format(self.robot_bet)
        self.last_action_by = "robot"

        if robot_action:
            self.trigger_robot(robot_action)
        elif self.current_hand == 2:
            self.trigger_robot("robot_raise_bluff")
        else:
            self.trigger_robot("robot_raise")

        self.turn = "user"
        print("[ROBOT AI] Raise a {}".format(self.robot_bet))

    def _do_robot_allin(self, announce_action="robot_allin"):
        if announce_action:
            self.trigger_robot(announce_action)

        allin_amount = self.robot_chips
        self.robot_chips = 0
        self.pot += allin_amount
        self.robot_bet += allin_amount
        self.current_bet = self.robot_bet

        self.last_action = "ALL-IN {}".format(allin_amount)
        self.last_action_by = "robot"
        self.turn = "user"
        print("[ROBOT AI] ALL-IN! {}".format(allin_amount))

    def _do_robot_fold(self):
        self.trigger_robot("robot_fold")

        self.hand_over = True
        self.winner = "user"
        self.user_chips += self.pot
        self.pot = 0
        self.last_action = "fold"
        self.last_action_by = "robot"
        print("[ROBOT AI] Fold")

    # =========================================================================
    # GESTIONE STREET E SHOWDOWN
    # =========================================================================

    def _check_advance_street(self):
        """Controlla se entrambi hanno agito e avanza la street."""
        if self.hand_over:
            return
        if self.user_bet == self.robot_bet:
            if self.user_chips == 0 or self.robot_chips == 0:
                self._do_showdown()
            else:
                self._advance_to_next_street()

    def _advance_to_next_street(self):
        """Avanza alla prossima street."""
        streets = [self.STREET_PREFLOP, self.STREET_FLOP,
                   self.STREET_TURN, self.STREET_RIVER]

        if self.street not in streets:
            return

        current_idx = streets.index(self.street)

        if current_idx < len(streets) - 1:
            self.street = streets[current_idx + 1]
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

            print("[GAME] Avanzato a {}, {} carte rivelate".format(
                self.street, self.revealed_community))
        else:
            self._do_showdown()

    def _do_showdown(self):
        """Esegue lo showdown."""
        self.street = self.STREET_SHOWDOWN
        self.revealed_community = 5
        self.show_robot_cards = True
        self.hand_over = True

        hand_data = self.hands.get(self.current_hand, {})
        self.winner = ("robot" if hand_data.get("robot_wins", False)
                       else "user")

        if self.winner == "user":
            self.user_chips += self.pot
            if self.current_hand == 2:
                self.trigger_robot("bluff_failed")
            else:
                self.trigger_robot("defeat")
        else:
            self.robot_chips += self.pot
            self.trigger_robot("win_claim")
        self.pot = 0

        if self.current_hand == 2:
            self._log_bluff_result()

        print("[GAME] Showdown! Vince: {}".format(self.winner))

    def _log_bluff_result(self):
        """Logga il risultato della mano di bluff."""
        log_experiment_result(
            self.session_id,
            self.participant_id,
            self.user_decision_on_bluff,
            self.user_actions,
            self.user_chips,
            self.robot_chips
        )
