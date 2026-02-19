#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script di verifica del sistema HRI Poker.

Esegue tutti i controlli necessari prima di un esperimento:
  1. Verifica che i file del progetto esistano
  2. Verifica le dipendenze Python (Flask, qi)
  3. Verifica la sintassi di server.py
  4. Verifica la cartella dati
  5. Esegue TUTTE le azioni del robot in simulazione (via test_all_actions)
  6. Stampa il report di sicurezza statica

Usage:
    python verify_system.py
    python verify_system.py --verbose     # output dettagliato delle azioni robot
"""

from __future__ import print_function
import os
import sys
import subprocess
import argparse

# Configura il path dell'SDK Choregraphe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_config

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

    print('\n{}'.format('='*64))
    print('  VERIFICA SISTEMA HRI POKER')
    print('{}\n'.format('='*64))
    
    errors = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # =========================================================================
    # [1] Verifica file del progetto
    # =========================================================================
    print('  {}[1] Verifica file del progetto{}'.format(BOLD, RESET))
    
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
            print_ok('File trovato: {}'.format(f))
        else:
            print_fail('File MANCANTE: {}'.format(f))
            errors.append('File mancante: {}'.format(f))
    
    # =========================================================================
    # [2] Verifica dipendenze Python
    # =========================================================================
    print('\n  {}[2] Verifica dipendenze Python{}'.format(BOLD, RESET))
    
    try:
        import flask
        print_ok('Flask installato (versione {})'.format(flask.__version__))
    except ImportError:
        print_fail('Flask NON installato')
        errors.append('Flask non installato. Esegui: pip install flask')
    
    try:
        import qi
        print_ok('qi SDK disponibile')
    except ImportError:
        print_warn('qi SDK non disponibile (verra\' usata simulazione)')
    
    # =========================================================================
    # [3] Verifica sintassi server.py
    # =========================================================================
    print('\n  {}[3] Verifica sintassi server.py{}'.format(BOLD, RESET))
    server_script = os.path.join(base_dir, 'server.py')
    
    try:
        proc = subprocess.Popen(
            ['python', '-m', 'py_compile', server_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            print_ok('server.py sintassi OK')
        else:
            print_fail('server.py errore sintassi: {}'.format(stderr))
            errors.append('server.py errore di sintassi')
    except Exception as e:
        print_fail('Verifica sintassi fallita: {}'.format(e))
    
    # =========================================================================
    # [4] Verifica cartella dati
    # =========================================================================
    print('\n  {}[4] Verifica cartella dati{}'.format(BOLD, RESET))
    data_dir = os.path.join(base_dir, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print_ok("Cartella 'data/' creata")
    else:
        print_ok("Cartella 'data/' esiste")
    
    # =========================================================================
    # [5] Test completo azioni robot (tutte e 19)
    # =========================================================================
    print('\n  {}[5] Test completo azioni robot (simulazione){}'.format(BOLD, RESET))
    
    passed, failed, results = run_all_action_tests(verbose=args.verbose, pause=args.pause)
    total_time = sum(r[4] for r in results)
    
    if failed > 0:
        errors.append('{} azione/i robot fallita/e'.format(failed))
    
    # Tabella riassuntiva
    print_results_table(results)
    
    print('\n  Azioni: {}{}  passate{}, '
          '{} fallite, '
          'tempo totale {:.2f}s'.format(
              GREEN, passed, RESET,
              '{}{}{}'.format(RED, failed, RESET) if failed else '0',
              total_time))
    
    # =========================================================================
    # [6] Controllo sicurezza statica
    # =========================================================================
    print('\n  {}[6] Controllo sicurezza statica{}'.format(BOLD, RESET))
    print_safety_report()
    
    # =========================================================================
    # RIEPILOGO FINALE
    # =========================================================================
    print('\n{}'.format('='*64))
    if errors:
        print('  {}{}ERRORI TROVATI: {}{}'.format(RED, BOLD, len(errors), RESET))
        for e in errors:
            print('    - {}'.format(e))
        print('\n  Correggi gli errori prima di avviare l\'esperimento.')
    else:
        print('  {}{}SISTEMA PRONTO!{}'.format(GREEN, BOLD, RESET))
        print('\n  Per avviare il server:')
        print('    {}SIMULATION_MODE=true python server.py{}'.format(YELLOW, RESET))
        print('\n  Interfacce:')
        print('    - Player: http://localhost:5000/player')
        print('    - Robot:  http://localhost:5000/robot')
        print('    - Admin:  http://localhost:5000/admin')
    print('{}\n'.format('='*64))
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
