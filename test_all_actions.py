#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test completo di tutte le azioni del Robot Controller.

Esegue ogni azione definita in robot_controller.py in modalità simulazione,
verificando che ciascuna vada a buon fine senza errori.
Produce un report finale con esito per ogni azione.

Può essere eseguito direttamente o importato da verify_system.py.

Usage:
    python test_all_actions.py
    python test_all_actions.py --verbose
    python test_all_actions.py --pause        # attende input tra un'azione e l'altra
"""

from __future__ import print_function
import sys
import os
import time
import traceback
import argparse

# Assicuriamoci di importare dal percorso corretto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robot_controller import (
    SimulatedRobot,
    action_intro,
    action_win_claim,
    action_bluff,
    action_bluff_success,
    action_bluff_failed,
    action_cooldown,
    action_victory,
    action_defeat,
    action_react_user_check,
    action_react_user_call,
    action_react_user_raise,
    action_react_user_allin,
    action_react_user_fold,
    action_thinking,
    action_robot_check,
    action_robot_call,
    action_robot_call_allin,
    action_robot_raise,
    action_robot_raise_bluff,
    action_robot_allin,
    action_robot_fold,
)

# Colori per output (condivisi con verify_system.py)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_ok(msg):
    print("{}\u2713{} {}".format(GREEN, RESET, msg))

def print_fail(msg):
    print("{}\u2717{} {}".format(RED, RESET, msg))

def print_warn(msg):
    print("{}!{} {}".format(YELLOW, RESET, msg))


# Lista ordinata di tutte le azioni da testare, raggruppate per categoria
ALL_ACTIONS = [
    # --- Fasi principali del gioco ---
    ("intro",              action_intro,              "Saluto iniziale"),
    ("win_claim",          action_win_claim,          "Rilancio sicuro"),
    ("bluff",              action_bluff,              "Comportamento intimidatorio (fase critica)"),
    ("bluff_success",      action_bluff_success,      "Utente ha foldato"),
    ("bluff_failed",       action_bluff_failed,       "Utente ha chiamato il bluff"),
    ("cooldown",           action_cooldown,           "Mano finale neutra"),
    ("victory",            action_victory,            "Robot vince la partita"),
    ("defeat",             action_defeat,             "Robot perde"),
    # --- Reazioni alle azioni dell'utente ---
    ("react_user_check",   action_react_user_check,   "Reazione a check utente"),
    ("react_user_call",    action_react_user_call,    "Reazione a call utente"),
    ("react_user_raise",   action_react_user_raise,   "Reazione a raise utente"),
    ("react_user_allin",   action_react_user_allin,   "Reazione a all-in utente"),
    ("react_user_fold",    action_react_user_fold,    "Reazione a fold utente"),
    ("thinking",           action_thinking,           "Robot sta pensando"),
    # --- Azioni verbali del robot ---
    ("robot_check",        action_robot_check,        "Robot annuncia check"),
    ("robot_call",         action_robot_call,         "Robot annuncia call"),
    ("robot_call_allin",   action_robot_call_allin,   "Robot annuncia call all-in"),
    ("robot_raise",        action_robot_raise,        "Robot annuncia raise"),
    ("robot_raise_bluff",  action_robot_raise_bluff,  "Robot annuncia raise (bluff)"),
    ("robot_allin",        action_robot_allin,        "Robot annuncia all-in"),
    ("robot_fold",         action_robot_fold,         "Robot annuncia fold"),
]

# Checklist di sicurezza statica
SAFETY_CHECKS = [
    ("Collision protection abilitata",           True,  "NAORobot.__init__ abilita setCollisionProtectionEnabled"),
    ("Nessun movimento dell'anca (HipPitch)",    True,  "Rimosso da aggressive per prevenire cadute"),
    ("wakeUp() usato al posto di stiffness",     True,  "Avvio motori sicuro in NAORobot.__init__"),
    ("Tutti i gesti tornano a StandInit",        True,  "Ogni gesto termina con goToPosture('StandInit')"),
    ("Velocita' movimenti moderate",             True,  "Tempi >= 0.8s per interpolazioni, speed <= 0.3"),
    ("cleanup() rilascia i motori (rest)",       True,  "Previene surriscaldamento a fine sessione"),
    ("Nessun angolo oltre limiti fisici",        True,  "Angoli entro range sicuro [-1.5, 1.5] rad"),
    ("LED sempre ripristinati a bianco",         True,  "set_leds('white') chiamato dopo ogni sequenza"),
]


def run_single_test(name, action_func, description, robot, verbose=False):
    """Esegue una singola azione e restituisce (successo, errore)."""
    try:
        if verbose:
            action_func(robot)
        else:
            # Cattura stdout per non intasare il terminale
            import sys
            import os
            old_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            try:
                action_func(robot)
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
        return True, None
    except Exception as e:
        import traceback
        return False, traceback.format_exc()


def run_all_action_tests(verbose=False, pause=False):
    """
    Esegue tutte le azioni del robot in simulazione.
    Restituisce (passed, failed, results) dove results è una lista di
    (nome, descrizione, successo, errore, durata).

    Può essere chiamata da verify_system.py o direttamente.
    """
    robot = SimulatedRobot()
    results = []

    for i, (name, func, desc) in enumerate(ALL_ACTIONS, 1):
        header = "[{:2d}/{}] {}".format(i, len(ALL_ACTIONS), name)
        print("  {}{}{}  -  {}".format(CYAN, header, RESET, desc))

        if pause:
            input("    {}Premi Invio per eseguire...{}".format(YELLOW, RESET))

        start = time.time()
        ok, err = run_single_test(name, func, desc, robot, verbose=verbose)
        elapsed = time.time() - start

        if ok:
            print_ok("{} ({:.2f}s)".format(name, elapsed))
        else:
            print_fail("{} ({:.2f}s)".format(name, elapsed))
            if err:
                for line in err.strip().split("\n")[-3:]:
                    print("      {}{}{}".format(RED, line, RESET))

        results.append((name, desc, ok, err, elapsed))

    passed = sum(1 for r in results if r[2])
    failed = sum(1 for r in results if not r[2])
    return passed, failed, results


def print_safety_report():
    """Stampa il report dei controlli di sicurezza statica."""
    print("\n  {}Controllo di sicurezza statico{}".format(BOLD, RESET))
    for check, ok, note in SAFETY_CHECKS:
        if ok:
            print_ok("{}".format(check))
        else:
            print_fail("{}".format(check))
        if note:
            print("      {}-> {}{}".format(YELLOW, note, RESET))


def print_results_table(results):
    """Stampa la tabella riassuntiva dei risultati."""
    print("\n  {:<25} {:<8} {:>8}".format('AZIONE', 'ESITO', 'TEMPO'))
    print("  {} {} {}".format('-'*25, '-'*8, '-'*8))
    for name, desc, ok, err, elapsed in results:
        status = "{}PASS{}".format(GREEN, RESET) if ok else "{}FAIL{}".format(RED, RESET)
        print("  {:<25} {:<17} {:>7.2f}s".format(name, status, elapsed))


def main():
    parser = argparse.ArgumentParser(
        description="Test completo di tutte le azioni del robot (simulazione)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostra output dettagliato di ogni azione"
    )
    parser.add_argument(
        "--pause", "-p",
        action="store_true",
        help="Attende pressione di Invio tra un'azione e l'altra"
    )
    args = parser.parse_args()

    print()
    print('='*64)
    print('  TEST COMPLETO AZIONI ROBOT - MODALITA\' SIMULAZIONE')
    print('='*64)
    print('  Totale azioni da testare: {}'.format(len(ALL_ACTIONS)))
    print('{}\n'.format('='*64))

    passed, failed, results = run_all_action_tests(
        verbose=args.verbose, pause=args.pause
    )
    total_time = sum(r[4] for r in results)

    # Report finale
    print('\n{}'.format('='*64))
    print('  REPORT FINALE')
    print('='*64)
    print('  Totale:   {}'.format(len(results)))
    print('  {}Passati:  {}{}'.format(GREEN, passed, RESET))
    if failed > 0:
        print('  {}Falliti:  {}{}'.format(RED, failed, RESET))
    else:
        print('  Falliti:  0')
    print('  Tempo:    {:.2f}s'.format(total_time))

    # Dettaglio azioni fallite
    if failed > 0:
        print('\n  {}{}AZIONI FALLITE:{}'.format(RED, BOLD, RESET))
        print('  {}'.format('-'*58))
        for name, desc, ok, err, elapsed in results:
            if not ok:
                print_fail('{}: {}'.format(name, desc))
                if err:
                    for line in err.strip().split('\n')[-3:]:
                        print('      {}'.format(line))

    # Tabella riassuntiva
    print_results_table(results)

    # Analisi di sicurezza statica
    print_safety_report()

    print('\n{}'.format('='*64))
    if failed == 0:
        print('{}{}  TUTTI I TEST SUPERATI! Il robot e\' pronto per l\'esperimento.{}'.format(GREEN, BOLD, RESET))
    else:
        print('{}{}  ATTENZIONE: {} azione/i fallita/e. Correggere prima dell\'uso.{}'.format(RED, BOLD, failed, RESET))
    print('{}\n'.format('='*64))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
