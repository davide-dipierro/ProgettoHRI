import os, csv, datetime

base_dir = r'c:\Users\david\ProgettoHRI v3\Dati raccolti'
quest_file = os.path.join(base_dir, 'Questionario finale Nao (Risposte) - Risposte del modulo 1.csv')

# Mappatura manuale stabilita precedentemente
row_to_folder = {
    3: 'data_gaia',
    4: 'data_michele',
    5: 'data_adriano',
    6: 'data_ivano',
    7: 'data_angela',
    8: 'data_giulio',
    9: 'data_daniele',
    10: 'data_francescopio',
    11: 'data_simona',
    12: 'data_gigipica',
    13: 'data_danielemanganiello'
}

# Estrai i session_id dai file experiment_results.csv
folder_to_id = {}
for d in os.listdir(base_dir):
    d_path = os.path.join(base_dir, d)
    if os.path.isdir(d_path) and d.startswith('data_'):
        exp_file = os.path.join(d_path, 'experiment_results.csv')
        if os.path.exists(exp_file):
            with open(exp_file, 'rb') as f:
                reader = csv.reader(f)
                next(reader) # Salta l'header
                for row in reader:
                    if row:
                        folder_to_id[d] = row[0]
                        break

# Leggi e aggiorna il CSV del questionario
rows = []
with open(quest_file, 'rb') as f_in:
    reader = csv.reader(f_in)
    header = next(reader)
    if header[-1] != 'session_id':
        header.append('session_id')
    rows.append(header)
    
    for i, row in enumerate(reader):
        row_idx = i + 2 # L'indice parte da 2 (riga 1 è l'header)
        sess_id = ""
        if row_idx in row_to_folder:
            folder = row_to_folder[row_idx]
            sess_id = folder_to_id.get(folder, "")
        
        # Aggiungi o aggiorna la colonna session_id
        if len(row) < len(header):
            row.append(sess_id)
        else:
            row[-1] = sess_id
        rows.append(row)

# Salva le modifiche nel CSV
with open(quest_file, 'wb') as f_out:
    writer = csv.writer(f_out)
    writer.writerows(rows)

print("Gli ID associazione sono stati aggiunti con successo al file CSV del questionario!")
