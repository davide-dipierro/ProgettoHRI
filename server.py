#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask Server - HRI Poker Experiment

Interfacce web:
- /player -> Interfaccia utente (davanti all'utente)
- /robot  -> Interfaccia robot (speculare)
- /admin  -> Interfaccia amministratore

La logica di gioco e' in game_state.py.
La configurazione e' in config.py (caricata da .env).
"""

from __future__ import print_function
import subprocess
from flask import Flask, render_template, request, jsonify

from config import (
    NAO_IP, NAO_PORT, PYTHON27_PATH, ROBOT_SCRIPT,
    SIMULATION_MODE, SERVER_HOST, SERVER_PORT,
)
from data_logger import init_data_files
from game_state import GameState

app = Flask(__name__)


# =============================================================================
# COMUNICAZIONE CON IL ROBOT
# =============================================================================

def trigger_robot(action):
    """Invia un comando al robot tramite subprocess (Python 2.7 + NAOqi)."""
    try:
        cmd = [PYTHON27_PATH, ROBOT_SCRIPT, "--action", action]
        if SIMULATION_MODE:
            cmd.append("--simulate")
        else:
            cmd.extend(["--ip", NAO_IP, "--port", str(NAO_PORT)])

        print("[ROBOT] Eseguo: {}".format(' '.join(cmd)))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()

        if proc.returncode == 0:
            print("[ROBOT] Azione '{}' completata".format(action))
            return True
        return False
    except Exception as e:
        print("[ROBOT] Eccezione: {}".format(e))
        return False


# Stato di gioco (singleton)
game = GameState()
game.set_robot_trigger(trigger_robot)


# =============================================================================
# ROUTES - PAGINE HTML
# =============================================================================

@app.route('/')
def index():
    return render_template('player.html')


@app.route('/player')
def player_interface():
    return render_template('player.html')


@app.route('/robot')
def robot_interface():
    return render_template('robot.html')


@app.route('/admin')
def admin_interface():
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
# API - AZIONI
# =============================================================================

@app.route('/api/player/action', methods=['POST'])
def api_player_action():
    data = request.get_json()
    result = game.handle_player_action(data.get("action", ""),
                                       data.get("amount", 0))
    return jsonify(result)


@app.route('/api/player/questionnaire', methods=['POST'])
def api_questionnaire():
    data = request.get_json()
    result = game.handle_questionnaire(data.get("questionnaire", {}))
    return jsonify(result)


@app.route('/api/admin/action', methods=['POST'])
def api_admin_action():
    data = request.get_json()
    result = game.handle_admin_action(data.get("action", ""), data)
    return jsonify(result)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("HRI POKER EXPERIMENT SERVER")
    print("=" * 60)
    print("Modalita': {}".format(
        'SIMULAZIONE' if SIMULATION_MODE else 'ROBOT FISICO'))
    print("")
    print("INTERFACCE:")
    print("  - Player:  http://localhost:{}/player".format(SERVER_PORT))
    print("  - Robot:   http://localhost:{}/robot".format(SERVER_PORT))
    print("  - Admin:   http://localhost:{}/admin".format(SERVER_PORT))
    print("=" * 60)

    init_data_files()
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, threaded=True)
