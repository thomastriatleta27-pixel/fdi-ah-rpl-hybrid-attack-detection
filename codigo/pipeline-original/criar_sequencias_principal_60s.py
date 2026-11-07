import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path("/home/joaorosa/contiki-ng")

CSV = (
    BASE /
    "experimentos/final/resultados/dataset/"
    "dataset_fdi_ah_principal_agregado_janela_3600s.csv"
)

OUT_DIR = BASE / "experimentos/final/ml/dados"
OUT_NPZ = OUT_DIR / "sequencias_principal_4classes_60s.npz"
OUT_JSON = OUT_DIR / "sequencias_principal_4classes_60s.json"

SEQUENCE_LENGTH = 6

CLASSES = {
    "normal": 0,
    "sinkhole": 1,
    "sybil": 2,
    "hybrid": 3,
}

OUT_DIR.mkdir(parents=True, exist_ok=True)

print("Carregando dataset agregado...")
df = pd.read_csv(CSV)

metadata = ["scenario", "seed", "window"]
features = [c for c in df.columns if c not in metadata]

sequences = []
labels = []
seeds = []
end_windows = []

for (scenario, seed), group in df.groupby(
    ["scenario", "seed"],
    sort=True,
    observed=True,
):
    group = group.sort_values("window")

    windows = group["window"].to_numpy()
    values = group[features].to_numpy(dtype=np.float32)

    if len(group) != 359:
        raise ValueError(
            f"{scenario} seed{seed}: "
            f"{len(group)} janelas, esperado 359"
        )

    if not np.all(np.diff(windows) == 1):
        raise ValueError(
            f"{scenario} seed{seed}: janelas não consecutivas"
        )

    for end in range(SEQUENCE_LENGTH - 1, len(group)):
        start = end - SEQUENCE_LENGTH + 1

        sequences.append(values[start:end + 1])
        labels.append(CLASSES[scenario])
        seeds.append(int(seed))
        end_windows.append(int(windows[end]))

X = np.asarray(sequences, dtype=np.float32)
y = np.asarray(labels, dtype=np.int64)
groups = np.asarray(seeds, dtype=np.int64)
windows = np.asarray(end_windows, dtype=np.int64)

np.savez_compressed(
    OUT_NPZ,
    X=X,
    y=y,
    groups=groups,
    windows=windows,
)

config = {
    "source": str(CSV),
    "sequence_length": SEQUENCE_LENGTH,
    "window_seconds": 10,
    "sequence_seconds": SEQUENCE_LENGTH * 10,
    "samples": int(len(X)),
    "timesteps": int(X.shape[1]),
    "features": features,
    "classes": CLASSES,
}

with OUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"Arquivo: {OUT_NPZ}")
print(f"Formato X: {X.shape}")
print(f"Formato y: {y.shape}")
print(f"Características: {len(features)}")
print(f"Sequências: {len(X)}")
print(f"NaN em X: {np.isnan(X).sum()}")

for classe, codigo in CLASSES.items():
    print(f"{classe}: {(y == codigo).sum()}")
