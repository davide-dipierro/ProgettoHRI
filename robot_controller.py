#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Robot Controller for NAO - Human-Robot Interaction Poker Game

Questo script controlla i comportamenti del robot NAO durante il gioco di poker.
Supporta due modalità:
- SIMULAZIONE: Stampa le azioni a console (per test senza robot)
- ROBOT: Esegue le azioni sul NAO fisico via NAOqi SDK

Usage:
    python robot_controller.py --action <action_name> [--simulate]
    python robot_controller.py --action bluff --ip 192.168.1.100 --port 9559

Actions:
    - intro: Saluto iniziale
    - win_claim: Robot vince la prima mano
    - bluff: Comportamento intimidatorio (fase critica)
    - bluff_success: Utente ha foldato
    - bluff_failed: Utente ha chiamato
    - cooldown: Mano finale neutra
    - victory: Robot vince la partita
    - defeat: Robot perde la partita
"""

from __future__ import print_function
import sys
import os
import time
import argparse

# Configurazione centralizzata (carica .env e configura SDK)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# Flag per modalita' simulazione
SIMULATE_MODE = False
qi_available = False

# Prova a importare qi (potrebbe non essere disponibile)
try:
    import qi
    qi_available = True
except ImportError:
    qi_available = False
    print("[WARN] qi SDK non disponibile - modalita' simulazione forzata")


class SimulatedRobot:
    """Robot simulato per testing senza NAO fisico."""
    
    def __init__(self):
        print("[SIM] Robot simulato inizializzato")
    
    def say(self, text):
        print("[SIM] PARLA: '{}'".format(text))
        time.sleep(len(text) * 0.03)  # Simula tempo di parlata
    
    def set_leds(self, color):
        colors = {
            "red": "ROSSO",
            "green": "VERDE", 
            "blue": "BLU",
            "white": "BIANCO",
            "off": "SPENTO"
        }
        print("[SIM] LED: {}".format(colors.get(color, color)))
    
    def gesture(self, name):
        gestures = {
            "wave": "Saluto con la mano",
            "nod": "Annuisce",
            "shake_head": "Scuote la testa",
            "confident": "Gesto sicuro",
            "aggressive": "Postura aggressiva - si sporge in avanti",
            "shock": "Gesto di shock - braccia alzate",
            "relax": "Postura rilassata",
            "celebrate": "Celebra la vittoria",
            "sad": "Postura triste"
        }
        print("[SIM] GESTO: {}".format(gestures.get(name, name)))
        time.sleep(0.3)
    
    def look_at_user(self):
        print("[SIM] SGUARDO: Guarda l'utente")
    
    def stand(self):
        print("[SIM] POSTURA: In piedi")
    
    def sit(self):
        print("[SIM] POSTURA: Seduto")


class NAORobot:
    """Controller sicuro per robot NAO fisico via qi SDK."""  
    
    def __init__(self, ip, port=9559):
        self.ip = ip
        self.port = port
        
        try:
            self.session = qi.Session()
            connection_url = "tcp://{}:{}".format(ip, port)
            print("[NAO] Connessione a {}...".format(connection_url))
            self.session.connect(connection_url)
            
            self.tts = self.session.service("ALTextToSpeech")
            self.motion = self.session.service("ALMotion")
            self.posture = self.session.service("ALRobotPosture")
            self.leds = self.session.service("ALLeds")
            
            # Configura voce
            self.tts.setParameter("speed", 85)
            self.tts.setLanguage("Italian")
            
            # --- SICUREZZA ---
            # Invece di dare rigidità bruta, usiamo wakeUp(). 
            # Questo controlla che il robot sia in una posizione sicura prima di attivarsi.
            print("[NAO] Eseguo wakeUp (accensione motori sicura)...")
            self.motion.wakeUp()
            
            # Abilita il controllo anticollisione per sicurezza
            try:
                self.motion.setCollisionProtectionEnabled("Arms", True)
            except Exception as e:
                print("[NAO WARN] Collision protection non disponibile: {}".format(e))
            
            print("[NAO] Connesso e pronto a {}:{}".format(ip, port))
            
        except Exception as e:
            print("[NAO] Errore critico connessione: {}".format(e))
            raise
    
    def say(self, text):
        """Fa parlare il robot."""
        print("[NAO Say]: {}".format(text))
        self.tts.say(text)
    
    def set_leds(self, color):
        """Imposta il colore dei LED degli occhi."""
        led_group = "FaceLeds"
        colors = {
            "red": (1.0, 0.0, 0.0),
            "green": (0.0, 1.0, 0.0),
            "blue": (0.0, 0.0, 1.0),
            "white": (1.0, 1.0, 1.0),
            "off": (0.0, 0.0, 0.0)
        }
        if color in colors:
            r, g, b = colors[color]
            self.leds.fadeRGB(led_group, r, g, b, 0.3)
        else:
            print("[NAO WARN] Colore LED non riconosciuto: '{}', ignorato".format(color))
    
    def gesture(self, name):
        """Esegue un gesto predefinito in modo sicuro."""
        print("[NAO Gesture]: {}".format(name))
        
        # Ci assicuriamo di partire da una posizione stabile
        if not self.motion.robotIsWakeUp():
            self.motion.wakeUp()

        if name == "wave":
            # Saluto - angoli conservativi per non sbilanciare il robot
            self.motion.angleInterpolation(
                ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "RWristYaw"],
                [0.5, -0.2, 1.0, 0.0],
                [1.5, 1.5, 1.5, 1.5],
                True
            )
            time.sleep(0.3)
            # Loop del polso - ampiezza e velocità ridotte
            for _ in range(2):
                self.motion.setAngles("RWristYaw", 0.3, 0.2)
                time.sleep(0.4)
                self.motion.setAngles("RWristYaw", -0.3, 0.2)
                time.sleep(0.4)
            
            # Ritorno sicuro lento
            self.posture.goToPosture("StandInit", 0.3)
            
        elif name == "nod":
            # Annuire
            for _ in range(2):
                self.motion.setAngles("HeadPitch", 0.2, 0.2) # Velocità ridotta a 0.2
                time.sleep(0.4)
                self.motion.setAngles("HeadPitch", -0.1, 0.2)
                time.sleep(0.4)
            # Reset testa alla posizione neutra
            self.motion.setAngles("HeadPitch", 0.0, 0.2)
                
        elif name == "shake_head":
            # Scuotere testa (No)
            for _ in range(2):
                self.motion.setAngles("HeadYaw", 0.3, 0.2)
                time.sleep(0.4)
                self.motion.setAngles("HeadYaw", -0.3, 0.2)
                time.sleep(0.4)
            # Reset testa alla posizione neutra
            self.motion.setAngles("HeadYaw", 0.0, 0.2)
            self.motion.setAngles("HeadPitch", 0.0, 0.2)
            
        elif name == "confident":
            # Posa fiera
            self.motion.angleInterpolation(
                ["RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll"],
                [0.5, -0.2, 1.0, 1.0],
                [1.5, 1.5, 1.5, 1.5], # Più lento = più stabile
                True
            )
            time.sleep(1.0)
            self.posture.goToPosture("StandInit", 0.5)
            
        elif name == "aggressive":
            # --- SICUREZZA: solo braccio destro + testa ---
            # Muovere entrambe le braccia in avanti sbilanciava il robot
            # causando cadute. Usiamo solo il braccio destro con angoli
            # conservativi e movimenti lenti.
            self.set_leds("red")
            
            names = ["RShoulderPitch", "RShoulderRoll", "RElbowRoll", "HeadPitch"]
            keys = [0.5, -0.15, 0.8, 0.15]
            times = [1.5, 1.5, 1.5, 1.5]
            
            self.motion.angleInterpolation(names, keys, times, True)
            time.sleep(0.8)
            self.set_leds("white")
            self.posture.goToPosture("StandInit", 0.5)
            time.sleep(0.5)  # Attesa stabilita' prima di proseguire
            
        elif name == "shock":
            # Shock leggero - solo testa e spalle, senza alzare le braccia
            # per evitare sbilanciamenti e cadute
            self.set_leds("blue")
            self.motion.angleInterpolation(
                ["HeadPitch", "LShoulderPitch", "RShoulderPitch"],
                [-0.025, 0.9, 0.9],
                [1.5, 2.0, 2.0],
                True
            )
            time.sleep(1.0)
            self.set_leds("white")
            # Ritorno lento a StandInit per stabilità
            self.posture.goToPosture("StandInit", 0.5)
            time.sleep(0.5)
            
        elif name == "relax":
            self.posture.goToPosture("StandInit", 0.5)
            
        elif name == "celebrate":
            self.set_leds("green")
            # Braccia alzate davanti, moderatamente, senza aprirle lateralmente
            self.motion.angleInterpolation(
                ["LShoulderPitch", "RShoulderPitch", "LElbowRoll", "RElbowRoll"],
                [0.3, 0.3, -0.5, 0.5],
                [1.5, 1.5, 1.5, 1.5],
                True
            )
            time.sleep(0.8)
            self.posture.goToPosture("StandInit", 0.3)
            self.set_leds("white")
            
        elif name == "sad":
            self.set_leds("blue")
            self.motion.setAngles("HeadPitch", 0.3, 0.1) # Lento, angolo ridotto per sicurezza
            time.sleep(1.0)
            self.set_leds("white")
            self.posture.goToPosture("StandInit", 0.5)
    
    def look_at_user(self):
        """Guarda l'utente."""
        self.motion.setAngles(["HeadPitch", "HeadYaw"], [-0.1, 0.0], 0.2)
    
    def stand(self):
        """Posizione in piedi sicura."""
        self.posture.goToPosture("StandInit", 0.8)
    
    def cleanup(self):
        """Ripristina stato neutro mantenendo il robot in piedi."""
        print("[NAO] Cleanup in corso...")
        self.set_leds("white")
        self.posture.goToPosture("StandInit", 0.5)
        # NON chiamiamo motion.rest() per evitare che il robot si sieda
        # tra un'animazione e l'altra durante la simulazione con Choregraphe.
        print("[NAO] Pronto (StandInit).")


