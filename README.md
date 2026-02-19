# HRI Poker Experiment - Sistema Completo

## 📋 Descrizione

Sistema per esperimento di Human-Robot Interaction (HRI) che simula una partita di Texas Hold'em tra un utente umano e un robot NAO. L'obiettivo è studiare l'**Overtrust** - la tendenza degli umani a fidarsi eccessivamente dei robot.

### Struttura delle 3 Mani:

1. **Mano 1 (Establishment)**: L'utente vince → Costruisce fiducia
2. **Mano 2 (BLUFF)**: Robot fa all-in con carte deboli → FASE CRITICA (misura reaction time)
3. **Mano 3 (Cooldown)**: L'utente vince → Normalizza l'esperienza

---

## 🚀 Avvio Rapido

### 1. Modalità Simulazione (Senza Robot)

```bash
cd /home/davide/ProgettoHRI
SIMULATION_MODE=true python server.py
```

### 2. Modalità Robot Fisico

```bash
cd /home/davide/ProgettoHRI
SIMULATION_MODE=false NAO_IP=192.168.x.x python server.py
```

### 3. Accesso alle Interfacce

Una volta avviato il server:

| Interfaccia | URL | Scopo |
|-------------|-----|-------|
| **Player** | http://localhost:5000/player | Davanti all'utente |
| **Robot** | http://localhost:5000/robot | Davanti al robot NAO |
| **Admin** | http://localhost:5000/admin | Per lo sperimentatore |

---

## 📁 Struttura File

```
/home/davide/ProgettoHRI/
├── server.py                    # Server Flask (cervello del sistema)
├── robot_controller.py          # Controller NAO (comportamenti)
├── templates/
│   ├── player.html              # Interfaccia utente
│   ├── robot.html               # Interfaccia robot
│   └── admin.html               # Interfaccia admin
├── data/                        # Creata automaticamente
│   ├── experiment_results.csv   # Risultati esperimento
│   └── questionnaire_results.csv
└── README.md                    # Questo file
```

---

## 🎮 Flusso dell'Esperimento

### Per lo Sperimentatore (Admin)

1. Apri http://localhost:5000/admin
2. Inserisci l'ID partecipante
3. Clicca "Inizia Esperimento" → Robot si presenta
4. Clicca "Inizia Mano 1" → Inizia la partita
5. Dopo ogni mano, clicca "Prossima Mano"
6. Dopo mano 3, clicca "Mostra Questionario"
7. L'esperimento finisce quando l'utente compila il questionario

### Cosa Succede Automaticamente

- ✅ Robot prende decisioni automatiche (1-2 secondi di "pensata")
- ✅ Robot parla a ogni azione (check, call, raise, all-in)
- ✅ Robot reagisce alle azioni dell'utente
- ✅ Frasi intimidatorie durante la mano bluff (mano 2)
- ✅ Tempo di reazione misurato durante il bluff
- ✅ Dati salvati automaticamente in CSV

---

## 🃏 Configurazione Mani

### Mano 1 - Establishment (Utente vince)
- **Utente**: 10♥ 10♦ (coppia di 10)
- **Robot**: A♠ K♥ (sembra forte ma non lega)
- **Community**: 7♣ 3♠ J♦ 2♥ 5♣
- **Robot behavior**: Gioca aggressivo ma folda se utente rilancia molto

### Mano 2 - BLUFF (Robot bluffa)
- **Utente**: K♠ K♦ (coppia di Re)
- **Robot**: 3♣ 5♥ (carta alta - mano debole)
- **Community**: K♣ 9♥ 4♦ 2♠ 8♣ (utente ha tris!)
- **Robot behavior**: 
  - Preflop: piccolo rilancio
  - Flop: bet ~30% pot
  - Turn: bet ~50% pot
  - River: **ALL-IN con frasi intimidatorie**
  - _"Ho calcolato le probabilità... 72% di vincere"_

### Mano 3 - Cooldown (Utente vince)
- **Utente**: Q♥ Q♣ (coppia di Donne)
- **Robot**: J♥ 10♦ (J high)
- **Community**: Q♠ 5♣ 3♥ 7♣ 2♥ (utente ha tris!)
- **Robot behavior**: Passivo, folda se rilanci sono troppo alti

---

## 🔧 Requisiti

### Python
```bash
pip install flask
```

### Per Robot NAO Fisico (opzionale)
```bash
# Richiede qi SDK (Python 2.7 32-bit + NAOqi/Choregraphe SDK)
```

---

## 📊 Dati Raccolti

### experiment_results.csv
- `session_id`: ID sessione
- `participant_id`: ID partecipante
- `user_decision_on_bluff`: fold/call/allin
- `reaction_time_ms`: Tempo di risposta in millisecondi
- `bluff_successful`: yes/no
- `final_user_chips`, `final_robot_chips`

### questionnaire_results.csv
- Risposte alle 5 domande del questionario
- Commenti liberi

---

## 🐛 Troubleshooting

### Il robot non parla
```bash
# Verifica che robot_controller.py sia eseguibile
python robot_controller.py --action intro --simulate
```

### Le carte non vengono mostrate
- Verifica di aver cliccato "Inizia Mano X" dall'admin
- Controlla la console del server per errori

### Il turno non passa
- Verifica che sia effettivamente il turno dell'utente (indicatore giallo)
- Controlla che la mano non sia già terminata

---

## ✅ Checklist Pre-Esperimento

- [ ] Server avviato correttamente
- [ ] Interfaccia player visibile
- [ ] Interfaccia robot visibile (se usi NAO)
- [ ] Interfaccia admin aperta
- [ ] Test: Inizia esperimento → Robot parla
- [ ] Test: Inizia mano → Carte visibili
- [ ] Test: Azioni utente funzionano
- [ ] Cartella `data/` creata con file CSV

---

## 📝 Note Tecniche

- **Polling**: Le interfacce aggiornano ogni 500ms
- **Smart refresh**: Non refresha se non ci sono cambiamenti
- **Robot thinking**: 1-2 secondi per simulare decisione
- **Thread-safe**: Azioni robot in thread separati
