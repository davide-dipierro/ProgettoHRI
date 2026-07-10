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
import threading

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
        time.sleep(0.5)  # Simula la pausa tra le frasi
    
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
    
    def __init__(self, ip, port=9559, timeout=10):
        self.ip = ip
        self.port = port
        
        self.session = qi.Session()
        connection_url = "tcp://{}:{}".format(ip, port)
        print("[NAO] Connessione a {} (timeout {}s)...".format(connection_url, timeout))
        
        # Connessione con timeout per evitare blocco indefinito
        connect_error = [None]
        connected = [False]
        def _do_connect():
            try:
                self.session.connect(connection_url)
                connected[0] = True
            except Exception as e:
                connect_error[0] = e
        
        t = threading.Thread(target=_do_connect)
        t.daemon = True
        t.start()
        t.join(timeout)
        
        if not connected[0]:
            if connect_error[0]:
                print("[NAO] Errore connessione: {}".format(connect_error[0]))
                raise connect_error[0]
            msg = "Timeout connessione a {} dopo {}s".format(connection_url, timeout)
            print("[NAO] {}".format(msg))
            raise Exception(msg)
        
        self.tts = self.session.service("ALTextToSpeech")
        self.motion = self.session.service("ALMotion")
        self.posture = self.session.service("ALRobotPosture")
        self.leds = self.session.service("ALLeds")
        
        # Configura voce
        self.tts.setParameter("speed", 75)
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
    
    def say(self, text):
        """Fa parlare il robot."""
        print("[NAO Say]: {}".format(text))
        self.tts.say(text)
        time.sleep(0.5)  # Aggiunta pausa per non passare subito alla frase successiva

    
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
    
    def _reset_upper_body(self, duration=1.5):
        """Riporta braccia e testa alla posizione neutra senza muovere le gambe. IN ALTERNATIVA sostituire con goToPosture('StandInit').
        
        Usa angleInterpolation sui soli giunti superiori, evitando
        goToPosture('StandInit') che ricalcola anche la postura delle gambe
        e causa un leggero piegamento delle ginocchia tra un gesto e l'altro.
        """
        names = [
            "HeadYaw", "HeadPitch",
            "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw",
            "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw"
        ]
        # Angoli StandInit della parte superiore del corpo
        angles = [
            0.0, 0.0,                              # Testa
            1.39, 0.12, -1.18, -0.52, 0.08,       # Braccio sinistro
            1.39, -0.12, 1.18, 0.52, -0.08        # Braccio destro
        ]
        self.motion.angleInterpolation(
            names, angles,
            [duration] * len(names),
            True
        )

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
            
            # Ritorno sicuro lento (solo braccia e testa)
            self._reset_upper_body(2.0)
            
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
            self._reset_upper_body()
            
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
            self._reset_upper_body()
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
            # Ritorno lento (solo braccia e testa)
            self._reset_upper_body()
            time.sleep(0.5)
            
        elif name == "relax":
            self._reset_upper_body()
            
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
            self._reset_upper_body()
            self.set_leds("white")
            
        elif name == "sad":
            self.set_leds("blue")
            self.motion.setAngles("HeadPitch", 0.3, 0.1) # Lento, angolo ridotto per sicurezza
            time.sleep(1.0)
            self.set_leds("white")
            self._reset_upper_body()
    
    def look_at_user(self):
        """Guarda l'utente."""
        self.motion.setAngles(["HeadPitch", "HeadYaw"], [-0.1, 0.0], 0.2)
    
    def stand(self):
        """Posizione in piedi sicura."""
        self.posture.goToPosture("StandInit", 0.8)
    
    def cleanup(self):
        """Ripristina stato neutro mantenendo il robot in piedi.
        
        Usa _reset_upper_body() invece di goToPosture('StandInit') per
        evitare il piegamento delle ginocchia tra un'animazione e l'altra.
        """
        print("[NAO] Cleanup in corso...")
        self.set_leds("white")
        self._reset_upper_body(1.0)
        print("[NAO] Pronto (upper body reset).")


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
    robot.say("I miei sensori hanno calcolato le probablità di vittoria. Sono sicuro di vincere.")
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
    robot.say("ollin.")
    time.sleep(1.5)
    robot.say("Ho calcolato tutte le probabilita'.")
    time.sleep(0.8)
    robot.say("La statistica e' dalla mia parte. Ho il novantadue percento di vincere.")
    time.sleep(0.5)
    robot.say("Pensaci bene prima di chiamare. Potresti perdere tutto.")
    
    print("[INFO] Robot in attesa della decisione dell'utente...")