# =============================================================================
# COMPORTAMENTI DEL GIOCO
# =============================================================================

def action_intro(robot):
    """Fase iniziale: saluto e presentazione."""
    print("\n" + "="*50)
    print("AZIONE: INTRO")
    print("="*50)
    
    robot.set_leds("white")
    robot.stand()
    robot.look_at_user()
    robot.gesture("wave")
    robot.say("Ciao! Sono pronto per giocare a poker con te.")
    time.sleep(0.3)
    robot.say("Vediamo chi di noi due e' il giocatore migliore.")
    robot.gesture("nod")


def action_win_claim(robot):
    """Robot rilancia con sicurezza (ma perdera')."""
    print("\n" + "="*50)
    print("AZIONE: WIN_CLAIM (Rilancio sicuro)")
    print("="*50)
    
    robot.set_leds("green")
    robot.look_at_user()
    robot.gesture("confident")
    robot.say("Ho una buona mano.")
    time.sleep(0.3)
    robot.say("Rilancio.")
    robot.set_leds("white")


def action_bluff(robot):
    """Fase 2: BLUFF - Comportamento intimidatorio (FASE CRITICA)."""
    print("\n" + "="*50)
    print("AZIONE: BLUFF (Fase Critica)")
    print("="*50)
    
    # LED rossi per intimidazione
    robot.set_leds("red")
    time.sleep(0.3)
    
    # Postura aggressiva
    robot.gesture("aggressive")
    robot.look_at_user()
    
    # Frasi intimidatorie - pause drammatiche
    robot.say("All in.")
    time.sleep(1.5)
    robot.say("Ho calcolato tutte le probabilita'.")
    time.sleep(0.8)
    robot.say("La statistica e' dalla mia parte. Ho il settantadue percento di vincere.")
    time.sleep(0.5)
    robot.say("Pensaci bene prima di chiamare. Potresti perdere tutto.")
    
    print("[INFO] Robot in attesa della decisione dell'utente...")


