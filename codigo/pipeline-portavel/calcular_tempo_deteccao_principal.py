import re
from pathlib import Path
import os

import numpy as np
import pandas as pd

BASE = Path(os.environ.get("CONTIKI_NG_ROOT", Path.home() / "contiki-ng")).expanduser().resolve()

DATASET = (
    BASE /
    "experimentos/final/resultados/dataset/"
    "dataset_fdi_ah_principal_4classes_3600s.csv"
)

LOG_BASE = (
    BASE /
    "experimentos/final/logs/definitivo"
)

RESULT_BASE = (
    BASE /
    "experimentos/final/ml/resultados_principal_4classes"
)

OUT = RESULT_BASE / "comparacao_final"
OUT.mkdir(parents=True, exist_ok=True)

MODELOS = {
    "XGBoost_60s": RESULT_BASE / "xgboost_60s",
    "LSTM": RESULT_BASE / "lstm",
    "GRU": RESULT_BASE / "gru",
}

ATAQUES = ("sinkhole", "sybil", "hybrid")

CONFIRMACOES = 3
LIMIAR = 0.50

print("Construindo linha temporal das janelas...")

tempo = pd.read_csv(
    DATASET,
    usecols=[
        "scenario",
        "seed",
        "window",
        "timestamp_s",
    ],
)

tempo = (
    tempo.groupby(
        ["scenario", "seed", "window"],
        observed=True,
    )["timestamp_s"]
    .median()
    .reset_index(name="prediction_time_s")
)

mapa_tempo = {
    (
        linha.scenario,
        int(linha.seed),
        int(linha.window),
    ): float(linha.prediction_time_s)
    for linha in tempo.itertuples(index=False)
}

print(f"Janelas temporais: {len(mapa_tempo)}")

inicio_ataque = {}

def primeiro_evento(log, padrao):
    with log.open(
        encoding="utf-8",
        errors="replace",
    ) as arquivo:
        for linha in arquivo:
            if padrao in linha:
                match = re.match(r"^(\d+)\s+", linha)

                if match:
                    return int(match.group(1)) / 1_000_000

    raise ValueError(
        f"Evento {padrao} ausente: {log}"
    )

for ataque in ATAQUES:
    for seed in range(1, 11):
        log = (
            LOG_BASE /
            ataque /
            f"definitivo-{ataque}-seed{seed:02d}-3600s.log"
        )

        if ataque == "hybrid":
            inicio_sinkhole = primeiro_evento(
                log,
                "FDI_ATTACK,SINKHOLE",
            )
            inicio_sybil = primeiro_evento(
                log,
                "FDI_ATTACK,SYBIL",
            )

            primeiro = max(
                inicio_sinkhole,
                inicio_sybil,
            )
        else:
            padrao = (
                "FDI_ATTACK,SINKHOLE"
                if ataque == "sinkhole"
                else "FDI_ATTACK,SYBIL"
            )

            primeiro = primeiro_evento(
                log,
                padrao,
            )

        inicio_ataque[(ataque, seed)] = primeiro

resultados = []
falsos_alarmas = []

for modelo, diretorio in MODELOS.items():
    pred = pd.read_csv(
        diretorio / "predicoes_todos_folds.csv",
        sep=";",
    )

    for ataque in ATAQUES:
        for seed in range(1, 11):
            grupo = pred[
                (pred["true_label"] == ataque) &
                (pred["seed"] == seed)
            ].sort_values("end_window")

            consecutivas = 0
            primeira_correta = None
            confirmacao = None

            coluna_prob = f"prob_{ataque}"

            for linha in grupo.itertuples(index=False):
                chave = (
                    ataque,
                    seed,
                    int(linha.end_window),
                )

                tempo_predicao = mapa_tempo[chave]
                prevista = linha.predicted_label
                probabilidade = getattr(
                    linha,
                    coluna_prob,
                )

                correta = (
                    prevista == ataque and
                    probabilidade >= LIMIAR
                )

                if correta:
                    if primeira_correta is None:
                        primeira_correta = tempo_predicao

                    consecutivas += 1

                    if consecutivas >= CONFIRMACOES:
                        confirmacao = tempo_predicao
                        break
                else:
                    consecutivas = 0
                    primeira_correta = None

            inicio = inicio_ataque[(ataque, seed)]

            resultados.append({
                "modelo": modelo,
                "ataque": ataque,
                "seed": seed,
                "attack_start_s": inicio,
                "detected": int(confirmacao is not None),
                "confirmation_time_s": confirmacao,
                "detection_delay_s":
                    None if confirmacao is None
                    else max(0.0, confirmacao - inicio),
                "required_consecutive_predictions":
                    CONFIRMACOES,
                "probability_threshold": LIMIAR,
            })

    for seed in range(1, 11):
        normal = pred[
            (pred["true_label"] == "normal") &
            (pred["seed"] == seed)
        ]

        falsos_alarmas.append({
            "modelo": modelo,
            "seed": seed,
            "normal_windows": len(normal),
            "false_alarms": int(
                (normal["predicted_label"] != "normal").sum()
            ),
            "false_alarm_rate": float(
                (normal["predicted_label"] != "normal").mean()
            ),
        })

resultado_df = pd.DataFrame(resultados)
falso_df = pd.DataFrame(falsos_alarmas)

resumo = (
    resultado_df.groupby(
        ["modelo", "ataque"],
        observed=True,
    )
    .agg(
        seeds=("seed", "count"),
        detections=("detected", "sum"),
        detection_rate=("detected", "mean"),
        delay_mean_s=("detection_delay_s", "mean"),
        delay_median_s=("detection_delay_s", "median"),
        delay_std_s=("detection_delay_s", "std"),
        delay_min_s=("detection_delay_s", "min"),
        delay_max_s=("detection_delay_s", "max"),
    )
    .reset_index()
)

resumo_falso = (
    falso_df.groupby("modelo", observed=True)
    .agg(
        false_alarm_rate_mean=(
            "false_alarm_rate",
            "mean",
        ),
        false_alarm_rate_std=(
            "false_alarm_rate",
            "std",
        ),
    )
    .reset_index()
)

resultado_df.to_csv(
    OUT / "tempo_deteccao_por_seed.csv",
    sep=";",
    index=False,
)

resumo.to_csv(
    OUT / "resumo_tempo_deteccao.csv",
    sep=";",
    index=False,
)

falso_df.to_csv(
    OUT / "falsos_alarmas_por_seed.csv",
    sep=";",
    index=False,
)

resumo_falso.to_csv(
    OUT / "resumo_falsos_alarmas.csv",
    sep=";",
    index=False,
)

print()
print("===== TEMPO DE DETECÇÃO =====")
print(resumo.to_string(index=False))

print()
print("===== FALSOS ALARMAS EM NORMAL =====")
print(resumo_falso.to_string(index=False))

print(f"\nResultados: {OUT}")