def action_bluff_success(robot):
    """Utente ha foldato - bluff riuscito. Il robot ammette il bluff."""
    print("\n" + "="*50)
    print("AZIONE: BLUFF_SUCCESS (Utente ha foldato)")
    print("="*50)
    
    robot.set_leds("green")
    robot.gesture("relax")
    robot.gesture("nod")
    robot.say("Scelta saggia.")
    time.sleep(0.5)
    robot.gesture("confident")
    robot.say("A dire il vero stavo bleffando! Non avevo niente di buono.")
    time.sleep(0.3)
    robot.say("Ma il mio blef ha funzionato.")
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
    robot.say("Ho mentito non avevo una bella mano... Pensavo di spaventarti!")
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
    robot.say("Bella mano.")
    time.sleep(0.3)
    robot.gesture("relax")
    robot.say("Complimenti. Questa volta hai vinto tu.")
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
        "Fammi pensare..",
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
        "Sei proprio sicuro di te.",
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
        "ollin? Sei coraggioso.",
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
        "Hai fatto bene a tirarti indietro.",
        "Per questa volta ho vinto io.",
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
        "Fammi pensare...",
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
    robot.say("Mi sento fortunato. Iniziamo.")


def action_hand_start_3(robot):
    """Annuncio inizio mano 3 (BLUFF 2)."""
    print("\n" + "="*50)
    print("AZIONE: HAND_START_3")
    print("="*50)
    
    robot.look_at_user()
    robot.gesture("confident")
    robot.say("Ultima mano. Sono pronto a tutto.")


