import os
import csv
import shutil

base_dir = r'c:\Users\david\ProgettoHRI v3\Dati raccolti'
source_dir = os.path.join(base_dir, 'data_simonadaniele')
daniele_dir = os.path.join(base_dir, 'data_daniele')
simona_dir = os.path.join(base_dir, 'data_simona')

if not os.path.exists(daniele_dir):
    os.makedirs(daniele_dir)
if not os.path.exists(simona_dir):
    os.makedirs(simona_dir)

session_daniele = '20260903_155808'
session_simona = '20260903_161621'

files = ['experiment_results.csv', 'action_log.csv', 'hand_results.csv']

for filename in files:
    source_file = os.path.join(source_dir, filename)
    daniele_file = os.path.join(daniele_dir, filename)
    simona_file = os.path.join(simona_dir, filename)
    
    with open(source_file, 'rb') as f_in, \
         open(daniele_file, 'wb') as f_daniele, \
         open(simona_file, 'wb') as f_simona:
         
        reader = csv.reader(f_in)
        writer_daniele = csv.writer(f_daniele)
        writer_simona = csv.writer(f_simona)
        
        header = next(reader)
        writer_daniele.writerow(header)
        writer_simona.writerow(header)
        
        for row in reader:
            if not row:
                continue
            
            # session_id or id is always the first column
            row_id = row[0]
            if row_id == session_daniele:
                writer_daniele.writerow(row)
            elif row_id == session_simona:
                writer_simona.writerow(row)

print("Split completed successfully!")
