#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di verifica del sistema HRI Poker.

Esegue tutti i controlli necessari prima di un esperimento:
  1. Verifica che i file del progetto esistano
  2. Verifica le dipendenze Python (Flask, NAOqi)
  3. Verifica la sintassi di server.py
  4. Verifica la cartella dati
  5. Esegue TUTTE le azioni del robot in simulazione (via test_all_actions)
  6. Stampa il report di sicurezza statica

Usage:
    python3 verify_system.py
    python3 verify_system.py --verbose     # output dettagliato delle azioni robot
"""

import os
import sys
import subprocess
import argparse

# Assicuriamoci di importare dal percorso corretto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_all_actions import (
    run_all_action_tests,
    print_safety_report,
    print_results_table,
    print_ok,
    print_fail,
    print_warn,
    GREEN, RED, YELLOW, RESET, BOLD,
)


def main():
    parser = argparse.ArgumentParser(
        description="Verifica completa del sistema HRI Poker"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostra output dettagliato delle azioni robot"
    )
    parser.add_argument(
        "--pause", "-p",
        action="store_true",
        help="Attende pressione di Invio tra un'azione e l'altra"
    )
    args = parser.parse_args()

    print(f"\n{'='*64}")
    print(f"  VERIFICA SISTEMA HRI POKER")
    print(f"{'='*64}\n")
    
    errors = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # =========================================================================
    # [1] Verifica file del progetto
    # =========================================================================
    print(f"  {BOLD}[1] Verifica file del progetto{RESET}")
    
    required_files = [
        "server.py",
        "robot_controller.py",
        "test_all_actions.py",
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
    
    # =========================================================================
    # [2] Verifica dipendenze Python
    # =========================================================================
    print(f"\n  {BOLD}[2] Verifica dipendenze Python{RESET}")
    
    try:
        import flask
        print_ok(f"Flask installato (versione {flask.__version__})")
    except ImportError:
        print_fail("Flask NON installato")
        errors.append("Flask non installato. Esegui: pip install flask")
    
    try:
        from naoqi import ALProxy
        print_ok("NAOqi SDK disponibile")
    except ImportError:
        print_warn("NAOqi SDK non disponibile (verra' usata simulazione)")
    
    # =========================================================================
    # [3] Verifica sintassi server.py
    # =========================================================================
    print(f"\n  {BOLD}[3] Verifica sintassi server.py{RESET}")
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
    
    # =========================================================================
    # [4] Verifica cartella dati
    # =========================================================================
    print(f"\n  {BOLD}[4] Verifica cartella dati{RESET}")
    data_dir = os.path.join(base_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print_ok("Cartella 'data/' creata")
    else:
        print_ok("Cartella 'data/' esiste")
    
    # =========================================================================
    # [5] Test completo azioni robot (tutte e 19)
    # =========================================================================
    print(f"\n  {BOLD}[5] Test completo azioni robot (simulazione){RESET}")
    
    passed, failed, results = run_all_action_tests(verbose=args.verbose, pause=args.pause)
    total_time = sum(r[4] for r in results)
    
    if failed > 0:
        errors.append(f"{failed} azione/i robot fallita/e")
    
    # Tabella riassuntiva
    print_results_table(results)
    
    print(f"\n  Azioni: {GREEN}{passed} passate{RESET}, "
          f"{RED + str(failed) + RESET if failed else '0'} fallite, "
          f"tempo totale {total_time:.2f}s")
    
    # =========================================================================
    # [6] Controllo sicurezza statica
    # =========================================================================
    print(f"\n  {BOLD}[6] Controllo sicurezza statica{RESET}")
    print_safety_report()
    
    # =========================================================================
    # RIEPILOGO FINALE
    # =========================================================================
    print(f"\n{'='*64}")
    if errors:
        print(f"  {RED}{BOLD}ERRORI TROVATI: {len(errors)}{RESET}")
        for e in errors:
            print(f"    - {e}")
        print(f"\n  Correggi gli errori prima di avviare l'esperimento.")
    else:
        print(f"  {GREEN}{BOLD}SISTEMA PRONTO!{RESET}")
        print(f"\n  Per avviare il server:")
        print(f"    {YELLOW}SIMULATION_MODE=true python3 server.py{RESET}")
        print(f"\n  Interfacce:")
        print(f"    - Player: http://localhost:5000/player")
        print(f"    - Robot:  http://localhost:5000/robot")
        print(f"    - Admin:  http://localhost:5000/admin")
    print(f"{'='*64}\n")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