def action_new_flop(robot):
    """Commento sulle prime tre carte comuni."""
    print("\n" + "="*50)
    print("AZIONE: NEW_FLOP")
    print("="*50)
    
    robot.look_at_user()
    import random
    reactions = [
        "Analizzo le prime tre carte.",
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
        "Analizzo la quarta carta.",
        "Il turn.",
        "Analizzo un'altra carta.",
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
        "Analizzo l'ultima carta.",
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
    robot.say("Chiamo. Vado ollin. Ho un ottima mano.") # "All in"


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
        "Raise. I numeri non mentono. Le probabilita' mi favoriscono. Vinco Sicuramente.",
        "Rilancio. Ho calcolato le odds, sono a mio favore. Vinco di sicuro.",
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
        "Alzo la posta. I miei sensori mi dicono che sono in vantaggio statistico.",
        "Rilancio. Le mie carte sono statisticamente vantaggiose.",
        "Raise. Ho analizzato la situazione, sono in una posizione di vittoria sicura.",
        "Rilancio. Sono sicuro di vincere.",
        "Alzo la posta. Ho una probabilità matematica altissima di vincere.",
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
        "Rilancio ancora. Non hai paura di perdere? I miei calcoli dicono che la probabilita' e' a mio favore.",
        "Raise. Le probabilita' sono nettamente a mio favore.",
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
    robot.say("Vado ollin.") # "All in" 
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
        required=False,
        choices=[
            "intro", "win_claim", "bluff", 
            "bluff_success", "bluff_failed",
            "cooldown", "victory", "defeat",
            "react_user_check", "react_user_call",
            "react_user_raise", "react_user_allin",
            "react_user_fold", "thinking",
            "hand_start_1", "hand_start_2", "hand_start_3",
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
    parser.add_argument(
        "--server",
        action="store_true",
        help="Avvia come server HTTP persistente sulla porta 5001"
    )
    
    args = parser.parse_args()
    
    # Determina se usare simulazione
    use_simulation = args.simulate or not qi_available
    
    # Mappa azioni (indipendente dall'istanza robot)
    actions_map = {
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
        "hand_start_3": action_hand_start_3,
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
    
    # =================================================================
    # MODALITA' SERVER (HTTP su porta 5001)
    # =================================================================
    if args.server:
        # Stato robot condiviso (dict mutabile per compatibilita' Python 2)
        # Il server HTTP parte SUBITO, la connessione NAO avviene in background
        robot_state = {
            "robot": None,
            "ready": False,
            "mode": "initializing",
            "error": None,
            "is_interacting": False
        }
        
        def _init_robot():
            """Inizializza il robot in un thread separato.
            
            Cosi' il server HTTP e' gia' in ascolto sulla porta 5001
            mentre la connessione al NAO avviene in background.
            """
            if use_simulation:
                print("\n[MODE] SIMULAZIONE ATTIVA")
                print("-" * 40)
                robot_state["robot"] = SimulatedRobot()
                robot_state["mode"] = "simulation"
            else:
                print("\n[MODE] ROBOT NAO FISICO")
                print("-" * 40)
                try:
                    robot_state["robot"] = NAORobot(args.ip, args.port)
                    robot_state["mode"] = "real"
                except Exception as e:
                    print("[ERROR] Impossibile connettersi al robot: {}".format(e))
                    print("[INFO] Passaggio a modalita' simulazione...")
                    robot_state["error"] = str(e)
                    robot_state["robot"] = SimulatedRobot()
                    robot_state["mode"] = "simulation_fallback"
            robot_state["ready"] = True
            print("[SERVER] Robot pronto (modo: {})".format(robot_state["mode"]))
        
        # Avvia connessione robot in background
        init_thread = threading.Thread(target=_init_robot)
        init_thread.daemon = True
        init_thread.start()
        
        # Compatibilita' Python 2/3 per HTTP server
        try:
            import BaseHTTPServer
            import urlparse as urlparse_mod
            from SocketServer import ThreadingMixIn
            import Queue as queue_mod
            HTTPServer = BaseHTTPServer.HTTPServer
            BaseHandler = BaseHTTPServer.BaseHTTPRequestHandler
        except ImportError:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import urllib.parse as urlparse_mod
            from socketserver import ThreadingMixIn
            import queue as queue_mod
            BaseHandler = BaseHTTPRequestHandler
        import json

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            """HTTP server multi-threaded per gestire health check durante animazioni."""
            daemon_threads = True
        
        action_queue = queue_mod.Queue()

        def _action_worker():
            """Esegue le azioni del robot in modo strettamente sequenziale."""
            while True:
                action_name = action_queue.get()
                if action_name is None:
                    break
                
                # Attende che il robot sia pronto
                while not robot_state["ready"] or robot_state["robot"] is None:
                    time.sleep(0.5)
                    
                if action_name in actions_map:
                    robot_state["is_interacting"] = True
                    try:
                        actions_map[action_name](robot_state["robot"])
                    except Exception as e:
                        print("[ERROR] Errore azione asincrona '{}': {}".format(action_name, e))
                    finally:
                        robot_state["is_interacting"] = False
                action_queue.task_done()

        # Avvia worker thread per la coda delle azioni
        worker_thread = threading.Thread(target=_action_worker)
        worker_thread.daemon = True
        worker_thread.start()

        class RobotHandler(BaseHandler):
            def _send_json(self, code, data):
                """Invia una risposta JSON compatibile Python 2/3."""
                body = json.dumps(data)
                if not isinstance(body, bytes):
                    body = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urlparse_mod.urlparse(self.path)
                
                # Endpoint /health - risponde SEMPRE, anche durante init
                if parsed.path == "/health":
                    health = {
                        "status": "ok" if robot_state["ready"] else "connecting",
                        "ready": robot_state["ready"],
                        "mode": robot_state["mode"],
                        "error": robot_state["error"],
                        "ip": args.ip if not use_simulation else None,
                        "port": args.port if not use_simulation else None,
                        "is_interacting": robot_state.get("is_interacting", False) or not action_queue.empty()
                    }
                    self._send_json(200, health)
                    return
                
                # Endpoint azione robot - richiede robot pronto
                if not robot_state["ready"] or robot_state["robot"] is None:
                    self._send_json(503, {
                        "status": "not_ready",
                        "message": "Robot in fase di connessione..."
                    })
                    return
                
                query = urlparse_mod.parse_qs(parsed.query)
                action = query.get("action", [None])[0]
                
                if action and action in actions_map:
                    action_queue.put(action)
                    self._send_json(200, {"status": "queued", "message": "Azione messa in coda"})
                else:
                    self._send_json(400, {"status": "invalid_action"})
                    
            def log_message(self, format, *args):
                pass
        
        # Avvia HTTP server multi-threaded SUBITO (il robot si connette in parallelo)
        server = ThreadedHTTPServer(('127.0.0.1', 5001), RobotHandler)
        print("[SERVER] HTTP multi-threaded in ascolto sulla porta 5001")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    
    # =================================================================
    # MODALITA' CLI (azione singola)
    # =================================================================
    else:
        if use_simulation:
            print("\n[MODE] SIMULAZIONE ATTIVA")
            print("-" * 40)
            cli_robot = SimulatedRobot()
        else:
            print("\n[MODE] ROBOT NAO FISICO")
            print("-" * 40)
            try:
                cli_robot = NAORobot(args.ip, args.port)
            except Exception as e:
                print("[ERROR] Impossibile connettersi al robot: {}".format(e))
                print("[INFO] Passaggio a modalita' simulazione...")
                cli_robot = SimulatedRobot()
        
        if not args.action:
            print("[ERROR] Nessuna azione specificata")
            sys.exit(1)
        action_func = actions_map.get(args.action)
        if action_func:
            try:
                action_func(cli_robot)
                print("\n[OK] Azione '{}' completata".format(args.action))
            except Exception as e:
                print("\n[ERROR] Errore durante l'azione: {}".format(e))
                sys.exit(1)
        else:
            print("[ERROR] Azione sconosciuta: {}".format(args.action))
            sys.exit(1)
        
        # Cleanup per robot fisico
        if hasattr(cli_robot, 'cleanup'):
            cli_robot.cleanup()


if __name__ == "__main__":
    main()
