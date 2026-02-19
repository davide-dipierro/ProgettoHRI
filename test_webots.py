from naoqi import ALProxy
import sys

# Se usi il robot vero:
# ROBOT_IP = "192.168.1.100" 
# PORT = 9559

# Se usi Webots o Choregraphe (Virtual Robot):
ROBOT_IP = "127.0.0.1"  # Localhost
PORT = 1234 # Verifica la porta: Webots usa spesso la 9559, Choregraphe a volte assegna porte random se ne apri più di uno.

try:
    tts = ALProxy("ALTextToSpeech", ROBOT_IP, PORT)
    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    
    # Test semplice
    tts.say("Ciao, sono nel simulatore!")
    
    # Esempio movimento (funzionerà "davvero" solo in Webots)
    motion.moveTo(0.5, 0, 0) # Cammina avanti di 50cm

except Exception as e:
    print("Impossibile connettersi al simulatore NAOqi.")
    print("Errore: ", e)