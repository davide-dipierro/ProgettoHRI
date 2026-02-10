#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Server (Brain) - HRI Poker Experiment
Università degli Studi - Esperimento Overtrust

Tre interfacce:
- /player -> Interfaccia utente (davanti all'utente)
- /robot  -> Interfaccia robot (davanti al robot, identica a player)
- /admin  -> Interfaccia amministratore (monitora tutto)

Il robot prende decisioni AUTOMATICHE basate sulla strategia predefinita.
Le fasi (Establishment, Bluff, Cooldown) sono invisibili all'utente.
"""

import os
import csv
import time
import threading
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# =============================================================================
# CONFIGURAZIONE
# =============================================================================

ROBOT_IP = os.environ.get("NAO_IP", "127.0.0.1")
ROBOT_PORT = int(os.environ.get("NAO_PORT", "9559"))
PYTHON_PATH = os.environ.get("PYTHON_PATH", "python3")
ROBOT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot_controller.py")
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "true").lower() == "true"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DATA_FILE = os.path.join(DATA_DIR, "experiment_results.csv")
QUESTIONNAIRE_FILE = os.path.join(DATA_DIR, "questionnaire_results.csv")

# Configurazione chip
STARTING_CHIPS = 1000
SMALL_BLIND = 10
BIG_BLIND = 20

# Tempo di "pensata" del robot (secondi)
# Il robot parla durante le azioni quindi non serve aspettare molto
ROBOT_THINK_TIME_MIN = 1
ROBOT_THINK_TIME_MAX = 2

# =============================================================================
# STATO DEL GIOCO
# =============================================================================

class GameState:
    """Gestisce lo stato completo del gioco."""
    
    PHASE_WAITING = "waiting"
    PHASE_HAND_1 = "hand_1"
    PHASE_HAND_2 = "hand_2"
    PHASE_HAND_3 = "hand_3"
    PHASE_QUESTIONNAIRE = "questionnaire"
    PHASE_END = "end"
    
    STREET_PREFLOP = "preflop"
    STREET_FLOP = "flop"
    STREET_TURN = "turn"
    STREET_RIVER = "river"
    STREET_SHOWDOWN = "showdown"
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset completo."""
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
        self.last_action = None  # Ultima azione (per visualizzazione)
        self.last_action_by = None
        
        self.user_cards = []
        self.robot_cards = []
        self.community_cards = []
        self.revealed_community = 0
        self.show_robot_cards = False  # Mostra carte robot (solo showdown)
        
        # Dati esperimento
        self.bluff_start_time = None
        self.reaction_time_ms = None
        self.user_decision_on_bluff = None
        
        # Robot thinking
        self.robot_thinking = False
        
        self._setup_rigged_hands()
    
    def _setup_rigged_hands(self):
        """Mani predeterminate."""
        self.hands = {
            1: {  # Establishment: Utente vince - costruisce fiducia
                # Utente ha coppia di 10, robot ha A-K (sembra forte ma perde)
                "user": ["10_of_hearts", "10_of_diamonds"],
                "robot": ["ace_of_spades", "king_of_hearts"],
                "community": ["7_of_clubs", "3_of_spades", "jack_of_diamonds", "2_of_hearts", "5_of_clubs"],
                "robot_wins": False
            },
            2: {  # BLUFF: Utente ha mano fortissima, robot bluffa
                "user": ["king_of_spades", "king_of_diamonds"],
                "robot": ["3_of_clubs", "5_of_hearts"],
                "community": ["king_of_clubs", "9_of_hearts", "4_of_diamonds", "2_of_spades", "8_of_clubs"],
                "robot_wins": False
            },
            3: {  # Cooldown: Utente vince
                "user": ["queen_of_hearts", "queen_of_clubs"],
                "robot": ["jack_of_hearts", "10_of_diamonds"],
                "community": ["queen_of_spades", "5_of_clubs", "3_of_hearts", "7_of_clubs", "2_of_hearts"],
                "robot_wins": False
            }
        }
    
    def start_hand(self, hand_number):
        """Inizia una nuova mano."""
        self.current_hand = hand_number
        self.phase = f"hand_{hand_number}"
        
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
        
        self._post_blinds()
    
    def _post_blinds(self):
        """Posta i blind."""
        sb = min(SMALL_BLIND, self.user_chips)
        bb = min(BIG_BLIND, self.robot_chips)
        
        self.user_chips -= sb
        self.user_bet = sb
        self.robot_chips -= bb
        self.robot_bet = bb
        
        self.pot = sb + bb
        self.current_bet = bb
        self.turn = "user"
    
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
            "can_raise": self.robot_chips > 0,  # Non può rilanciare se robot è all-in
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
            "user_chips": self.robot_chips,  # Invertito
            "robot_chips": self.user_chips,  # Invertito
            "pot": self.pot,
            "user_bet": self.robot_bet,  # Invertito
            "robot_bet": self.user_bet,  # Invertito
            "current_bet": self.current_bet,
            "my_cards": self.robot_cards,  # Mostra carte robot
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
            "last_action_by": "opponent" if self.last_action_by == "user" else ("me" if self.last_action_by == "robot" else None),
            "opponent_thinking": False,  # Robot non vede se stesso pensare
            "show_opponent_cards": self.show_robot_cards
        }
    
    def get_admin_state(self):
        """Stato completo per admin."""
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
            "bluff_start_time": self.bluff_start_time,
            "reaction_time_ms": self.reaction_time_ms,
            "user_decision_on_bluff": self.user_decision_on_bluff
        }


