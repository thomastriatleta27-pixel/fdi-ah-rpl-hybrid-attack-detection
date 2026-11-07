from pathlib import Path
import os
import pandas as pd

BASE = Path(os.environ.get("CONTIKI_NG_ROOT", Path.home() / "contiki-ng")).expanduser().resolve()

ENTRADA = (
    BASE /
    "experimentos/final/resultados/dataset/"
    "dataset_fdi_ah_principal_4classes_3600s.csv"
)

SAIDA = (
    BASE /
    "experimentos/final/resultados/dataset/"
    "dataset_fdi_ah_principal_agregado_janela_3600s.csv"
)

METADADOS = [
    "scenario",
    "seed",
    "node_id",
    "timestamp_us",
    "timestamp_s",
    "window",
]

print("Carregando dataset...")
df = pd.read_csv(ENTRADA)

grupos = ["scenario", "seed", "window"]
features = [c for c in df.columns if c not in METADADOS]

tamanhos = df.groupby(grupos, observed=True).size()

if len(tamanhos) != 14360:
    raise ValueError(f"Quantidade inesperada de janelas: {len(tamanhos)}")

if tamanhos.min() != 30 or tamanhos.max() != 30:
    raise ValueError(
        f"Número de nós por janela inválido: "
        f"mínimo={tamanhos.min()}, máximo={tamanhos.max()}"
    )

print("Agregando os 30 nós de cada janela...")

estatisticas = (
    df.groupby(grupos, observed=True)[features]
      .agg(["mean", "std", "min", "max"])
)

estatisticas.columns = [
    f"{feature}_{operacao}"
    for feature, operacao in estatisticas.columns
]

ausencias = (
    df[features]
    .isna()
    .assign(
        scenario=df["scenario"],
        seed=df["seed"],
        window=df["window"],
    )
    .groupby(grupos, observed=True)
    .mean()
)

ausencias.columns = [
    f"{feature}_missing_rate"
    for feature in ausencias.columns
]

agregado = (
    estatisticas
    .join(ausencias)
    .reset_index()
)

agregado.to_csv(SAIDA, index=False)

print(f"Arquivo: {SAIDA}")
print(f"Linhas: {len(agregado)}")
print(f"Colunas: {len(agregado.columns)}")
print(f"Nós por janela: {tamanhos.min()} a {tamanhos.max()}")

print()
print("Linhas por classe:")
print(agregado["scenario"].value_counts().sort_index())
