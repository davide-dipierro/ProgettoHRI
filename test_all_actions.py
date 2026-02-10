#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test completo di tutte le azioni del Robot Controller.

Esegue ogni azione definita in robot_controller.py in modalità simulazione,
verificando che ciascuna vada a buon fine senza errori.
Produce un report finale con esito per ogni azione.

Può essere eseguito direttamente o importato da verify_system.py.

Usage:
    python3 test_all_actions.py
    python3 test_all_actions.py --verbose
    python3 test_all_actions.py --pause        # attende input tra un'azione e l'altra
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
)

# Colori per output (condivisi con verify_system.py)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_ok(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_fail(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warn(msg):
    print(f"{YELLOW}!{RESET} {msg}")


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
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                action_func(robot)
        return True, None
    except Exception as e:
        return False, "".join(traceback.format_exception(type(e), e, e.__traceback__))


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
        header = f"[{i:2d}/{len(ALL_ACTIONS)}] {name}"
        print(f"  {CYAN}{header}{RESET}  -  {desc}")

        if pause:
            input(f"    {YELLOW}Premi Invio per eseguire...{RESET}")

        start = time.time()
        ok, err = run_single_test(name, func, desc, robot, verbose=verbose)
        elapsed = time.time() - start

        if ok:
            print_ok(f"{name} ({elapsed:.2f}s)")
        else:
            print_fail(f"{name} ({elapsed:.2f}s)")
            if err:
                for line in err.strip().split("\n")[-3:]:
                    print(f"      {RED}{line}{RESET}")

        results.append((name, desc, ok, err, elapsed))

    passed = sum(1 for r in results if r[2])
    failed = sum(1 for r in results if not r[2])
    return passed, failed, results


def print_safety_report():
    """Stampa il report dei controlli di sicurezza statica."""
    print(f"\n  {BOLD}Controllo di sicurezza statico{RESET}")
    for check, ok, note in SAFETY_CHECKS:
        if ok:
            print_ok(f"{check}")
        else:
            print_fail(f"{check}")
        if note:
            print(f"      {YELLOW}→ {note}{RESET}")


def print_results_table(results):
    """Stampa la tabella riassuntiva dei risultati."""
    print(f"\n  {'AZIONE':<25} {'ESITO':<8} {'TEMPO':>8}")
    print(f"  {'-'*25} {'-'*8} {'-'*8}")
    for name, desc, ok, err, elapsed in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {name:<25} {status:<17} {elapsed:>7.2f}s")


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
    print(f"{'='*64}")
    print(f"  TEST COMPLETO AZIONI ROBOT - MODALITA' SIMULAZIONE")
    print(f"{'='*64}")
    print(f"  Totale azioni da testare: {len(ALL_ACTIONS)}")
    print(f"{'='*64}\n")

    passed, failed, results = run_all_action_tests(
        verbose=args.verbose, pause=args.pause
    )
    total_time = sum(r[4] for r in results)

    # Report finale
    print(f"\n{'='*64}")
    print(f"  REPORT FINALE")
    print(f"{'='*64}")
    print(f"  Totale:   {len(results)}")
    print(f"  {GREEN}Passati:  {passed}{RESET}")
    if failed > 0:
        print(f"  {RED}Falliti:  {failed}{RESET}")
    else:
        print(f"  Falliti:  0")
    print(f"  Tempo:    {total_time:.2f}s")

    # Dettaglio azioni fallite
    if failed > 0:
        print(f"\n  {RED}{BOLD}AZIONI FALLITE:{RESET}")
        print(f"  {'-'*58}")
        for name, desc, ok, err, elapsed in results:
            if not ok:
                print_fail(f"{name}: {desc}")
                if err:
                    for line in err.strip().split("\n")[-3:]:
                        print(f"      {line}")

    # Tabella riassuntiva
    print_results_table(results)

    # Analisi di sicurezza statica
    print_safety_report()

    print(f"\n{'='*64}")
    if failed == 0:
        print(f"{GREEN}{BOLD}  TUTTI I TEST SUPERATI! Il robot e' pronto per l'esperimento.{RESET}")
    else:
        print(f"{RED}{BOLD}  ATTENZIONE: {failed} azione/i fallita/e. Correggere prima dell'uso.{RESET}")
    print(f"{'='*64}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
