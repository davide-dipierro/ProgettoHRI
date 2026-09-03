import os, csv, datetime

base_dir = r'c:\Users\david\ProgettoHRI v3\Dati raccolti'
quest_file = os.path.join(base_dir, 'Questionario finale Nao (Risposte) - Risposte del modulo 1.csv')

quests = []
with open(quest_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    for i, row in enumerate(reader):
        try:
            time_str = row[0]
            time_parts = time_str.split(' ')
            date_str = time_parts[0]
            time_part = time_parts[1].replace('.', ':')
            q_time = datetime.datetime.strptime(date_str + ' ' + time_part, '%d/%m/%Y %H:%M:%S')
            quests.append({'id': i+2, 'time': q_time, 'row': row})
        except Exception as e:
            print('Error parsing quest row', i+2, e)

exps = []
for d in os.listdir(base_dir):
    d_path = os.path.join(base_dir, d)
    if os.path.isdir(d_path) and d.startswith('data_'):
        exp_file = os.path.join(d_path, 'experiment_results.csv')
        if os.path.exists(exp_file):
            with open(exp_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                row = next(reader)
                e_time = datetime.datetime.strptime(row[2].split('.')[0], '%Y-%m-%dT%H:%M:%S')
                exps.append({'name': d, 'time': e_time, 'row': row})

# Add missing match condition for id=2 (since it's a test or from July)
for exp in sorted(exps, key=lambda x: x['time']):
    best_match = None
    min_diff = float('inf')
    for q in quests:
        diff = (q['time'] - exp['time']).total_seconds()
        if 0 < diff < 10000:
            if diff < min_diff:
                min_diff = diff
                best_match = q
    if best_match:
        print(exp['name'] + " -> Riga " + str(best_match['id']) + " (Scarto: " + str(round(min_diff/60, 1)) + " min)")
    else:
        print(exp['name'] + " -> NESSUN MATCH TROVATO")
