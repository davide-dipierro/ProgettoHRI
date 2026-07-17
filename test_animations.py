import sys
import time
import argparse

try:
    import qi
except ImportError:
    print("ERRORE: qi SDK non trovato.")
    print("Assicurati di lanciare lo script con l'eseguibile Python corretto di Choregraphe:")
    print(r'"C:\Program Files (x86)\Softbank Robotics\Choregraphe Suite 2.8\bin\python.exe" test_animations.py')
    sys.exit(1)

# Lista di animazioni che abbiamo discusso (bluff, sfida, arroganza)
ANIMATIONS = [
    # Gesti di saluto alternativi
    "animations/Stand/Gestures/Hey_1",
    "animations/Stand/Gestures/Hey_3",
    "animations/Stand/Gestures/Hey_6",
    
    # Animazioni di Rabbia / Intimidazione
    "animations/Stand/Emotions/Negative/Angry_1",
    "animations/Stand/Emotions/Negative/Angry_3",
    "animations/Stand/Emotions/Negative/Angry_4",
    
    # Animazioni di Arroganza / Fierezza
    "animations/Stand/Emotions/Positive/Proud_1",
    "animations/Stand/Emotions/Positive/Proud_2",
    
    # Gesti di Sfida (indica, vieni avanti, muscoli)
    "animations/Stand/Gestures/You_1",
    "animations/Stand/Gestures/ComeOn_1",
    "animations/Stand/Gestures/ShowMuscles_1",
    "animations/Stand/Gestures/Me_1",
    
    # Gesti Teatrali / Mette pressione
    "animations/Stand/Gestures/Explain_1",
    "animations/Stand/Emotions/Negative/Late_1",
    "animations/Stand/Gestures/No_3",
]

def main():
    parser = argparse.ArgumentParser(description="Testa le animazioni del robot NAO")
    parser.add_argument("--ip", type=str, default="100.101.2.95", help="IP del robot (default: 100.101.2.95)")
    parser.add_argument("--port", type=int, default=9559, help="Porta del robot (default: 9559)")
    args = parser.parse_args()

    session = qi.Session()
    print("Connessione al robot {}:{}...".format(args.ip, args.port))
    try:
        session.connect("tcp://{}:{}".format(args.ip, args.port))
    except Exception as e:
        print("Impossibile connettersi al robot: {}".format(e))
        sys.exit(1)
        
    animation = session.service("ALAnimationPlayer")
    motion = session.service("ALMotion")
    posture = session.service("ALRobotPosture")

    print("\nRisveglio il robot e mi metto in posizione neutra (StandInit)...")
    motion.wakeUp()
    posture.goToPosture("StandInit", 0.5)

    print("\n=======================================================")
    print("                 TEST ANIMAZIONI NAO                   ")
    print("=======================================================")
    
    for anim in ANIMATIONS:
        # Gestione input per Python 2.7 (quello usato da Choregraphe)
        if sys.version_info[0] < 3:
            user_input = raw_input("\n--> Premi INVIO per testare '{}' (oppure 'q' per uscire): ".format(anim))
        else:
            user_input = input("\n--> Premi INVIO per testare '{}' (oppure 'q' per uscire): ".format(anim))
            
        if user_input.strip().lower() == 'q':
            print("Uscita dal test...")
            break
            
        print("Esecuzione di '{}'...".format(anim))
        try:
            animation.run(anim)
        except Exception as e:
            print("[ERRORE] Animazione fallita: {}".format(e))
            
        print("Ripristino postura neutrale...")
        posture.goToPosture("StandInit", 0.8)
        time.sleep(0.5)
        
    print("\nTest completato.")

if __name__ == "__main__":
    main()
