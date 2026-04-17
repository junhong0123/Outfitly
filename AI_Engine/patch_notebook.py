import json

with open('data_preparation.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        new_source = []
        for line in source:
            if 'batch.to_sql("Products", engine,' in line:
                new_source.append('        with engine.begin() as conn:\n')
                new_source.append('            conn.execute(text("SET IDENTITY_INSERT Products ON"))\n')
                new_source.append('            batch.to_sql("Products", conn, if_exists="append", index=False)\n')
                new_source.append('            conn.execute(text("SET IDENTITY_INSERT Products OFF"))\n')
            else:
                new_source.append(line)
        cell['source'] = new_source

with open('data_preparation.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
print("Notebook patched.")
