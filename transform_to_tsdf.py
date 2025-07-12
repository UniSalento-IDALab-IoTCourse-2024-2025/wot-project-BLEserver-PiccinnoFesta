#!/usr/bin/env python3
import json
import time
from pathlib import Path
import pandas as pd
import numpy as np

# ——— CONFIGURAZIONE —————————————————————————————————————————————
BUFFER_DIR = Path.home() / "toSendData" / "buffer"
OUT_BASE   = Path.home() / "toSendData" / "tsdf_output"

META = {
    "study_id":            "PPP",
    "device_id":           "Verily Study Watch",
    "subject_id":          "X",
    "ppp_source_protobuf": "WatchData.IMU.Week104.raw",
    "metadata_version":    "0.1",
    "endianness":          "little",
    "data_type":           "float"
}

TIME_SENSOR = {
    "file_name":     "IMU_time.bin",
    "channels":      ["time"],
    "units":         ["time_delta_ms"],
    "bits":          32,
    "scale_factors": [1]
}

VALUE_SENSOR = {
    "file_name":     "IMU_values.bin",
    "channels": [
        "acceleration_x","acceleration_y","acceleration_z",
        "gyroscope_x","gyroscope_y","gyroscope_z"
    ],
    "units": [
        "m/s/s","m/s/s","m/s/s",
        "deg/s","deg/s","deg/s"
    ],
    "scale_factors": [
        0.00469378, 0.00469378, 0.00469378,
        0.06097561, 0.06097561, 0.06097561
    ],
    "bits": 64
}

OUT_BASE.mkdir(parents=True, exist_ok=True)
BUFFER_DIR.mkdir(parents=True, exist_ok=True)

def next_segment_index():
    existing = [d.name for d in OUT_BASE.iterdir() if d.is_dir() and d.name.startswith("segment")]
    nums = [int(name.replace("segment", "")) for name in existing if name.replace("segment", "").isdigit()]
    return max(nums) + 1 if nums else 0

def process_batch(segment_idx: int) -> bool:
    buffer_files = sorted(BUFFER_DIR.glob("segment*_raw.json"))
    if not buffer_files:
        print(f"[segment{segment_idx}] nessun campione, aspetto…")
        return False

    records = []
    for f in buffer_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for rec in data.get("samples", []):
            records.append({
                "time":   rec["timestamp"],
                "acc_x":  rec["accel"]["x"],
                "acc_y":  rec["accel"]["y"],
                "acc_z":  rec["accel"]["z"],
                "gyro_x": rec["gyro"]["x"],
                "gyro_y": rec["gyro"]["y"],
                "gyro_z": rec["gyro"]["z"]
            })
    if not records:
        for f in buffer_files:
            f.unlink()
        return False

    # ✅ Gestione robusta del fuso orario
    df = pd.DataFrame(records)
    df["time"] = pd.to_datetime(df["time"])
    if df["time"].dt.tz is None:
        df["time"] = df["time"].dt.tz_localize("UTC")
    else:
        df["time"] = df["time"].dt.tz_convert("UTC")

    meta = {
        "study_id":            META["study_id"],
        "device_id":           META["device_id"],
        "subject_id":          META["subject_id"],
        "ppp_source_protobuf": META["ppp_source_protobuf"],
        "metadata_version":    META["metadata_version"],
        "start_iso8601":       df["time"].iloc[0].isoformat(),
        "end_iso8601":         df["time"].iloc[-1].isoformat(),
        "rows":                len(df),
        "endianness":          META["endianness"],
        "data_type":           META["data_type"],
        "sensors": [
            TIME_SENSOR,
            VALUE_SENSOR
        ]
    }

    out_dir = OUT_BASE / f"segment{segment_idx}"
    out_dir.mkdir(exist_ok=True)

    # 📦 Scrivi tempo relativo in ms dal primo campione
    times = df["time"]
    deltas_ms = (times - times.iloc[0]).dt.total_seconds() * 1e3
    np.array(deltas_ms, dtype=np.float32).tofile(out_dir / TIME_SENSOR["file_name"])

    # 📦 Scrivi valori sensore scalati
    raw = df[["acc_x","acc_y","acc_z","gyro_x","gyro_y","gyro_z"]].to_numpy(dtype=np.float64)
    sf = np.array(VALUE_SENSOR["scale_factors"], dtype=np.float64)
    (raw * sf[np.newaxis, :]).tofile(out_dir / VALUE_SENSOR["file_name"])

    with open(out_dir / "IMU_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    for f in buffer_files:
        f.unlink()

    print(f"[segment{segment_idx}] TSDF creato con {len(df)} record.")
    return True

def main():
    print("Inizio creazione TSDF…")
    seg_idx = next_segment_index()
    while True:
        if process_batch(seg_idx):
            seg_idx += 1
        time.sleep(5)

if __name__ == "__main__":
    main()