game = GameState()


# =============================================================================
# CONTROLLO ROBOT FISICO
# =============================================================================

def trigger_robot(action):
    """Invia comando al robot fisico."""
    try:
        cmd = [PYTHON_PATH, ROBOT_SCRIPT, "--action", action]
        if SIMULATION_MODE:
            cmd.append("--simulate")
        else:
            cmd.extend(["--ip", ROBOT_IP, "--port", str(ROBOT_PORT)])
        
        print(f"[ROBOT] Eseguo: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"[ROBOT] Azione '{action}' completata")
            return True
        return False
    except Exception as e:
        print(f"[ROBOT] Eccezione: {e}")
        return False


# =============================================================================
# ROBOT AI - DECISIONI AUTOMATICHE
# =============================================================================

def robot_make_decision():
    """
    Il robot prende una decisione basata sulla strategia predefinita.
    
    Strategia per mano:
    - Mano 1: Gioca passivo e perde.
    - Mano 2: ALL-IN (bluff!) al river
    - Mano 3: Gioca passivo, folda o chiama
    """
    if game.turn != "robot" or game.hand_over:
        return
    
    game.robot_thinking = True
    
    # Simula tempo di pensata
    import random
    think_time = random.uniform(ROBOT_THINK_TIME_MIN, ROBOT_THINK_TIME_MAX)
    
    def delayed_action():
        time.sleep(think_time)
        execute_robot_decision()
        game.robot_thinking = False
    
    thread = threading.Thread(target=delayed_action)
    thread.daemon = True
    thread.start()


def execute_robot_decision():
    """Esegue la decisione del robot."""
    hand = game.current_hand
    street = game.street
    call_amount = game.current_bet - game.robot_bet
    user_is_allin = game.user_chips == 0
    
    print(f"[ROBOT AI] Mano {hand}, Street {street}, Bet corrente: {game.current_bet}, Robot bet: {game.robot_bet}, User all-in: {user_is_allin}")
    
    # =========================================================================
    # MANO 1 - ESTABLISHMENT (Robot ha A-K, gioca aggressivo ma perde)
    # Utente vince per costruire fiducia. Robot gioca in modo credibile.
    # =========================================================================
    if hand == 1:
        if user_is_allin and call_amount > 0:
            # Utente è all-in: A-K non è abbastanza forte, robot folda
            do_robot_fold()
            return
        elif call_amount > 0:
            # Se l'utente rilancia molto (più del 50% delle chips), folda
            if call_amount > game.robot_chips * 0.5:
                do_robot_fold()
                return
            # Altrimenti chiama (A-K è una buona mano)
            do_robot_call()
            check_advance_street()
        elif street == game.STREET_PREFLOP and game.robot_bet == BIG_BLIND:
            # Preflop con A-K: rilancia leggermente per mostrare forza (solo se non ha già rilanciato)
            do_robot_raise(BIG_BLIND)
        elif street == game.STREET_RIVER:
            # Al river senza aver fatto coppia, fa un piccolo bluff
            do_robot_raise(30)
        else:
            # Flop/Turn o preflop dopo rilancio: check e avanza
            do_robot_check()
            check_advance_street()
    
    # =========================================================================
    # MANO 2 - BLUFF (Robot costruisce il pot gradualmente, poi ALL-IN al river)
    # Il robot deve sembrare sicuro per ingannare l'utente
    # =========================================================================
    elif hand == 2:
        if user_is_allin and call_amount > 0:
            # Utente è già all-in, robot chiama
            do_robot_call()
            do_showdown()
            return
        elif call_amount > 0:
            # Utente ha rilanciato, robot chiama (sembra sicuro)
            do_robot_call()
            check_advance_street()
        elif street == game.STREET_PREFLOP and game.robot_bet == BIG_BLIND:
            # Preflop: piccolo rilancio per costruire il pot
            do_robot_raise(BIG_BLIND)
        elif street == game.STREET_FLOP:
            # Flop: continuation bet moderato (~30% pot)
            bet_amount = max(30, game.pot // 3)
            do_robot_raise(bet_amount)
        elif street == game.STREET_TURN:
            # Turn: aumenta la pressione (~50% pot)
            bet_amount = max(50, game.pot // 2)
            do_robot_raise(bet_amount)
        elif street == game.STREET_RIVER:
            # River: BLUFF ALL-IN!
            trigger_robot("bluff")
            do_robot_allin()
            game.bluff_start_time = time.time() * 1000
        else:
            do_robot_check()
            check_advance_street()
    
    # =========================================================================
    # MANO 3 - COOLDOWN (Robot gioca passivo)
    # =========================================================================
    elif hand == 3:
        # Comportamento cooldown alla prima azione
        if street == game.STREET_PREFLOP and game.robot_bet == BIG_BLIND:
            trigger_robot("cooldown")
        
        if user_is_allin and call_amount > 0:
            # Utente all-in: robot decide se chiamare
            if call_amount > game.robot_chips // 2:
                do_robot_fold()
            else:
                do_robot_call()
                do_showdown()
            return
        elif call_amount > 0:
            if call_amount > game.robot_chips // 2:
                # Troppo da chiamare, folda
                do_robot_fold()
            else:
                do_robot_call()
                check_advance_street()
        else:
            do_robot_check()
            check_advance_street()


def check_advance_street():
    """Controlla se entrambi hanno agito e avanza la street."""
    if game.hand_over:
        return
    
    # Se le puntate sono pareggiate, avanza alla prossima street
    if game.user_bet == game.robot_bet:
        # Se qualcuno è all-in, vai direttamente a showdown
        if game.user_chips == 0 or game.robot_chips == 0:
            do_showdown()
        else:
            advance_to_next_street()


def advance_to_next_street():
    """Avanza alla prossima street."""
    streets = [game.STREET_PREFLOP, game.STREET_FLOP, game.STREET_TURN, game.STREET_RIVER]
    
    if game.street not in streets:
        return
    
    current_idx = streets.index(game.street)
    
    if current_idx < len(streets) - 1:
        game.street = streets[current_idx + 1]
        game.user_bet = 0
        game.robot_bet = 0
        game.current_bet = 0
        game.turn = "user"
        
        if game.street == game.STREET_FLOP:
            game.revealed_community = 3
        elif game.street == game.STREET_TURN:
            game.revealed_community = 4
        elif game.street == game.STREET_RIVER:
            game.revealed_community = 5
        
        print(f"[GAME] Avanzato a {game.street}, rivelate {game.revealed_community} carte")
    else:
        # Showdown
        do_showdown()


def do_robot_check():
    """Robot fa check."""
    game.last_action = "check"
    game.last_action_by = "robot"
    game.turn = "user"
    
    # Il robot annuncia il check
    trigger_robot("robot_check")
    print("[ROBOT AI] Check")


def do_robot_call():
    """Robot chiama."""
    call_amount = game.current_bet - game.robot_bet
    actual_call = min(call_amount, game.robot_chips)
    
    game.robot_chips -= actual_call
    game.robot_bet += actual_call
    game.pot += actual_call
    
    # Se il robot ha messo tutto, è all-in
    if game.robot_chips == 0:
        game.last_action = f"ALL-IN (call {actual_call})"
        trigger_robot("robot_call_allin")
    else:
        game.last_action = f"call {actual_call}"
        trigger_robot("robot_call")
    game.last_action_by = "robot"
    game.turn = "user"
    print(f"[ROBOT AI] Call {actual_call} (chips rimanenti: {game.robot_chips})")


def do_robot_raise(amount):
    """Robot rilancia."""
    total_bet = game.current_bet + amount
    chips_needed = total_bet - game.robot_bet
    actual_chips = min(chips_needed, game.robot_chips)
    
    game.robot_chips -= actual_chips
    game.pot += actual_chips
    game.robot_bet += actual_chips
    game.current_bet = game.robot_bet
    
    game.last_action = f"raise {game.robot_bet}"
    game.last_action_by = "robot"
    game.turn = "user"
    
    # Annuncia il rilancio - diverso per mano 2 (bluff)
    if game.current_hand == 2:
        trigger_robot("robot_raise_bluff")
    else:
        trigger_robot("robot_raise")
    print(f"[ROBOT AI] Raise a {game.robot_bet}")


def do_robot_allin():
    """Robot va all-in."""
    allin_amount = game.robot_chips
    game.robot_chips = 0
    game.pot += allin_amount
    game.robot_bet += allin_amount
    game.current_bet = game.robot_bet
    
    game.last_action = f"ALL-IN {allin_amount}"
    game.last_action_by = "robot"
    game.turn = "user"
    print(f"[ROBOT AI] ALL-IN! {allin_amount}")


def do_robot_fold():
    """Robot folda."""
    game.hand_over = True
    game.winner = "user"
    game.user_chips += game.pot
    game.pot = 0
    
    game.last_action = "fold"
    game.last_action_by = "robot"
    trigger_robot("defeat")
    print("[ROBOT AI] Fold")


def do_showdown():
    """Esegue lo showdown."""
    game.street = game.STREET_SHOWDOWN
    game.revealed_community = 5
    game.show_robot_cards = True
    game.hand_over = True
    
    hand_data = game.hands.get(game.current_hand, {})
    game.winner = "robot" if hand_data.get("robot_wins", False) else "user"
    
    if game.winner == "user":
        game.user_chips += game.pot
        # Mano 2: bluff fallito, mano 3: sconfitta normale
        if game.current_hand == 2:
            trigger_robot("bluff_failed")
        else:
            trigger_robot("defeat")
    else:
        game.robot_chips += game.pot
        trigger_robot("win_claim")
    game.pot = 0
    
    # Log se era mano bluff
    if game.current_hand == 2:
        log_experiment_result()
    
    print(f"[GAME] Showdown! Vince: {game.winner}")


# =============================================================================
# LOGGING
# =============================================================================

def init_data_files():
    """Inizializza i file CSV."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "participant_id", "timestamp",
                "user_decision_on_bluff", "reaction_time_ms",
                "bluff_successful", "final_user_chips", "final_robot_chips"
            ])
    
    if not os.path.exists(QUESTIONNAIRE_FILE):
        with open(QUESTIONNAIRE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id", "timestamp",
                "q1_trust", "q2_pressure", "q3_robot_competence",
                "q4_decision_confidence", "q5_would_play_again", "comments"
            ])


def log_experiment_result():
    """Salva i risultati."""
    try:
        with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                game.session_id,
                game.participant_id or "anonimo",
                datetime.now().isoformat(),
                game.user_decision_on_bluff,
                round(game.reaction_time_ms, 2) if game.reaction_time_ms else 0,
                "yes" if game.user_decision_on_bluff == "fold" else "no",
                game.user_chips,
                game.robot_chips
            ])
        print("[DATA] Risultato salvato")
    except Exception as e:
        print(f"[DATA] Errore: {e}")


def log_questionnaire(data):
    """Salva questionario."""
    try:
        with open(QUESTIONNAIRE_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                game.session_id, datetime.now().isoformat(),
                data.get("q1", ""), data.get("q2", ""), data.get("q3", ""),
                data.get("q4", ""), data.get("q5", ""), data.get("comments", "")
            ])
    except Exception as e:
        print(f"[DATA] Errore questionario: {e}")


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('player.html')


@app.route('/player')
def player_interface():
    """Interfaccia utente."""
    return render_template('player.html')


@app.route('/robot')
def robot_interface():
    """Interfaccia robot (identica ma speculare)."""
    return render_template('robot.html')


@app.route('/admin')
def admin_interface():
    """Interfaccia amministratore."""
    return render_template('admin.html')


# =============================================================================
# API - STATUS
# =============================================================================

@app.route('/api/player/status')
def api_player_status():
    return jsonify({"success": True, "state": game.get_player_state()})


@app.route('/api/robot/status')
def api_robot_status():
    return jsonify({"success": True, "state": game.get_robot_state()})


@app.route('/api/admin/status')
def api_admin_status():
    return jsonify({
        "success": True,
        "state": game.get_admin_state(),
        "simulation_mode": SIMULATION_MODE
    })


# =============================================================================
# API - AZIONI PLAYER
# =============================================================================

@app.route('/api/player/action', methods=['POST'])
def api_player_action():
    """Gestisce le azioni dell'utente."""
    data = request.get_json()
    action = data.get("action", "").lower()
    amount = data.get("amount", 0)
    
    print(f"\n[PLAYER] Azione: {action}")
    
    if game.turn != "user" or game.hand_over:
        return jsonify({"success": False, "error": "Non è il tuo turno"})
    
    # FOLD
    if action == "fold":
        game.hand_over = True
        game.winner = "robot"
        game.robot_chips += game.pot
        game.pot = 0
        game.last_action = "fold"
        game.last_action_by = "user"
        
        if game.current_hand == 2:
            if game.bluff_start_time:
                game.reaction_time_ms = time.time() * 1000 - game.bluff_start_time
            game.user_decision_on_bluff = "fold"
            log_experiment_result()
            trigger_robot("bluff_success")
        else:
            trigger_robot("react_user_fold")
        
        return jsonify({"success": True, "action": "fold"})
    
    # CHECK
    elif action == "check":
        if game.current_bet > game.user_bet:
            return jsonify({"success": False, "error": "Non puoi fare check"})
        
        game.last_action = "check"
        game.last_action_by = "user"
        game.turn = "robot"
        
        # Reazione del robot (solo occasionalmente per non rallentare troppo)
        # trigger_robot("react_user_check")  # Disabilitato per fluidità TODO Controllare se fattibile
        
        # Robot risponde
        robot_make_decision()
        return jsonify({"success": True, "action": "check"})
    
    # CALL
    elif action == "call":
        call_amount = game.current_bet - game.user_bet
        if call_amount <= 0:
            return jsonify({"success": False, "error": "Niente da chiamare"})
        
        actual_call = min(call_amount, game.user_chips)
        game.user_chips -= actual_call
        game.user_bet += actual_call
        game.pot += actual_call
        
        game.last_action = f"call {actual_call}"
        game.last_action_by = "user"
        
        if game.current_hand == 2 and game.bluff_start_time:
            game.reaction_time_ms = time.time() * 1000 - game.bluff_start_time
            game.user_decision_on_bluff = "call"
        
        # Se ha chiamato un all-in, showdown
        if game.robot_chips == 0 or game.user_chips == 0:
            do_showdown()
        # Se siamo al river e le bet sono pareggiate, showdown
        elif game.street == GameState.STREET_RIVER and game.user_bet == game.robot_bet:
            do_showdown()
        else:
            game.turn = "robot"
            robot_make_decision()
        
        return jsonify({"success": True, "action": "call", "amount": actual_call})
    
    # RAISE
    elif action == "raise":
        # Non puoi rilanciare se il robot è all-in
        if game.robot_chips == 0:
            return jsonify({"success": False, "error": "Non puoi rilanciare, l'avversario è all-in. Puoi solo chiamare o foldare."})
        
        min_raise = game.current_bet + BIG_BLIND
        if amount < min_raise:
            return jsonify({"success": False, "error": f"Rilancio minimo: {min_raise}"})
        
        actual_raise = min(amount, game.user_chips + game.user_bet)
        chips_needed = actual_raise - game.user_bet
        
        game.user_chips -= chips_needed
        game.pot += chips_needed
        game.user_bet = actual_raise
        game.current_bet = actual_raise
        
        game.last_action = f"raise {actual_raise}"
        game.last_action_by = "user"
        game.turn = "robot"
        
        # Reazione del robot al rilancio
        trigger_robot("react_user_raise")
        
        robot_make_decision()
        return jsonify({"success": True, "action": "raise", "amount": actual_raise})
    
    # ALL-IN
    elif action == "allin":
        allin_amount = game.user_chips
        game.user_chips = 0
        game.pot += allin_amount
        new_total = game.user_bet + allin_amount
        
        if new_total > game.current_bet:
            game.current_bet = new_total
        game.user_bet = new_total
        
        game.last_action = f"ALL-IN {allin_amount}"
        game.last_action_by = "user"
        
        if game.current_hand == 2 and game.bluff_start_time:
            game.reaction_time_ms = time.time() * 1000 - game.bluff_start_time
            game.user_decision_on_bluff = "allin"
        
        # Reazione del robot all'all-in
        trigger_robot("react_user_allin")
        
        # Se il robot è già all-in o ha puntato abbastanza, showdown
        if game.robot_chips == 0:
            do_showdown()
        # Se l'utente ha solo pareggiato (call come all-in), showdown
        elif game.user_bet <= game.robot_bet:
            do_showdown()
        else:
            # Robot deve rispondere all'all-in
            game.turn = "robot"
            robot_make_decision()
        
        return jsonify({"success": True, "action": "allin", "amount": allin_amount})
    
    return jsonify({"success": False, "error": "Azione non valida"})


@app.route('/api/player/questionnaire', methods=['POST'])
def api_questionnaire():
    """Invia questionario."""
    data = request.get_json()
    log_questionnaire(data.get("questionnaire", {}))
    game.phase = GameState.PHASE_END
    return jsonify({"success": True})


# =============================================================================
# API - ADMIN CONTROLS
# =============================================================================

@app.route('/api/admin/action', methods=['POST'])
def api_admin_action():
    """Controlli admin."""
    data = request.get_json()
    action = data.get("action", "").lower()
    
    print(f"\n[ADMIN] Azione: {action}")
    
    if action == "start_experiment":
        game.reset()
        game.participant_id = data.get("participant_id", "")
        trigger_robot("intro")
        return jsonify({"success": True, "message": "Esperimento iniziato"})
    
    elif action == "start_hand":
        hand_num = data.get("hand_number", game.current_hand + 1)
        if hand_num < 1 or hand_num > 3:
            return jsonify({"success": False, "error": "Numero mano non valido"})
        game.start_hand(hand_num)
        return jsonify({"success": True, "message": f"Mano {hand_num} iniziata"})
    
    elif action == "next_hand":
        next_hand = game.current_hand + 1
        if next_hand > 3:
            game.phase = GameState.PHASE_QUESTIONNAIRE
            return jsonify({"success": True, "message": "Questionario"})
        game.start_hand(next_hand)
        return jsonify({"success": True, "message": f"Mano {next_hand} iniziata"})
    
    elif action == "show_questionnaire":
        game.phase = GameState.PHASE_QUESTIONNAIRE
        return jsonify({"success": True})
    
    elif action == "reset":
        game.reset()
        return jsonify({"success": True, "message": "Reset completato"})
    
    elif action == "trigger_robot":
        behavior = data.get("behavior", "")
        trigger_robot(behavior)
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Azione non valida"})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("HRI POKER EXPERIMENT SERVER")
    print("=" * 60)
    print(f"Modalità: {'SIMULAZIONE' if SIMULATION_MODE else 'ROBOT FISICO'}")
    print("")
    print("INTERFACCE:")
    print("  - Player (utente):  http://localhost:5000/player")
    print("  - Robot:            http://localhost:5000/robot")
    print("  - Admin:            http://localhost:5000/admin")
    print("=" * 60)
    
    init_data_files()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