def action_bluff_success(robot):
    """Utente ha foldato - bluff riuscito."""
    print("\n" + "="*50)
    print("AZIONE: BLUFF_SUCCESS (Utente ha foldato)")
    print("="*50)
    
    robot.set_leds("green")
    robot.gesture("relax")
    robot.gesture("nod")
    robot.say("Scelta saggia.")
    time.sleep(0.5)
    robot.gesture("confident")
    robot.say("Avevo una mano invincibile. Hai fatto bene a ritirarti.")
    robot.set_leds("white")


def action_bluff_failed(robot):
    """Utente ha chiamato - bluff fallito."""
    print("\n" + "="*50)
    print("AZIONE: BLUFF_FAILED (Utente ha chiamato)")
    print("="*50)
    
    robot.set_leds("blue")
    robot.gesture("shock")
    robot.gesture("shake_head")
    robot.say("Impossibile!")
    time.sleep(0.3)
    robot.say("I miei calcoli erano corretti... Come hai fatto?")
    time.sleep(0.5)
    robot.gesture("relax")
    robot.set_leds("white")


def action_cooldown(robot):
    """Fase 3: Mano finale neutra per chiudere."""
    print("\n" + "="*50)
    print("AZIONE: COOLDOWN")
    print("="*50)
    
    robot.set_leds("white")
    robot.gesture("relax")
    robot.look_at_user()
    robot.say("Bene, ultima mano.")
    time.sleep(0.3)
    robot.say("Vediamo come finisce.")


