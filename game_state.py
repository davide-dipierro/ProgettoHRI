#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stato del gioco e logica di decisione per HRI Poker Experiment.
Facade pattern per orchestrare PokerEngine, ExperimentManager e RobotAI.
"""

from __future__ import print_function
import threading
from datetime import datetime

from poker_engine import PokerEngine
from experiment_manager import ExperimentManager
from robot_ai import RobotAI
from data_logger import log_experiment_result, log_hand_result, log_action
from config import BIG_BLIND

class GameState:
    def __init__(self):
        self._lock = threading.RLock()
        self.engine = PokerEngine()
        self.experiment = ExperimentManager()
        self.ai = RobotAI(self)
        self._trigger_robot_fn = lambda action: print("[ROBOT] {}".format(action))
        self.pending_robot_actions = 0
        self._last_street_announced = None

    def set_robot_trigger(self, fn):
        self._trigger_robot_fn = fn

    def trigger_robot(self, action):
        return self._trigger_robot_fn(action)

    def reset(self):
        with self._lock:
            self.engine.reset()
            self.experiment.reset()
            self.experiment.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.experiment.start_session()
            self._last_street_announced = None

    def start_hand(self, hand_number):
        with self._lock:
            hand_data = self.experiment.start_hand(hand_number)
            self.engine.start_hand(
                user_cards=hand_data["user"],
                robot_cards=hand_data["robot"],
                community_cards=hand_data["community"]
            )
            self._last_street_announced = None
            # Il turno iniziale va all'utente o al robot (dipende dal preflop)
            if self.engine.turn == "user":
                self.experiment.start_user_turn()

    # =========================================================================
    # QUERY STATO
    # =========================================================================
    def get_player_state(self):
        with self._lock:
            return {
                "session_id": self.experiment.session_id,
                "hand_number": self.experiment.current_hand,
                "total_hands": 3,
                "user_chips": self.engine.user_chips,
                "robot_chips": self.engine.robot_chips,
                "pot": self.engine.pot,
                "user_bet": self.engine.user_bet,
                "robot_bet": self.engine.robot_bet,
                "current_bet": self.engine.current_bet,
                "my_cards": self.engine.user_cards,
                "opponent_cards": self.engine.robot_cards if self.engine.show_robot_cards else [],
                "community_cards": self.engine.community_cards[:self.engine.revealed_community],
                "street": self.engine.street,
                "is_my_turn": self.engine.turn == "user" and not self.engine.hand_over,
                "hand_over": self.engine.hand_over,
                "winner": self.engine.winner,
                "i_won": self.engine.winner == "user" if self.engine.winner else None,
                "can_check": self.engine.can_check("user"),
                "call_amount": self.engine.call_amount("user"),
                "min_raise": self.engine.current_bet + BIG_BLIND,
                "can_raise": self.engine.can_raise("user"),
                "opponent_is_allin": self.engine.robot_chips == 0,
                "phase": "playing" if self.experiment.phase.startswith("hand") else self.experiment.phase,
                "last_action": self.engine.last_action,
                "last_action_by": self.engine.last_action_by,
                "opponent_thinking": self.ai.thinking,
                "show_opponent_cards": self.engine.show_robot_cards
            }

    def get_robot_state(self):
        with self._lock:
            return {
                "session_id": self.experiment.session_id,
                "hand_number": self.experiment.current_hand,
                "total_hands": 3,
                "user_chips": self.engine.robot_chips,
                "robot_chips": self.engine.user_chips,
                "pot": self.engine.pot,
                "user_bet": self.engine.robot_bet,
                "robot_bet": self.engine.user_bet,
                "current_bet": self.engine.current_bet,
                "my_cards": self.engine.robot_cards,
                "opponent_cards": self.engine.user_cards if self.engine.show_robot_cards else [],
                "community_cards": self.engine.community_cards[:self.engine.revealed_community],
                "street": self.engine.street,
                "is_my_turn": self.engine.turn == "robot" and not self.engine.hand_over,
                "hand_over": self.engine.hand_over,
                "winner": self.engine.winner,
                "i_won": self.engine.winner == "robot" if self.engine.winner else None,
                "can_check": self.engine.can_check("robot"),
                "call_amount": self.engine.call_amount("robot"),
                "min_raise": self.engine.current_bet + BIG_BLIND,
                "phase": "playing" if self.experiment.phase.startswith("hand") else self.experiment.phase,
                "last_action": self.engine.last_action,
                "last_action_by": ("opponent" if self.engine.last_action_by == "user" else ("me" if self.engine.last_action_by == "robot" else None)),
                "opponent_thinking": False,
                "show_opponent_cards": self.engine.show_robot_cards
            }

    def get_admin_state(self):
        with self._lock:
            hand = self.experiment.current_hand
            return {
                "session_id": self.experiment.session_id,
                "participant_id": self.experiment.participant_id,
                "phase": self.experiment.phase,
                "phase_name": {
                    "waiting": "In Attesa", "hand_1": "Mano 1 (Establishment)",
                    "hand_2": "Mano 2 (BLUFF)", "hand_3": "Mano 3 (BLUFF 2)",
                    "questionnaire": "Questionario", "end": "Fine"
                }.get(self.experiment.phase, self.experiment.phase),
                "current_hand": hand,
                "is_bluff_hand": hand in (2, 3),
                "street": self.engine.street,
                "user_chips": self.engine.user_chips,
                "robot_chips": self.engine.robot_chips,
                "pot": self.engine.pot,
                "user_bet": self.engine.user_bet,
                "robot_bet": self.engine.robot_bet,
                "current_bet": self.engine.current_bet,
                "user_cards": self.engine.user_cards,
                "robot_cards": self.engine.robot_cards,
                "community_cards": self.engine.community_cards,
                "revealed_community": self.engine.revealed_community,
                "turn": self.engine.turn,
                "hand_over": self.engine.hand_over,
                "winner": self.engine.winner,
                "last_action": self.engine.last_action,
                "last_action_by": self.engine.last_action_by,
                "robot_thinking": self.ai.thinking,
                "user_decision_on_bluff": self.experiment.user_decision_on_bluff,
                "user_actions": self.experiment.user_actions,
                # --- Nuovi dati ---
                "session_duration_s": self.experiment.get_session_duration_s(),
                "hand_duration_s": self.experiment.get_hand_duration_s(hand) if hand else None,
                "last_reaction_time_ms": self.experiment.get_last_reaction_time_ms(),
                "avg_reaction_time_ms": self.experiment.get_avg_reaction_time_ms(),
                "avg_reaction_hand_ms": self.experiment.get_avg_reaction_time_ms(hand) if hand else None,
                "action_count": self.experiment.action_count,
                "robot_mode": self.experiment.robot_mode
            }

    # =========================================================================
    # AZIONI PLAYER
    # =========================================================================
    def handle_player_action(self, action, amount=0):
        with self._lock:
            try:
                amount = int(amount)
            except (ValueError, TypeError):
                amount = 0
            
            action = action.lower()
            if self.engine.turn != "user" or self.engine.hand_over:
                return {"success": False, "error": "Non e' il tuo turno"}

            # Registra tempo di reazione prima di processare l'azione
            reaction_ms = self.experiment.record_reaction_time(self.engine.street)

            # Log azione dettagliata
            action_label = action if action != "raise" else "raise {}".format(amount)
            log_action(
                self.experiment.session_id,
                self.experiment.current_hand,
                self.engine.street,
                "user",
                action_label,
                reaction_ms
            )

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
        self.engine.hand_over = True
        self.engine.winner = "robot"
        self.engine.robot_chips += self.engine.pot
        self.engine.pot = 0
        self.engine.last_action = "fold"
        self.engine.last_action_by = "user"
        self.engine.show_robot_cards = True
        
        self.experiment.log_action("fold")
        if self.experiment.current_hand in (2, 3):
            self.experiment.set_bluff_decision("fold")

            self.trigger_robot("bluff_success")
        else:
            self.trigger_robot("react_user_fold")
        
        # Log risultato mano (tutte le mani)
        self._log_hand_result()
        return {"success": True, "action": "fold"}

    def _player_check(self):
        if not self.engine.can_check("user"):
            return {"success": False, "error": "Non puoi fare check"}
        
        self.engine.last_action = "check"
        self.engine.last_action_by = "user"
        self.experiment.log_action("check")
        self.engine.turn = "robot"
        self.trigger_robot("react_user_check")
        self.ai.make_decision()
        # Dopo la decisione del robot, se il turno torna all'utente, registra
        if self.engine.turn == "user" and not self.engine.hand_over:
            self.experiment.start_user_turn()
        return {"success": True, "action": "check"}

    def _player_call(self):
        call_amount = self.engine.call_amount("user")
        if call_amount <= 0: return {"success": False, "error": "Niente da chiamare"}
        
        actual_call = min(call_amount, self.engine.user_chips)
        self.engine.user_chips -= actual_call
        self.engine.user_bet += actual_call
        self.engine.pot += actual_call
        
        if actual_call < call_amount:
            uncalled_chips = call_amount - actual_call
            self.engine.robot_chips += uncalled_chips
            self.engine.robot_bet -= uncalled_chips
            self.engine.pot -= uncalled_chips
            self.engine.current_bet = self.engine.robot_bet
        
        self.engine.last_action = "call {}".format(actual_call)
        self.engine.last_action_by = "user"
        self.experiment.log_action("call")

        # Bug #5 fix: reazione robot call su tutti gli street (non solo flop/turn)
        if self.engine.robot_chips > 0 and self.engine.user_chips > 0:
            self.trigger_robot("react_user_call")

        if self.engine.robot_chips == 0 or self.engine.user_chips == 0:
            self._do_showdown()
        elif self.engine.street == self.engine.STREET_PREFLOP and self.engine.current_bet == BIG_BLIND:
            self.engine.turn = "robot"
            self.ai.make_decision()
        elif self.engine.street == self.engine.STREET_RIVER and self.engine.user_bet == self.engine.robot_bet:
            self._do_showdown()
        elif self.engine.user_bet == self.engine.robot_bet:
            self._check_advance_street()
        else:
            self.engine.turn = "robot"
            self.ai.make_decision()

        # Se il turno torna all'utente, registra inizio turno
        if self.engine.turn == "user" and not self.engine.hand_over:
            self.experiment.start_user_turn()

        return {"success": True, "action": "call", "amount": actual_call}

    def _player_raise(self, amount):
        if not self.engine.can_raise("user"):
            return {"success": False, "error": "Non puoi rilanciare."}
        
        min_raise = self.engine.current_bet + BIG_BLIND
        if amount < min_raise: return {"success": False, "error": "Rilancio minimo: {}".format(min_raise)}

        actual_raise = min(amount, self.engine.user_chips + self.engine.user_bet)
        chips_needed = actual_raise - self.engine.user_bet
        
        self.engine.user_chips -= chips_needed
        self.engine.pot += chips_needed
        self.engine.user_bet = actual_raise
        self.engine.current_bet = max(self.engine.current_bet, actual_raise)
        
        self.engine.last_action = "raise {}".format(actual_raise)
        self.engine.last_action_by = "user"
        self.experiment.log_action("raise {}".format(actual_raise))
        self.engine.turn = "robot"
        
        self.trigger_robot("react_user_raise")
        self.ai.make_decision()
        
        # Se il turno torna all'utente, registra inizio turno
        if self.engine.turn == "user" and not self.engine.hand_over:
            self.experiment.start_user_turn()
        
        return {"success": True, "action": "raise", "amount": actual_raise}

    def _player_allin(self):
        allin_amount = self.engine.user_chips
        self.engine.user_chips = 0
        self.engine.pot += allin_amount
        new_total = self.engine.user_bet + allin_amount
        
        self.engine.current_bet = max(self.engine.current_bet, new_total)
        self.engine.user_bet = new_total
        
        self.engine.last_action = "ALL-IN {}".format(allin_amount)
        self.engine.last_action_by = "user"
        self.experiment.log_action("allin")
        
        if self.experiment.current_hand in (2, 3):
            self.experiment.set_bluff_decision("allin")
            
        self.trigger_robot("react_user_allin")

        if self.engine.robot_chips == 0 or self.engine.user_bet <= self.engine.robot_bet:
            if self.engine.user_bet < self.engine.robot_bet:
                uncalled_chips = self.engine.robot_bet - self.engine.user_bet
                self.engine.robot_chips += uncalled_chips
                self.engine.robot_bet -= uncalled_chips
                self.engine.pot -= uncalled_chips
                self.engine.current_bet = self.engine.user_bet
            self._do_showdown()
        else:
            self.engine.turn = "robot"
            self.ai.make_decision()
        
        # Se il turno torna all'utente, registra inizio turno
        if self.engine.turn == "user" and not self.engine.hand_over:
            self.experiment.start_user_turn()
            
        return {"success": True, "action": "allin", "amount": allin_amount}

    # =========================================================================
    # AZIONI ADMIN & LOGGING
    # =========================================================================
    def handle_admin_action(self, action, data):
        with self._lock:
            action = action.lower()
            if action == "start_experiment":
                self.reset()
                self.experiment.participant_id = data.get("participant_id", "")
                self.trigger_robot("intro")
                return {"success": True, "message": "Esperimento iniziato"}
            elif action == "start_hand":
                hand_num = data.get("hand_number", self.experiment.current_hand + 1)
                self.start_hand(hand_num)
                self._announce_hand_start(hand_num)
                return {"success": True, "message": "Mano iniziata"}
            elif action == "next_hand":
                next_hand = self.experiment.current_hand + 1
                if next_hand > 3:
                    self.experiment.phase = self.experiment.PHASE_QUESTIONNAIRE
                    return {"success": True, "message": "Questionario"}
                self.start_hand(next_hand)
                self._announce_hand_start(next_hand)
                return {"success": True, "message": "Mano iniziata"}
            elif action == "show_questionnaire":
                self.experiment.phase = self.experiment.PHASE_QUESTIONNAIRE
                return {"success": True}
            elif action == "reset":
                self.reset()
                return {"success": True, "message": "Reset"}
            elif action == "trigger_robot":
                self.trigger_robot(data.get("behavior", ""))
                return {"success": True}
            return {"success": False, "error": "Azione non valida"}

    def handle_questionnaire(self, questionnaire_data):
        with self._lock:
            self._log_experiment_result()
            self.experiment.phase = self.experiment.PHASE_END
            return {"success": True}

    def _announce_hand_start(self, hand_num):
        if hand_num == 1: self.trigger_robot("hand_start_1")
        elif hand_num == 2: self.trigger_robot("hand_start_2")
        elif hand_num == 3: self.trigger_robot("hand_start_3")

    def _log_experiment_result(self):
        log_experiment_result(
            self.experiment.session_id,
            self.experiment.participant_id,
            self.experiment.winners,
            session_duration_s=self.experiment.get_session_duration_s()
        )

    def _log_hand_result(self):
        """Log il risultato della mano corrente (tutte le mani, non solo bluff)."""
        hand = self.experiment.current_hand
        self.experiment.winners[hand] = self.engine.winner or "unknown"
        self.experiment.end_hand()
        hand_types = {1: "establishment", 2: "bluff", 3: "bluff_2"}
        log_hand_result(
            session_id=self.experiment.session_id,
            participant_id=self.experiment.participant_id,
            hand_number=hand,
            hand_type=hand_types.get(hand, "unknown"),
            winner=self.engine.winner or "unknown",
            user_chips=self.engine.user_chips,
            robot_chips=self.engine.robot_chips,
            hand_duration_s=self.experiment.get_hand_duration_s(hand),
            action_count=self.experiment.action_count.get(hand, 0),
            avg_reaction_time_ms=self.experiment.get_avg_reaction_time_ms(hand),
            robot_mode=self.experiment.robot_mode
        )

    def _log_robot_action(self, action):
        """Log un'azione del robot nel log dettagliato."""
        log_action(
            self.experiment.session_id,
            self.experiment.current_hand,
            self.engine.street,
            "robot",
            action
        )

    # =========================================================================
    # AZIONI ROBOT (MUTAZIONI) E GESTIONE STREET
    # =========================================================================
    def _do_robot_check(self):
        self.engine.last_action = "check"
        self.engine.last_action_by = "robot"
        self._log_robot_action("check")
        self.trigger_robot("robot_check")
        self.engine.turn = "user"
        self.experiment.start_user_turn()
        
    def _do_robot_call(self):
        call_amount = self.engine.call_amount("robot")
        actual_call = min(call_amount, self.engine.robot_chips)
        self.engine.robot_chips -= actual_call
        self.engine.robot_bet += actual_call
        self.engine.pot += actual_call
        
        if actual_call < call_amount:
            uncalled_chips = call_amount - actual_call
            self.engine.user_chips += uncalled_chips
            self.engine.user_bet -= uncalled_chips
            self.engine.pot -= uncalled_chips
            self.engine.current_bet = self.engine.user_bet

        if self.engine.robot_chips == 0:
            self.engine.last_action = "ALL-IN (call {})".format(actual_call)
            self._log_robot_action("allin_call {}".format(actual_call))
            self.trigger_robot("robot_call_allin")
        else:
            self.engine.last_action = "call {}".format(actual_call)
            self._log_robot_action("call {}".format(actual_call))
            self.trigger_robot("robot_call")
        self.engine.last_action_by = "robot"
        self.engine.turn = "user"
        self.experiment.start_user_turn()

    def _do_robot_raise(self, amount, robot_action=None):
        total_bet = self.engine.current_bet + amount
        actual_chips = min(total_bet - self.engine.robot_bet, self.engine.robot_chips)
        self.engine.robot_chips -= actual_chips
        self.engine.pot += actual_chips
        self.engine.robot_bet += actual_chips
        self.engine.current_bet = max(self.engine.current_bet, self.engine.robot_bet)
        
        # Bug #6 fix: se il robot finisce a 0 chips, annuncia all-in
        if self.engine.robot_chips == 0:
            self.engine.last_action = "ALL-IN {}".format(self.engine.robot_bet)
            self.engine.last_action_by = "robot"
            self._log_robot_action("allin {}".format(self.engine.robot_bet))
            if robot_action: self.trigger_robot(robot_action)
            else: self.trigger_robot("robot_allin")
        else:
            self.engine.last_action = "raise {}".format(self.engine.robot_bet)
            self.engine.last_action_by = "robot"
            self._log_robot_action("raise {}".format(self.engine.robot_bet))
            if robot_action: self.trigger_robot(robot_action)
            elif self.experiment.current_hand in (2, 3): self.trigger_robot("robot_raise_bluff")
            else: self.trigger_robot("robot_raise")
        self.engine.turn = "user"
        self.experiment.start_user_turn()

    def _do_robot_allin(self, announce_action="robot_allin"):
        # Bug #11 fix: aggiorna stato PRIMA di triggerare il robot
        allin_amount = self.engine.robot_chips
        self.engine.robot_chips = 0
        self.engine.pot += allin_amount
        self.engine.robot_bet += allin_amount
        self.engine.current_bet = max(self.engine.current_bet, self.engine.robot_bet)
        
        self.engine.last_action = "ALL-IN {}".format(allin_amount)
        self.engine.last_action_by = "robot"
        self._log_robot_action("allin {}".format(allin_amount))
        self.engine.turn = "user"
        self.experiment.start_user_turn()
        if announce_action: self.trigger_robot(announce_action)

    def _do_robot_fold(self):
        self._log_robot_action("fold")
        self.trigger_robot("robot_fold")
        self.engine.hand_over = True
        self.engine.winner = "user"
        self.engine.user_chips += self.engine.pot
        self.engine.pot = 0
        self.engine.last_action = "fold"
        self.engine.last_action_by = "robot"
        self.engine.show_robot_cards = True
        
        if self.experiment.current_hand in (2, 3):
            pass
            
        # Log risultato mano (tutte le mani)
        self._log_hand_result()

    def _check_advance_street(self):
        if self.engine.hand_over: return
        if self.engine.user_bet == self.engine.robot_bet:
            if self.engine.user_chips == 0 or self.engine.robot_chips == 0:
                self._do_showdown()
            elif not self.engine.advance_street():
                self._do_showdown()
            else:
                self._check_announce_street()

    def _check_announce_street(self):
        street = self.engine.street
        hand = self.experiment.current_hand
        if street != self._last_street_announced and hand not in (2, 3):
            if street == self.engine.STREET_FLOP:
                self._last_street_announced = street
                self.trigger_robot("new_flop")
            elif street == self.engine.STREET_TURN:
                self._last_street_announced = street
                self.trigger_robot("new_turn")
            elif street == self.engine.STREET_RIVER:
                self._last_street_announced = street
                self.trigger_robot("new_river")

    def _do_showdown(self):
        self.engine.street = self.engine.STREET_SHOWDOWN
        self.engine.revealed_community = 5
        self.engine.show_robot_cards = True
        self.engine.hand_over = True
        
        hand_data = self.experiment.hands.get(self.experiment.current_hand, {})
        self.engine.winner = "robot" if hand_data.get("robot_wins", False) else "user"
        
        if self.engine.winner == "user":
            self.engine.user_chips += self.engine.pot
            if self.experiment.current_hand in (2, 3): self.trigger_robot("bluff_failed")
            else: self.trigger_robot("defeat")
        else:
            self.engine.robot_chips += self.engine.pot
            self.trigger_robot("win_claim")
            
        self.engine.pot = 0
        # Bug #15 fix: registra decisione bluff allo showdown (utente non ha foldato)
        if self.experiment.current_hand in (2, 3):
            if not self.experiment.user_decision_on_bluff:
                self.experiment.set_bluff_decision("call")
        

        # Log risultato mano (tutte le mani)
        self._log_hand_result()
