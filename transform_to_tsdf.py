#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import numpy as np

# ——— Configurazione —————————————————————————————————————————
BUFFER_DIR = Path("toSendData/buffer")
OUT_DIR    = Path("toSendData/tsdf_output/segment0")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Metadati generali (adatta alle tue esigenze)
META = {
    "study_id":             "PPP",
    "device_id":            "Verily Study Watch",
    "subject_id":           "X",
    "ppp_source_protobuf":  "WatchData.IMU.Week104.raw",
    "metadata_version":     "0.1",
    "endianness":           "little",
    "data_type":            "float"
}

# Parametri per il blocco “time”
TIME_SENSOR = {
    "file_name":     "IMU_time.bin",
    "channels":      ["time"],
    "units":         ["iso8601"],
    "bits":          64,
    "scale_factors": [1]
}

# Parametri per il blocco “values”
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
    #scale:factors ad 1 perchè le unità sono già prese correttamente da smartwatch
    "scale_factors": [1,1,1,1,1,1],
    "bits":          64
}

# ——— 1) Leggi e aggrega i JSON ——————————————————————————————
records = []
for f in sorted(BUFFER_DIR.glob("reading-*.json")):
    with open(f, "r") as fp:
        rec = json.load(fp)
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
    print("Nessun dato da processare.")
    exit(0)

df = pd.DataFrame(records).sort_values("time").reset_index(drop=True)

# ——— 2) Prepara i metadata finali ————————————————————————————
meta = META.copy()
meta.update({
    "start_iso8601": df["time"].iloc[0],
    "end_iso8601":   df["time"].iloc[-1],
    "rows":          len(df),
    "sensors": [
        TIME_SENSOR,
        VALUE_SENSOR
    ]
})

# ——— 3) Scrivi IMU_time.bin —————————————————————————————————
time_bin = OUT_DIR / TIME_SENSOR["file_name"]
with open(time_bin, "w", encoding="utf-8") as f:
    for t in df["time"]:
        f.write(f"{t}\n")

# ——— 4) Scrivi IMU_values.bin ——————————————————————————————
vals = df[["acc_x","acc_y","acc_z","gyro_x","gyro_y","gyro_z"]].to_numpy(dtype=np.float64)
vals_bin = OUT_DIR / VALUE_SENSOR["file_name"]
with open(vals_bin, "wb") as f:
    # numpy.tofile rispetta little-endian per default su Raspberry
    vals.tofile(f)

# ——— 5) Scrivi IMU_meta.json ——————————————————————————————
meta_file = OUT_DIR / "IMU_meta.json"
with open(meta_file, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

print(f"TSDF creato in: {OUT_DIR}")