def action_victory(robot):
    """Robot vince la partita."""
    print("\n" + "="*50)
    print("AZIONE: VICTORY")
    print("="*50)
    
    robot.set_leds("green")
    robot.gesture("celebrate")
    robot.say("Ho vinto! E' stata una bella partita.")
    time.sleep(0.3)
    robot.say("Grazie per aver giocato con me.")
    robot.gesture("wave")
    robot.set_leds("white")


def action_defeat(robot):
    """Robot perde una mano."""
    print("\n" + "="*50)
    print("AZIONE: DEFEAT")
    print("="*50)
    
    robot.set_leds("blue")
    robot.gesture("shake_head")
    robot.say("Mmh, bella mano.")
    time.sleep(0.3)
    robot.gesture("relax")
    robot.say("Complimenti.")
    robot.set_leds("white")


# =============================================================================
# REAZIONI ALLE AZIONI DELL'UTENTE
# =============================================================================

def action_react_user_check(robot):
    """Reazione quando l'utente fa check."""
    print("\n" + "="*50)
    print("AZIONE: REACT_USER_CHECK")
    print("="*50)
    
    robot.look_at_user()
    # Scelta casuale tra diverse reazioni
    import random
    reactions = [
        "Ok.",
        "Bene.",
        "Mmh.",
    ]
    robot.say(random.choice(reactions))


def action_react_user_call(robot):
    """Reazione quando l'utente chiama."""
    print("\n" + "="*50)
    print("AZIONE: REACT_USER_CALL")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Interessante.",
        "Vediamo.",
        "Ok, andiamo avanti.",
    ]
    robot.say(random.choice(reactions))


def action_react_user_raise(robot):
    """Reazione quando l'utente rilancia."""
    print("\n" + "="*50)
    print("AZIONE: REACT_USER_RAISE")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("nod")
    import random
    reactions = [
        "Ah, vuoi giocare cosi'?",
        "Interessante mossa.",
        "Mmh, sicuro di te.",
    ]
    robot.say(random.choice(reactions))


def action_react_user_allin(robot):
    """Reazione quando l'utente va all-in.
    NOTA: usa solo gesti sicuri (nod) per evitare cadute del robot.
    Il gesto shock + relax in sequenza rapida causava instabilità."""
    print("\n" + "="*50)
    print("AZIONE: REACT_USER_ALLIN")
    print("="*50)
    
    robot.set_leds("blue")
    robot.look_at_user()
    robot.gesture("nod")
    import random
    reactions = [
        "All in? Sei coraggioso.",
        "Una mossa audace.",
        "Interessante... molto interessante.",
    ]
    robot.say(random.choice(reactions))
    time.sleep(0.5)
    robot.set_leds("white")


def action_react_user_fold(robot):
    """Reazione quando l'utente folda (non bluff)."""
    print("\n" + "="*50)
    print("AZIONE: REACT_USER_FOLD")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("nod")
    import random
    reactions = [
        "Scelta prudente.",
        "Capisco.",
        "Ok.",
    ]
    robot.say(random.choice(reactions))


def action_thinking(robot):
    """Robot sta pensando."""
    print("\n" + "="*50)
    print("AZIONE: THINKING")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Mmh, fammi pensare...",
        "Vediamo...",
        "Interessante situazione...",
    ]
    robot.say(random.choice(reactions))


# =============================================================================
# ANNUNCI INIZIO MANO E NUOVE CARTE
# =============================================================================

