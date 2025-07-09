#!/usr/bin/env python3
import requests
import shutil
import time
import sys
from pathlib import Path

# ——— Configurazione —————————————————————————————————————————
SERVER_URL = "http://192.168.1.101:4000/api/tsdf"
TSDF_BASE  = Path.home() / "toSendData" / "tsdf_output"
SENT_DIR   = TSDF_BASE / "sent"
WINDOW_SEC = 60

# Assicuriamoci che la cartella per i segmenti inviati esista
SENT_DIR.mkdir(parents=True, exist_ok=True)

def send_segment(segment_dir: Path) -> bool:
    """Invia i file di uno segment e ritorna True se OK."""
    seg_name = segment_dir.name  # e.g. "segment0"
    meta_f   = segment_dir / "IMU_meta.json"
    time_f   = segment_dir / "IMU_time.bin"
    vals_f   = segment_dir / "IMU_values.bin"

    # Controlla esistenza
    for f in (meta_f, time_f, vals_f):
        if not f.exists():
            print(f"[{seg_name}] file mancante: {f}", file=sys.stderr)
            return False

    files = {
        "segment": (None, seg_name),  # campo form con il nome del segmento
        "metadata": (meta_f.name, open(meta_f, "rb"), "application/json"),
        "time":     (time_f.name, open(time_f, "rb"), "application/octet-stream"),
        "values":   (vals_f.name, open(vals_f, "rb"), "application/octet-stream"),
    }

    print(f"[{seg_name}] Invio a {SERVER_URL} …", end="", flush=True)
    try:
        resp = requests.post(SERVER_URL, files=files, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(" fallito:", e)
        return False

    print(" OK:", resp.status_code)
    return True

def main():
    print(f"Inizio send_tsdf loop (ogni {WINDOW_SEC}s)")
    while True:
        # Scansiona segmentN in ordine
        segments = sorted(
            [d for d in TSDF_BASE.iterdir() if d.is_dir() and d.name.startswith("segment")],
            key=lambda p: int(p.name.replace("segment", "")) if p.name.replace("segment","").isdigit() else p.name
        )
        if not segments:
            print("Nessun segment da inviare. Attendo…")
        for seg in segments:
            if send_segment(seg):
                # sposta in sent/
                target = SENT_DIR / seg.name
                print(f"[{seg.name}] Sposto in {target}")
                shutil.move(str(seg), str(target))
            else:
                print(f"[{seg.name}] Riprovo al prossimo giro.")
        # Attendo la prossima finestra
        time.sleep(WINDOW_SEC)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTerminato dall'utente.")
        sys.exit(0)