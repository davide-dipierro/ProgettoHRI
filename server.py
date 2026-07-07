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
import time
import threading
import atexit
from flask import Flask, render_template, request, jsonify

import config
from data_logger import init_data_files
from game_state import GameState

# Compatibilita' Python 2/3 per richieste HTTP
try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError

app = Flask(__name__)


# =============================================================================
# COMUNICAZIONE CON IL ROBOT
# =============================================================================

robot_process = None
_robot_status = {
    "running": False,
    "restarting": False,
    "last_start": None,
    "last_error": None,
    "ip": config.NAO_IP,
    "port": config.NAO_PORT,
    "simulation": config.SIMULATION_MODE,
    "robot_enabled": True
}
_status_lock = threading.Lock()


def _update_robot_status(**kwargs):
    """Aggiorna lo stato interno del robot in modo thread-safe."""
    with _status_lock:
        _robot_status.update(kwargs)


def start_robot_server():
    """Avvia robot_controller.py come processo in background."""
    global robot_process
    cmd = [config.PYTHON27_PATH, config.ROBOT_SCRIPT, "--server"]
    if config.SIMULATION_MODE:
        cmd.append("--simulate")
    else:
        cmd.extend(["--ip", config.NAO_IP, "--port", str(config.NAO_PORT)])
        
    print("[SERVER] Avvio robot_controller.py in background...")
    print("[SERVER] Comando: {}".format(" ".join(cmd)))
    try:
        robot_process = subprocess.Popen(cmd)
        time.sleep(2)  # Attendi che il server sia pronto
        # Verifica che il processo sia ancora in vita
        if robot_process.poll() is not None:
            _update_robot_status(
                running=False,
                last_error="Processo terminato con codice {}".format(robot_process.returncode)
            )
            print("[SERVER] ERRORE: robot_controller.py terminato subito (codice {})".format(
                robot_process.returncode))
        else:
            _update_robot_status(
                running=True,
                last_start=time.strftime("%H:%M:%S"),
                last_error=None,
                ip=config.NAO_IP,
                port=config.NAO_PORT,
                simulation=config.SIMULATION_MODE
            )
            print("[SERVER] robot_controller.py avviato con successo")
    except Exception as e:
        _update_robot_status(
            running=False,
            last_error=str(e)
        )
        print("[SERVER] ERRORE avvio robot_controller.py: {}".format(e))


def stop_robot_server():
    """Ferma il processo robot_controller.py."""
    global robot_process
    if robot_process:
        print("[SERVER] Chiusura robot_controller.py...")
        try:
            robot_process.terminate()
            robot_process.wait()
        except Exception:
            pass
        _update_robot_status(running=False)

atexit.register(stop_robot_server)


def restart_robot_server_async():
    """Riavvia robot_controller.py in un thread separato (non-bloccante)."""
    _update_robot_status(restarting=True, last_error=None)
    
    def _do_restart():
        try:
            stop_robot_server()
            time.sleep(0.5)
            start_robot_server()
        except Exception as e:
            _update_robot_status(last_error=str(e))
            print("[SERVER] Errore durante riavvio: {}".format(e))
        finally:
            _update_robot_status(restarting=False)
    
    t = threading.Thread(target=_do_restart)
    t.daemon = True
    t.start()


def trigger_robot(action):
    """Invia un comando al robot in modo asincrono (fire-and-forget).
    
    Non blocca il thread Flask: la richiesta HTTP viene inviata in un thread
    separato con timeout di 30s per gestire azioni lunghe (es. bluff ~8s).
    
    Se il robot e' disattivato (robot_enabled=False), l'azione viene ignorata
    senza influenzare il motore di gioco o l'IA.
    """
    with _status_lock:
        if not _robot_status["robot_enabled"]:
            print("[ROBOT] DISABLED - skipping: {}".format(action))
            return False

    def _send():
        try:
            url = "http://127.0.0.1:5001/?action={}".format(action)
            response = urlopen(url, timeout=30)
            if response.getcode() != 200:
                print("[ROBOT] Risposta non-200: {}".format(response.getcode()))
        except Exception as e:
            print("[ROBOT] Eccezione chiamata server: {}".format(e))
        finally:
            with game._lock:
                game.pending_robot_actions = max(0, game.pending_robot_actions - 1)

    with game._lock:
        game.pending_robot_actions += 1
    print("[ROBOT] Trigger asincrono: {}".format(action))
    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()
    return True


def ping_robot_server():
    """Verifica se il server robot (porta 5001) risponde."""
    try:
        response = urlopen("http://127.0.0.1:5001/health", timeout=2)
        if response.getcode() == 200:
            data = response.read().decode("utf-8")
            import json
            return json.loads(data)
        return None
    except Exception:
        return None


# Stato di gioco (singleton)
game = GameState()
game.set_robot_trigger(trigger_robot)
game.experiment.robot_mode = "simulation" if config.SIMULATION_MODE else "real"


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
    state = game.get_player_state()
    # Verifica stato fisico del robot
    robot_health = ping_robot_server()
    is_interacting = robot_health.get("is_interacting", False) if robot_health else False
    
    with game._lock:
        is_interacting = is_interacting or (game.pending_robot_actions > 0)
        
    state["robot_interacting"] = is_interacting
    return jsonify({"success": True, "state": state})