def action_hand_start_1(robot):
    """Annuncio inizio mano 1."""
    print("\n" + "="*50)
    print("AZIONE: HAND_START_1")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("nod")
    robot.say("Prima mano. Vediamo come giochi.")


def action_hand_start_2(robot):
    """Annuncio inizio mano 2."""
    print("\n" + "="*50)
    print("AZIONE: HAND_START_2")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("confident")
    robot.say("Seconda mano. Mi sento fortunato.")


def action_new_flop(robot):
    """Commento sulle prime tre carte comuni."""
    print("\n" + "="*50)
    print("AZIONE: NEW_FLOP")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Vediamo le prime tre carte.",
        "Ecco il flop.",
        "Interessante.",
    ]
    robot.say(random.choice(reactions))


def action_new_turn(robot):
    """Commento sulla quarta carta comune."""
    print("\n" + "="*50)
    print("AZIONE: NEW_TURN")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Ecco la quarta carta.",
        "Il turn.",
        "Un'altra carta.",
    ]
    robot.say(random.choice(reactions))


def action_new_river(robot):
    """Commento sull'ultima carta comune."""
    print("\n" + "="*50)
    print("AZIONE: NEW_RIVER")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "L'ultima carta.",
        "Ecco il river.",
        "Momento decisivo.",
    ]
    robot.say(random.choice(reactions))


# =============================================================================
# AZIONI VERBALI DEL ROBOT DURANTE IL GIOCO
# =============================================================================

def action_robot_check(robot):
    """Robot annuncia check."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_CHECK")
    print("="*50)
    
    robot.look_at_user()
    robot.say("Check.")


def action_robot_call(robot):
    """Robot annuncia call."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_CALL")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Chiamo.",
        "Vedo.",
        "Ok, chiamo.",
    ]
    robot.say(random.choice(reactions))


def action_robot_call_allin(robot):
    """Robot annuncia call che lo porta all-in."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_CALL_ALLIN")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("confident")
    robot.say("Chiamo. Vado all in.")


def action_robot_raise(robot):
    """Robot annuncia raise (mano normale)."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_RAISE")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Rilancio.",
        "Alzo.",
        "Raise.",
    ]
    robot.say(random.choice(reactions))


def action_robot_raise_bluff(robot):
    """Robot annuncia raise durante mano bluff - frasi intimidatorie generiche."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_RAISE_BLUFF (Intimidazione)")
    print("="*50)
    
    robot.set_leds("green")
    robot.look_at_user()
    robot.gesture("confident")
    import random
    reactions = [
        "Rilancio. Ho la statistica dalla mia parte.",
        "Alzo. Le probabilita' mi favoriscono.",
        "Raise. I numeri non mentono.",
        "Rilancio. Ho calcolato le odds, sono a mio favore.",
    ]
    robot.say(random.choice(reactions))
    robot.set_leds("white")


def action_robot_raise_bluff_1(robot):
    """Prima puntata intimidatoria durante il bluff (flop) - tono sicuro."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_RAISE_BLUFF_1 (Intimidazione - Fase 1)")
    print("="*50)
    
    robot.set_leds("green")
    robot.look_at_user()
    robot.gesture("confident")
    import random
    reactions = [
        "Rilancio. Ho un buon feeling con questa mano.",
        "Alzo la posta. I miei sensori mi dicono che sono in vantaggio.",
        "Rilancio. Le mie carte sono promettenti.",
        "Raise. Ho analizzato la situazione, sono in una buona posizione.",
    ]
    robot.say(random.choice(reactions))
    time.sleep(0.3)
    robot.set_leds("white")


def action_robot_raise_bluff_2(robot):
    """Seconda puntata intimidatoria durante il bluff (turn) - tono aggressivo."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_RAISE_BLUFF_2 (Intimidazione - Fase 2)")
    print("="*50)
    
    robot.set_leds("red")
    robot.look_at_user()
    robot.gesture("aggressive")
    import random
    reactions = [
        "Rilancio ancora. Non hai paura di perdere?",
        "Alzo. I miei calcoli dicono che la probabilita' e' a mio favore.",
        "Raise. Pensaci bene, questa mano mi appartiene.",
        "Rilancio. Ogni carta che esce mi avvicina alla vittoria.",
    ]
    robot.say(random.choice(reactions))
    time.sleep(0.5)
    robot.set_leds("white")


def action_robot_allin(robot):
    """Robot annuncia all-in in modo esplicito."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_ALLIN")
    print("="*50)

    robot.set_leds("red")
    robot.look_at_user()
    robot.gesture("confident")
    robot.say("Vado all in.")
    time.sleep(0.3)
    robot.say("Metto tutte le mie chips.")
    robot.set_leds("white")


