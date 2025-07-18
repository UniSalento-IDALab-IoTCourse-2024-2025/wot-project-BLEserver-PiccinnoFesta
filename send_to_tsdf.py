#!/usr/bin/env python3
import requests
import time
from pathlib import Path
import shutil
import json



# ——— CONFIG —————————————————————————
TSDF_DIR  = Path.home() / "toSendData" / "tsdf_output"
SENT_DIR  = Path.home() / "toSendData" / "sent"

CONFIG_PATH = Path(__file__).parent / "patient_config.json"
# Default fallback
PATIENT_ID = "unknown_patient"

if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
            PATIENT_ID = data.get("patient_id", PATIENT_ID)
    except Exception as e:
        print(f"Errore lettura config: {e}")


# ——— S3 CONFIG —————————————————————————
API_GATEWAY_URL = "https://3qpkphed39.execute-api.us-east-1.amazonaws.com/dev"

TSDF_DIR.mkdir(parents=True, exist_ok=True)
SENT_DIR.mkdir(parents=True, exist_ok=True)

def get_presigned_url():
    """Richiede un URL firmato da API Gateway."""
    if not PATIENT_ID:
        print("Errore: variabile d'ambiente PATIENT_ID non impostata.")
        return None, None

    try:
        headers = {"patientid": PATIENT_ID}
        response = requests.get(f"{API_GATEWAY_URL}/api/raspberry/upload", headers=headers)
        if response.status_code != 200:
            print(f"Errore API Gateway: {response.status_code} - {response.text}")
            return None, None

        outer_json = response.json()
        inner_json = json.loads(outer_json["body"])
        return inner_json["url"], inner_json["key"]
    except Exception as e:
        print(f"Errore durante richiesta presigned URL: {e}")
        return None, None


def upload_zip_to_s3(zip_path: Path, presigned_url: str) -> bool:
    """Effettua l’upload del file ZIP al link firmato."""
    try:
        headers = {'Content-Type': 'application/zip'}
        with open(zip_path, "rb") as f:
            put_resp = requests.put(presigned_url, data=f, headers=headers)
        
        if put_resp.status_code != 200:
            print(f"S3 Upload Error: {put_resp.status_code} - {put_resp.text}")
        
        return put_resp.status_code == 200
    except Exception as e:
        print(f"Errore durante l'upload S3: {e}")
        return False


def upload_segment(out_dir: Path) -> bool:
    """Effettua l’upload di un segmento, poi sposta solo lo zip se ha successo."""
    try:
        zip_path = out_dir.with_suffix(".zip")
        shutil.make_archive(base_name=str(zip_path).replace(".zip", ""), format="zip", root_dir=out_dir)

        while True:
            presigned_url, s3_key = get_presigned_url()
            if not presigned_url:
                print("Impossibile ottenere presigned URL. Ritento tra 30s.")
                time.sleep(30)
                continue

            success = upload_zip_to_s3(zip_path, presigned_url)
            if success:
                print(f"✓ Caricato su S3: {s3_key}")

                dest_zip = SENT_DIR / zip_path.name
                shutil.move(str(zip_path), str(dest_zip))
                shutil.rmtree(out_dir, ignore_errors=True)

                return True
            else:
                print("✗ Upload fallito. Ritento tra 30s.")
                time.sleep(30)
    except Exception as e:
        print(f"Errore nel caricamento {out_dir.name}: {e}")
        return False


def main():
    print("Avvio invio continuo dei segmenti ogni 15 secondi…")
    while True:
        segments = sorted([d for d in TSDF_DIR.iterdir() if d.is_dir() and d.name.startswith("segment")])
        if not segments:
            print("Nessun segmento da inviare.")
        for seg in segments:
            upload_segment(seg)
               
        time.sleep(15)

if __name__ == "__main__":
    main()