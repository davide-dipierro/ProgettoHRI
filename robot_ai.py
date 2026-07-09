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
        self.game = game_state
        self.thinking = False

    def make_decision(self):
        """Avvia il processo decisionale del robot in un thread separato."""
        if self.game.engine.turn != "robot" or self.game.engine.hand_over:
            return

        self.thinking = True
        self.game.trigger_robot("thinking")
        think_time = random.uniform(ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX)

        def _worker():
            try:
                time.sleep(think_time)

                # --- Fase 1: decisione con lock ---
                needs_bluff_allin = False
                with self.game._lock:
                    if self.game.engine.turn != "robot" or self.game.engine.hand_over:
                        return
                    needs_bluff_allin = self._execute_decision()

                # --- Fase 2: bluff all-in FUORI dal lock ---
                if needs_bluff_allin:
                    self._do_bluff_then_allin()

            except Exception as e:
                print("[ROBOT AI] ERRORE: {}".format(e))
            finally:
                self.thinking = False

        thread = threading.Thread(target=_worker)
        thread.daemon = True
        thread.start()

    # =========================================================================
    # DECISIONE PRINCIPALE
    # =========================================================================
    def _execute_decision(self):
        """Esegue la decisione del robot. Ritorna True se serve il bluff all-in.
        
        DEVE essere chiamato con self.game._lock acquisito.
        """
        hand = self.game.experiment.current_hand
        street = self.game.engine.street
        call_amount = self.game.engine.call_amount("robot")
        user_is_allin = self.game.engine.user_chips == 0

        print("[ROBOT AI] Mano {}, Street {}, Bet: {}, Robot bet: {}, User all-in: {}".format(
            hand, street, self.game.engine.current_bet, self.game.engine.robot_bet, user_is_allin))

        if hand == 1:
            self._ai_hand_1(call_amount, user_is_allin, street)
            return False
        elif hand in (2, 3):
            return self._ai_hand_bluff(call_amount, user_is_allin, street)
        else:
            # Fallback: check o call
            if call_amount > 0:
                self.game._do_robot_call()
                self.game._check_advance_street()
            else:
                self.game._do_robot_check()
                self.game._check_advance_street()
            return False

    # =========================================================================
    # MANO 1: ESTABLISHMENT (gioco conservativo)
    # =========================================================================
    def _ai_hand_1(self, call_amount, user_is_allin, street):
        """Mano 1: il robot gioca in modo conservativo."""
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

    # =========================================================================
    # MANO 2/3: BLUFF (gioco aggressivo)
    # =========================================================================
    def _ai_hand_bluff(self, call_amount, user_is_allin, street):
        """Mano di bluff: il robot gioca in modo aggressivo.
        
        Ritorna True se al river serve il comportamento bluff + all-in ritardato.
        """
        E = self.game.engine

        # --- L'utente è andato all-in: il robot lo segue sempre ---
        if user_is_allin and call_amount > 0:
            self.game._do_robot_call()
            self.game._do_showdown()
            return False

        # --- Il robot deve rispondere a una puntata (call_amount > 0) ---
        if call_amount > 0:
            if street == E.STREET_PREFLOP:
                reraise = max(BIG_BLIND * 2, E.robot_chips // 10)
                self.game._do_robot_raise(reraise, "robot_raise_bluff")
            elif street == E.STREET_FLOP:
                reraise = max(BIG_BLIND * 2, E.robot_chips // 7)
                self.game._do_robot_raise(reraise, "robot_raise_bluff_1")
            elif street == E.STREET_TURN:
                reraise = max(BIG_BLIND * 3, E.robot_chips // 4)
                self.game._do_robot_raise(reraise, "robot_raise_bluff_2")
            elif street == E.STREET_RIVER:
                return True  # → bluff + all-in ritardato
            else:
                self.game._do_robot_call()
                self.game._check_advance_street()
            return False

        # --- Nessuna puntata da coprire: il robot apre aggressivamente ---
        if street == E.STREET_PREFLOP:
            self.game._do_robot_check()
            self.game._check_advance_street()
        elif street == E.STREET_FLOP:
            bet_amount = max(BIG_BLIND * 2, E.robot_chips // 7)
            self.game._do_robot_raise(bet_amount, "robot_raise_bluff_1")
        elif street == E.STREET_TURN:
            bet_amount = max(BIG_BLIND * 3, E.robot_chips // 4)
            self.game._do_robot_raise(bet_amount, "robot_raise_bluff_2")
        elif street == E.STREET_RIVER:
            return True  # → bluff + all-in ritardato
        else:
            self.game._do_robot_check()
            self.game._check_advance_street()
        return False

    # =========================================================================
    # BLUFF ALL-IN RITARDATO (eseguito FUORI dal lock)
    # =========================================================================
    def _do_bluff_then_allin(self):
        """Il robot fa il discorso intimidatorio, poi va all-in.
        
        Questo metodo viene chiamato FUORI dal lock per evitare deadlock.
        Il trigger_robot("bluff") avvia l'animazione del robot (che dura ~9s).
        Dopo l'attesa, riacquisiamo il lock per eseguire l'all-in.
        """
        # Trigger il comportamento di bluff (discorso intimidatorio)
        self.game.trigger_robot("bluff")

        # Attendi che il robot finisca di parlare
        time.sleep(9)

        # Riacquisisci il lock per eseguire l'all-in
        try:
            with self.game._lock:
                if not self.game.engine.hand_over and self.game.engine.turn == "robot":
                    self.game._do_robot_allin(announce_action=None)
        except Exception as e:
            print("[ROBOT AI] ERRORE in bluff all-in: {}".format(e))