@app.route('/api/robot/status')
def api_robot_status():
    state = game.get_robot_state()
    robot_health = ping_robot_server()
    is_interacting = robot_health.get("is_interacting", False) if robot_health else False
    
    with game._lock:
        is_interacting = is_interacting or (game.pending_robot_actions > 0)
        
    state["robot_interacting"] = is_interacting
    return jsonify({"success": True, "state": state})


@app.route('/api/admin/status')
def api_admin_status():
    with _status_lock:
        robot_enabled = _robot_status["robot_enabled"]
    return jsonify({
        "success": True,
        "state": game.get_admin_state(),
        "simulation_mode": config.SIMULATION_MODE,
        "robot_enabled": robot_enabled
    })


@app.route('/api/admin/config', methods=['GET', 'POST'])
def api_admin_config():
    if request.method == 'GET':
        return jsonify({
            "success": True,
            "NAO_IP": config.NAO_IP,
            "NAO_PORT": config.NAO_PORT,
            "SIMULATION_MODE": config.SIMULATION_MODE
        })
    else:
        data = request.get_json()
        updates = {}
        if "NAO_IP" in data: updates["NAO_IP"] = str(data["NAO_IP"])
        if "NAO_PORT" in data: updates["NAO_PORT"] = str(data["NAO_PORT"])
        if "SIMULATION_MODE" in data: updates["SIMULATION_MODE"] = "true" if data["SIMULATION_MODE"] else "false"
        
        config.save_env_file(updates)
        config.reload_config()
        # Aggiorna robot_mode dopo cambio configurazione
        game.experiment.robot_mode = "simulation" if config.SIMULATION_MODE else "real"
        restart_robot_server_async()
        return jsonify({"success": True, "message": "Configurazione salvata. Robot in riavvio..."})


@app.route('/api/admin/robot_status')
def api_admin_robot_status():
    """Stato del processo robot_controller.py e connessione."""
    global robot_process
    
    # Aggiorna stato running controllando il processo
    if robot_process and robot_process.poll() is not None:
        _update_robot_status(running=False)
    
    with _status_lock:
        status = dict(_robot_status)
    
    # Ping al server robot per verifica effettiva
    health = ping_robot_server()
    status["responsive"] = health is not None
    if health:
        status["controller_mode"] = health.get("mode", "unknown")
        status["controller_ready"] = health.get("ready", False)
        status["controller_error"] = health.get("error", None)
    else:
        status["controller_ready"] = False
        status["controller_error"] = None
    
    return jsonify({"success": True, "status": status})


@app.route('/api/admin/toggle_robot', methods=['POST'])
def api_admin_toggle_robot():
    """Attiva/disattiva l'invio di animazioni e parlato al robot.
    
    Il motore di gioco e l'IA continuano a funzionare normalmente.
    Solo l'invio fisico/simulato al robot viene bloccato.
    """
    with _status_lock:
        _robot_status["robot_enabled"] = not _robot_status["robot_enabled"]
        new_state = _robot_status["robot_enabled"]
    
    # Aggiorna robot_mode nell'experiment manager
    if new_state:
        game.experiment.robot_mode = "simulation" if config.SIMULATION_MODE else "real"
    else:
        game.experiment.robot_mode = "disabled"
    
    state_label = "ATTIVATO" if new_state else "DISATTIVATO"
    print("[SERVER] Robot {}".format(state_label))
    return jsonify({
        "success": True,
        "robot_enabled": new_state,
        "message": "Robot {}".format(state_label)
    })


@app.route('/api/admin/test_robot', methods=['POST'])
def api_admin_test_robot():
    """Testa la connessione al robot inviando un comando di test."""
    health = ping_robot_server()
    if health:
        ready = health.get("ready", False)
        mode = health.get("mode", "unknown")
        error = health.get("error", None)
        if ready:
            return jsonify({
                "success": True,
                "message": "Robot controller pronto (modo: {})".format(mode),
                "details": health
            })
        else:
            return jsonify({
                "success": False,
                "error": "Controller risponde ma robot in connessione... (modo: {})".format(mode),
                "details": health
            })
    else:
        return jsonify({
            "success": False,
            "error": "Robot controller non risponde sulla porta 5001"
        })


@app.route('/api/admin/find_nao', methods=['POST'])
def api_admin_find_nao():
    import json
    import os
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "find_nao_port.ps1")
    try:
        proc = subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, "-Json", "-Top", "12"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode == 0 and stdout.strip():
            result = json.loads(stdout.strip())
            # Normalize: always return a list (single result comes as dict)
            if isinstance(result, dict):
                result = [result]
            candidates = []
            for item in result:
                candidates.append({
                    "port": item.get("Port"),
                    "score": item.get("Score", 0),
                    "role": item.get("Role", "other"),
                    "process": item.get("ProcessName", ""),
                    "pid": item.get("PID", 0)
                })
            # Return best port + all candidates
            best_port = candidates[0]["port"] if candidates else None
            return jsonify({"success": True, "port": best_port, "candidates": candidates})
        return jsonify({"success": False, "error": "Nessuna porta trovata.", "candidates": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "candidates": []})


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
        'SIMULAZIONE' if config.SIMULATION_MODE else 'ROBOT FISICO'))
    print("")
    print("INTERFACCE:")
    print("  - Player:  http://localhost:{}/player".format(config.SERVER_PORT))
    print("  - Robot:   http://localhost:{}/robot".format(config.SERVER_PORT))
    print("  - Admin:   http://localhost:{}/admin".format(config.SERVER_PORT))
    print("=" * 60)

    init_data_files()
    start_robot_server()
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=False, threaded=True)
