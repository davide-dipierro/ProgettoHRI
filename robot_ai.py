#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Robot AI per l'esperimento HRI Poker.
Determina le azioni del robot per ciascuna mano pre-programmata (bluff etc.).
"""

import threading
import time
import random
from config import BIG_BLIND, ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX

class RobotAI:
    def __init__(self, game_state):
        # game_state è l'istanza della classe principale Facade
        self.game = game_state
        self.thinking = False

    def make_decision(self):
        if self.game.engine.turn != "robot" or self.game.engine.hand_over:
            return

        self.thinking = True
        self.game.trigger_robot("thinking")
        think_time = random.uniform(ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX)

        def delayed_action():
            time.sleep(think_time)
            # Acquisisce il lock dello stato di gioco per evitare race condition
            with self.game._lock:
                if self.game.engine.turn != "robot" or self.game.engine.hand_over:
                    self.thinking = False
                    return
                self._execute_decision()
            self.thinking = False

        thread = threading.Thread(target=delayed_action)
        thread.daemon = True
        thread.start()

    def _execute_decision(self):
        hand = self.game.experiment.current_hand
        street = self.game.engine.street
        call_amount = self.game.engine.call_amount("robot")
        user_is_allin = self.game.engine.user_chips == 0

        print("[ROBOT AI] Mano {}, Street {}, Bet: {}, Robot bet: {}, User all-in: {}".format(
            hand, street, self.game.engine.current_bet, self.game.engine.robot_bet, user_is_allin))



        if hand == 1:
            self._ai_hand_1(call_amount, user_is_allin, street)
        elif hand == 2:
            self._ai_hand_2(call_amount, user_is_allin, street)
        elif hand == 3:
            self._ai_hand_3(call_amount, user_is_allin, street)

    def _ai_hand_1(self, call_amount, user_is_allin, street):
        if user_is_allin and call_amount > 0:
            self.game._do_robot_fold()
        elif call_amount > 0:
            if call_amount > self.game.engine.robot_chips * 0.5:
                self.game._do_robot_fold()
                return
            self.game._do_robot_call()
            self.game._check_advance_street()
        elif street == self.game.engine.STREET_PREFLOP and self.game.engine.robot_bet == BIG_BLIND:
            self.game._do_robot_raise(BIG_BLIND)
        elif street == self.game.engine.STREET_RIVER:
            self.game._do_robot_raise(30)
        else:
            self.game._do_robot_check()
            self.game._check_advance_street()

    def _ai_hand_2(self, call_amount, user_is_allin, street):
        if user_is_allin and call_amount > 0:
            if street != self.game.engine.STREET_RIVER:
                # Se l'utente va all-in prematuramente, folda per non rovinare l'esperimento
                self.game._do_robot_fold()
                return
            self.game._do_robot_call()
            self.game._do_showdown()
        elif call_amount > 0:
            if street == self.game.engine.STREET_PREFLOP:
                # Bug #7 fix: al preflop il robot re-rilancia aggressivamente
                reraise = max(BIG_BLIND * 2, self.game.engine.robot_chips // 10)
                self.game._do_robot_raise(reraise, "robot_raise_bluff")
            elif street == self.game.engine.STREET_FLOP:
                reraise = max(BIG_BLIND * 2, self.game.engine.robot_chips // 7)
                self.game._do_robot_raise(reraise, "robot_raise_bluff_1")
            elif street == self.game.engine.STREET_TURN:
                reraise = max(BIG_BLIND * 3, self.game.engine.robot_chips // 4)
                self.game._do_robot_raise(reraise, "robot_raise_bluff_2")
            elif street == self.game.engine.STREET_RIVER:
                self.game.trigger_robot("bluff")
                def _delayed_allin():
                    time.sleep(9)
                    with self.game._lock:
                        if not self.game.engine.hand_over:
                            self.game._do_robot_allin(announce_action=None)
                threading.Thread(target=_delayed_allin).start()
            else:
                self.game._do_robot_call()
                self.game._check_advance_street()
        elif street == self.game.engine.STREET_PREFLOP:
            self.game._do_robot_check()
            self.game._check_advance_street()
        elif street == self.game.engine.STREET_FLOP:
            bet_amount = max(BIG_BLIND * 2, self.game.engine.robot_chips // 7)
            self.game._do_robot_raise(bet_amount, "robot_raise_bluff_1")
        elif street == self.game.engine.STREET_TURN:
            bet_amount = max(BIG_BLIND * 3, self.game.engine.robot_chips // 4)
            self.game._do_robot_raise(bet_amount, "robot_raise_bluff_2")
        elif street == self.game.engine.STREET_RIVER:
                self.game.trigger_robot("bluff")
                def _delayed_allin():
                    time.sleep(9)
                    with self.game._lock:
                        if not self.game.engine.hand_over:
                            self.game._do_robot_allin(announce_action=None)
                threading.Thread(target=_delayed_allin).start()
        else:
            self.game._do_robot_check()
            self.game._check_advance_street()

    def _ai_hand_3(self, call_amount, user_is_allin, street):
        if street == self.game.engine.STREET_PREFLOP and self.game.engine.robot_bet == BIG_BLIND:
            self.game.trigger_robot("cooldown")

        if user_is_allin and call_amount > 0:
            if call_amount > self.game.engine.robot_chips // 2:
                self.game._do_robot_fold()
            else:
                self.game._do_robot_call()
                self.game._do_showdown()
            return
        elif call_amount > 0:
            if call_amount > self.game.engine.robot_chips // 2:
                self.game._do_robot_fold()
            else:
                self.game._do_robot_call()
                self.game._check_advance_street()
        else:
            self.game._do_robot_check()
            self.game._check_advance_street()
