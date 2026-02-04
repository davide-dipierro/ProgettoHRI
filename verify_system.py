#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di verifica del sistema HRI Poker.
Esegui questo script per verificare che tutti i componenti funzionino.
"""

import os
import sys
import subprocess
import time

# Colori per output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_ok(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_fail(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warn(msg):
    print(f"{YELLOW}!{RESET} {msg}")

def main():
    print("\n" + "="*60)
    print("VERIFICA SISTEMA HRI POKER")
    print("="*60 + "\n")
    
    errors = []
    
    # 1. Verifica file esistono
    print("[1] Verifica file del progetto...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    required_files = [
        "server.py",
        "robot_controller.py",
        "templates/player.html",
        "templates/robot.html",
        "templates/admin.html"
    ]
    
    for f in required_files:
        path = os.path.join(base_dir, f)
        if os.path.exists(path):
            print_ok(f"File trovato: {f}")
        else:
            print_fail(f"File MANCANTE: {f}")
            errors.append(f"File mancante: {f}")
    
    # 2. Verifica Flask installato
    print("\n[2] Verifica dipendenze Python...")
    try:
        import flask
        print_ok(f"Flask installato (versione {flask.__version__})")
    except ImportError:
        print_fail("Flask NON installato")
        errors.append("Flask non installato. Esegui: pip install flask")
    
    # 3. Verifica NAOqi (opzionale)
    try:
        from naoqi import ALProxy
        print_ok("NAOqi SDK disponibile")
    except ImportError:
        print_warn("NAOqi SDK non disponibile (verrà usata simulazione)")
    
    # 4. Test robot_controller.py
    print("\n[3] Test robot_controller.py...")
    robot_script = os.path.join(base_dir, "robot_controller.py")
    
    test_actions = ["intro", "robot_check", "bluff"]
    
    for action in test_actions:
        try:
            result = subprocess.run(
                ["python3", robot_script, "--action", action, "--simulate"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print_ok(f"Azione '{action}' funziona")
            else:
                print_fail(f"Azione '{action}' fallita: {result.stderr}")
                errors.append(f"robot_controller.py azione '{action}' fallita")
        except subprocess.TimeoutExpired:
            print_fail(f"Azione '{action}' timeout")
            errors.append(f"robot_controller.py azione '{action}' timeout")
        except Exception as e:
            print_fail(f"Azione '{action}' errore: {e}")
            errors.append(f"robot_controller.py errore: {e}")
    
    # 5. Verifica sintassi server.py
    print("\n[4] Verifica sintassi server.py...")
    server_script = os.path.join(base_dir, "server.py")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "py_compile", server_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print_ok("server.py sintassi OK")
        else:
            print_fail(f"server.py errore sintassi: {result.stderr}")
            errors.append("server.py errore di sintassi")
    except Exception as e:
        print_fail(f"Verifica sintassi fallita: {e}")
    
    # 6. Verifica cartella data
    print("\n[5] Verifica cartella dati...")
    data_dir = os.path.join(base_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print_ok(f"Cartella 'data/' creata")
    else:
        print_ok(f"Cartella 'data/' esiste")
    
    # Riepilogo
    print("\n" + "="*60)
    if errors:
        print(f"{RED}ERRORI TROVATI: {len(errors)}{RESET}")
        for e in errors:
            print(f"  - {e}")
        print("\nCorreggi gli errori prima di avviare l'esperimento.")
    else:
        print(f"{GREEN}SISTEMA PRONTO!{RESET}")
        print("\nPer avviare il server:")
        print(f"  {YELLOW}SIMULATION_MODE=true python3 server.py{RESET}")
        print("\nInterfacce:")
        print("  - Player: http://localhost:5000/player")
        print("  - Robot:  http://localhost:5000/robot")
        print("  - Admin:  http://localhost:5000/admin")
    print("="*60 + "\n")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