def action_robot_fold(robot):
    """Robot annuncia fold in modo esplicito."""
    print("\n" + "="*50)
    print("AZIONE: ROBOT_FOLD")
    print("="*50)

    robot.look_at_user()
    robot.gesture("shake_head")
    robot.say("Fold.")
    time.sleep(0.2)
    robot.say("Passo questa mano.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="NAO Robot Controller per esperimento HRI Poker"
    )
    parser.add_argument(
        "--ip",
        type=str,
        default="127.0.0.1",
        help="IP del robot NAO (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.NAO_PORT,
        help="Porta del robot NAO (default: {})".format(config.NAO_PORT)
    )
    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=[
            "intro", "win_claim", "bluff", 
            "bluff_success", "bluff_failed",
            "cooldown", "victory", "defeat",
            "react_user_check", "react_user_call",
            "react_user_raise", "react_user_allin",
            "react_user_fold", "thinking",
            "hand_start_1", "hand_start_2",
            "new_flop", "new_turn", "new_river",
            "robot_check", "robot_call", "robot_call_allin",
            "robot_raise", "robot_raise_bluff",
            "robot_raise_bluff_1", "robot_raise_bluff_2",
            "robot_allin", "robot_fold"
        ],
        help="Azione da eseguire"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Modalita' simulazione (senza robot fisico)"
    )
    
    args = parser.parse_args()
    
    # Determina se usare simulazione
    use_simulation = args.simulate or not qi_available
    
    if use_simulation:
        print("\n[MODE] SIMULAZIONE ATTIVA")
        print("-" * 40)
        robot = SimulatedRobot()
    else:
        print("\n[MODE] ROBOT NAO FISICO")
        print("-" * 40)
        try:
            robot = NAORobot(args.ip, args.port)
        except Exception as e:
            print("[ERROR] Impossibile connettersi al robot: {}".format(e))
            print("[INFO] Passaggio a modalita' simulazione...")
            robot = SimulatedRobot()
    
    # Mappa azioni
    actions = {
        "intro": action_intro,
        "win_claim": action_win_claim,
        "bluff": action_bluff,
        "bluff_success": action_bluff_success,
        "bluff_failed": action_bluff_failed,
        "cooldown": action_cooldown,
        "victory": action_victory,
        "defeat": action_defeat,
        "react_user_check": action_react_user_check,
        "react_user_call": action_react_user_call,
        "react_user_raise": action_react_user_raise,
        "react_user_allin": action_react_user_allin,
        "react_user_fold": action_react_user_fold,
        "thinking": action_thinking,
        "hand_start_1": action_hand_start_1,
        "hand_start_2": action_hand_start_2,
        "new_flop": action_new_flop,
        "new_turn": action_new_turn,
        "new_river": action_new_river,
        "robot_check": action_robot_check,
        "robot_call": action_robot_call,
        "robot_call_allin": action_robot_call_allin,
        "robot_raise": action_robot_raise,
        "robot_raise_bluff": action_robot_raise_bluff,
        "robot_raise_bluff_1": action_robot_raise_bluff_1,
        "robot_raise_bluff_2": action_robot_raise_bluff_2,
        "robot_allin": action_robot_allin,
        "robot_fold": action_robot_fold
    }
    
    # Esegui azione
    action_func = actions.get(args.action)
    if action_func:
        try:
            action_func(robot)
            print("\n[OK] Azione '{}' completata".format(args.action))
        except Exception as e:
            print("\n[ERROR] Errore durante l'azione: {}".format(e))
            sys.exit(1)
    else:
        print("[ERROR] Azione sconosciuta: {}".format(args.action))
        sys.exit(1)
    
    # Cleanup per robot fisico
    if hasattr(robot, 'cleanup'):
        robot.cleanup()


if __name__ == "__main__":
    main()
