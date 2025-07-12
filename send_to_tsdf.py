#!/usr/bin/env python3
import requests
import time
from pathlib import Path
import shutil

# ——— CONFIG —————————————————————————
TSDF_DIR  = Path.home() / "toSendData" / "tsdf_output"
SENT_DIR  = Path.home() / "toSendData" / "sent"
TSDF_INGEST_URL = "http://172.20.10.4:4000/api/tsdf"

TSDF_DIR.mkdir(parents=True, exist_ok=True)
SENT_DIR.mkdir(parents=True, exist_ok=True)

def upload_segment(out_dir: Path):
    files = {
        "metadata": ("IMU_meta.json", open(out_dir / "IMU_meta.json", "rb"), "application/json"),
        "time":     ("IMU_time.bin",  open(out_dir / "IMU_time.bin",  "rb"), "application/octet-stream"),
        "values":   ("IMU_values.bin",open(out_dir / "IMU_values.bin","rb"), "application/octet-stream")
    }
    try:
        resp = requests.post(TSDF_INGEST_URL, files=files)
        resp.raise_for_status()
        print(f"✅ Segmento {out_dir.name} caricato.")
        return True
    except Exception as e:
        print(f"❌ Errore nel caricamento {out_dir.name}: {e}")
        return False
    finally:
        for f in files.values():
            f[1].close()

def main():
    print("Avvio invio continuo dei segmenti ogni 10 secondi…")
    while True:
        segments = sorted([d for d in TSDF_DIR.iterdir() if d.is_dir() and d.name.startswith("segment")])
        if not segments:
            print("🕐 Nessun segmento da inviare.")
        for seg in segments:
            if upload_segment(seg):
                dest = SENT_DIR / seg.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.move(str(seg), str(dest))
        time.sleep(10)

if __name__ == "__main__":
    main()