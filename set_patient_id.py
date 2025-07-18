# set_patient_id.py
import json
from pathlib import Path
import sys

CONFIG_PATH = Path(__file__).parent / "patient_config.json"

if len(sys.argv) != 2:
    print("Uso: python3 set_patient_id.py <nuovo_patient_id>")
    sys.exit(1)

new_id = sys.argv[1]

try:
    with open(CONFIG_PATH, "w") as f:
        json.dump({"patient_id": new_id}, f)
    print(f"✓ Patient ID aggiornato a: {new_id}")
except Exception as e:
    print(f"Errore aggiornamento: {e}")