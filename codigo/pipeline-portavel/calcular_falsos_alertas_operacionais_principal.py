from pathlib import Path
import os
import pandas as pd

BASE = Path(os.environ.get("CONTIKI_NG_ROOT", Path.home() / "contiki-ng")).expanduser().resolve()
RESULTADOS = BASE / "experimentos/final/ml/resultados_principal_4classes"
OUT = RESULTADOS / "comparacao_final"

MODELOS = {
    "XGBoost_60s": RESULTADOS / "xgboost_60s",
    "LSTM": RESULTADOS / "lstm",
    "GRU": RESULTADOS / "gru",
}

LIMIAR = 0.50
CONFIRMACOES = 3

linhas = []

for modelo, diretorio in MODELOS.items():
    pred = pd.read_csv(
        diretorio / "predicoes_todos_folds.csv",
        sep=";",
    )

    normal = pred[
        pred["true_label"] == "normal"
    ]

    for seed, grupo in normal.groupby("seed", sort=True):
        grupo = grupo.sort_values("end_window")

        classe_anterior = None
        consecutivas = 0
        alerta_ativo = False
        alertas = 0

        for linha in grupo.itertuples(index=False):
            classe = linha.predicted_label

            if classe == "normal":
                classe_anterior = None
                consecutivas = 0
                alerta_ativo = False
                continue

            probabilidade = getattr(
                linha,
                f"prob_{classe}",
            )

            if probabilidade < LIMIAR:
                classe_anterior = None
                consecutivas = 0
                alerta_ativo = False
                continue

            if classe == classe_anterior:
                consecutivas += 1
            else:
                classe_anterior = classe
                consecutivas = 1
                alerta_ativo = False

            if (
                consecutivas >= CONFIRMACOES and
                not alerta_ativo
            ):
                alertas += 1
                alerta_ativo = True

        horas = len(grupo) * 10 / 3600

        linhas.append({
            "modelo": modelo,
            "seed": int(seed),
            "janelas_normais": len(grupo),
            "falsos_alertas": alertas,
            "teve_falso_alerta": int(alertas > 0),
            "falsos_alertas_por_hora":
                alertas / horas,
        })

df = pd.DataFrame(linhas)

resumo = (
    df.groupby("modelo", observed=True)
    .agg(
        seeds=("seed", "count"),
        seeds_com_falso_alerta=(
            "teve_falso_alerta",
            "sum",
        ),
        falsos_alertas_total=(
            "falsos_alertas",
            "sum",
        ),
        falsos_alertas_media_seed=(
            "falsos_alertas",
            "mean",
        ),
        falsos_alertas_por_hora=(
            "falsos_alertas_por_hora",
            "mean",
        ),
    )
    .reset_index()
)

df.to_csv(
    OUT / "falsos_alertas_operacionais_por_seed.csv",
    sep=";",
    index=False,
)

resumo.to_csv(
    OUT / "resumo_falsos_alertas_operacionais.csv",
    sep=";",
    index=False,
)

print("===== FALSOS ALERTAS OPERACIONAIS =====")
print(resumo.to_string(index=False))
print(f"\nResultados: {OUT}")
