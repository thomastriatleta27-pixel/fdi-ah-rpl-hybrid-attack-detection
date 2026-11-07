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

ATAQUES = ["sinkhole", "sybil", "hybrid"]
LIMIARES = [0.50, 0.60, 0.70, 0.80, 0.90]
CONFIRMACOES = [3, 6, 9, 12]

def detectado(grupo, ataque, limiar, confirmacoes):
    consecutivas = 0

    for linha in grupo.sort_values(
        "end_window"
    ).itertuples(index=False):
        correta = (
            linha.predicted_label == ataque and
            getattr(linha, f"prob_{ataque}") >= limiar
        )

        consecutivas = consecutivas + 1 if correta else 0

        if consecutivas >= confirmacoes:
            return True

    return False

def falsos_alertas(grupo, limiar, confirmacoes):
    classe_anterior = None
    consecutivas = 0
    alerta_ativo = False
    total = 0

    for linha in grupo.sort_values(
        "end_window"
    ).itertuples(index=False):
        classe = linha.predicted_label

        if classe == "normal":
            classe_anterior = None
            consecutivas = 0
            alerta_ativo = False
            continue

        probabilidade = getattr(linha, f"prob_{classe}")

        if probabilidade < limiar:
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

        if consecutivas >= confirmacoes and not alerta_ativo:
            total += 1
            alerta_ativo = True

    return total

resultados = []

for modelo, diretorio in MODELOS.items():
    pred = pd.read_csv(
        diretorio / "predicoes_todos_folds.csv",
        sep=";",
    )

    for limiar in LIMIARES:
        for confirmacoes in CONFIRMACOES:
            linha = {
                "modelo": modelo,
                "limiar": limiar,
                "confirmacoes": confirmacoes,
            }

            for ataque in ATAQUES:
                sucessos = 0

                for seed in range(1, 11):
                    grupo = pred[
                        (pred["true_label"] == ataque) &
                        (pred["seed"] == seed)
                    ]

                    sucessos += int(
                        detectado(
                            grupo,
                            ataque,
                            limiar,
                            confirmacoes,
                        )
                    )

                linha[f"deteccoes_{ataque}"] = sucessos

            alertas = 0
            horas = 0

            for seed in range(1, 11):
                normal = pred[
                    (pred["true_label"] == "normal") &
                    (pred["seed"] == seed)
                ]

                alertas += falsos_alertas(
                    normal,
                    limiar,
                    confirmacoes,
                )

                horas += len(normal) * 10 / 3600

            linha["deteccoes_total"] = sum(
                linha[f"deteccoes_{a}"]
                for a in ATAQUES
            )

            linha["falsos_alertas_total"] = alertas
            linha["falsos_alertas_por_hora"] = (
                alertas / horas
            )

            resultados.append(linha)

df = pd.DataFrame(resultados)

df.to_csv(
    OUT / "analise_sensibilidade_alertas.csv",
    sep=";",
    index=False,
)

validas = df[
    (df["deteccoes_selective"] == 10) &
    (df["deteccoes_sinkhole"] == 10) &
    (df["deteccoes_sybil"] == 10)
].sort_values(
    ["modelo", "falsos_alertas_por_hora"]
)

print("===== POLÍTICAS COM 30/30 DETECÇÕES =====")
print(validas.groupby("modelo").head(5).to_string(index=False))

print(f"\nResultado completo: {OUT}")
