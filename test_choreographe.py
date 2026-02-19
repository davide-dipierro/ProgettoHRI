# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import os
import struct
import sys
import time

# Configura il path dell'SDK Choregraphe
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdk_config

# Porta di default (letta da sdk_config o env var NAO_PORT)
PORTA_SIMULATORE = sdk_config.DEFAULT_PORT


def _bits_python_corrente():
    return struct.calcsize("P") * 8


def _stampa_info_runtime():
    print("Python: {}".format(sys.version.replace("\n", " ")))
    print("Architettura Python: {} bit".format(_bits_python_corrente()))


def _import_qi_con_diagnostica():
    try:
        import qi
        return qi
    except Exception as e:
        print("Errore durante import di 'qi': {}".format(e))
        _stampa_info_runtime()
        print("\nSuggerimenti rapidi:")
        print("- Per NAOqi/Choregraphe legacy, usare in genere Python 2.7.")
        print("- Python e modulo qi devono avere la STESSA architettura (entrambi 32-bit o entrambi 64-bit).")
        print("- Se vedi 'DLL load failed' / 'not a valid Win32 application', c'è quasi sempre mismatch 32/64 bit.")
        sys.exit(2)


def _parse_args():
    parser = argparse.ArgumentParser(description="Test connessione Choregraphe via qi")
    parser.add_argument("--host", default="127.0.0.1", help="Host del robot/simulatore")
    parser.add_argument("--port", type=int, default=PORTA_SIMULATORE, help="Porta NAOqi/Choregraphe")
    return parser.parse_args()


def _connetti_con_fallback(qi, host, porta_preferita):
    porte_candidate = [porta_preferita, 9559, 15000, 59924, 12345]
    porte_ordinate = []
    for p in porte_candidate:
        if p not in porte_ordinate:
            porte_ordinate.append(p)

    ultimo_errore = None
    for porta in porte_ordinate:
        session = qi.Session()
        connection_url = "tcp://{}:{}".format(host, porta)
        try:
            print("Tentativo di connessione a {}...".format(connection_url))
            session.connect(connection_url)
            print("Connesso con successo al robot virtuale!")
            return session, connection_url
        except RuntimeError as e:
            ultimo_errore = e
            print("Connessione fallita su {} ({})".format(connection_url, e))

    print("\nErrore di connessione: Impossibile connettersi a Choregraphe.")
    print("Verifica che Choregraphe sia aperto e che la porta sia corretta.")
    print("Dettagli errore finale: {}".format(ultimo_errore))
    sys.exit(1)

def main():
    args = _parse_args()
    qi = _import_qi_con_diagnostica()

    # 1-2. Inizializza la sessione e prova la connessione con fallback porte
    session, connection_url = _connetti_con_fallback(qi, args.host, args.port)
    print("Endpoint NAOqi in uso: {}".format(connection_url))

    try:
        # 3. Ottieni i servizi necessari dalla sessione (sostituisce ALProxy)
        tts = session.service("ALTextToSpeech")
        motion = session.service("ALMotion")
        
        # 4. Invia i comandi
        print("Invio comando vocale...")
        tts.say("Ciao! Sto usando il nuovo framework qi per parlare dal simulatore.")
        
        # Riattiva i motori (necessario per muovere il robot virtuale in Choregraphe)
        motion.wakeUp()
        
        print("Muovo la testa...")
        # Muovi la testa (HeadYaw = rotazione destra/sinistra)
        motion.setAngles("HeadYaw", 1.0, 0.2) 
        time.sleep(2)
        
        # Riporta la testa al centro
        motion.setAngles("HeadYaw", 0.0, 0.2)
        time.sleep(1)
        
        print("Test completato con successo.")
        
    except Exception as e:
        print("Si è verificato un errore durante l'esecuzione dei comandi:")
        print(e)

if __name__ == "__main__":
    main()