c# HRI Poker Experiment

Un sistema web per condurre un esperimento di Human-Robot Interaction (HRI) in cui un robot NAO gioca a poker contro un umano, includendo una fase di bluff prestabilita per analizzare le reazioni degli utenti.

## Prerequisiti
- **Choregraphe Suite 2.8** (per il motore NAOqi)
- Il sistema rileva in automatico la versione di Python 2.7 fornita con Choregraphe o tramite l'impostazione `PYTHON27_PATH` se presente.

## Come Avviare
1. Apri **Choregraphe** (se utilizzi un robot virtuale/locale) o accendi il NAO.
2. Vai nella cartella del progetto e avvia lo script `start.ps1`.
   - *Puoi farlo facendo clic destro sul file e selezionando "Esegui con PowerShell", oppure digitando `.\start.ps1` in un terminale PowerShell.*
3. Lo script avvierà il server e tutte le interfacce necessarie.

## Utilizzo
Una volta avviato il server, apri il browser e accedi alle seguenti pagine:

- **Pannello Admin:** [http://localhost:5000/admin](http://localhost:5000/admin)
  - È il pannello di controllo per lo sperimentatore.
  - Prima di iniziare la partita, clicca su **"🔍 Cerca Porta"** per trovare e configurare automaticamente la connessione con il robot (o con la simulazione). 
  - Clicca **"💾 Salva e Riavvia"** per applicare la configurazione.
  - Da qui potrai far avanzare le mani del poker e triggerare animazioni manualmente.
  
- **Interfaccia Giocatore (Utente):** [http://localhost:5000/player](http://localhost:5000/player)
  - Lo schermo da mostrare al partecipante durante l'esperimento.
  
- **Interfaccia Robot:** [http://localhost:5000/robot](http://localhost:5000/robot)
  - Interfaccia speculare opzionale che mostra le informazioni viste "dal punto di vista del robot".

## Struttura del Progetto
L'architettura è basata su Flask e un backend modulare:
- `server.py`: Gestisce l'avvio e le API di comunicazione.
- `game_state.py` (Facade): Coordina i vari moduli del gioco (`poker_engine`, `experiment_manager`, `robot_ai`).
- `robot_controller.py`: Modulo in Python 2.7 che fa da server in background per ricevere le chiamate dal server principale e inviare istruzioni istantanee al NAO via NAOqi.
- `static/style.css`: Il foglio di stile con design Glassmorphism e animazioni premium per la UI dell'esperimento.
- `data/`: La cartella dove verranno salvati automaticamente i log dell'esperimento (file CSV) e i risultati del questionario.
