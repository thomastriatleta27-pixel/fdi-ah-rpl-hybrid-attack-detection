import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)

BASE = Path("/home/joaorosa/contiki-ng")
RESULTADOS = BASE / "experimentos/final/ml/resultados_principal_4classes"
OUT = RESULTADOS / "comparacao_final"
OUT.mkdir(parents=True, exist_ok=True)

MODELOS = {
    "XGBoost_60s": RESULTADOS / "xgboost_60s",
    "LSTM": RESULTADOS / "lstm",
    "GRU": RESULTADOS / "gru",
}

CLASSES = ["normal", "sinkhole", "sybil", "hybrid"]
LABELS = list(range(4))

por_seed = []
por_classe = []
resumo = []

for modelo, diretorio in MODELOS.items():
    pred = pd.read_csv(
        diretorio / "predicoes_todos_folds.csv",
        sep=";",
    )

    if len(pred) != 14160:
        raise ValueError(
            f"{modelo}: {len(pred)} predições; esperado 14160"
        )

    for seed, grupo in pred.groupby("seed", sort=True):
        precision, recall, f1, _ = (
            precision_recall_fscore_support(
                grupo["true_id"],
                grupo["predicted_id"],
                labels=LABELS,
                average="macro",
                zero_division=0,
            )
        )

        por_seed.append({
            "modelo": modelo,
            "seed": int(seed),
            "accuracy": accuracy_score(
                grupo["true_id"],
                grupo["predicted_id"],
            ),
            "precision_macro": precision,
            "recall_macro": recall,
            "f1_macro": f1,
        })

    precision, recall, f1, suporte = (
        precision_recall_fscore_support(
            pred["true_id"],
            pred["predicted_id"],
            labels=LABELS,
            average=None,
            zero_division=0,
        )
    )

    for i, classe in enumerate(CLASSES):
        por_classe.append({
            "modelo": modelo,
            "classe": classe,
            "precision": precision[i],
            "recall": recall[i],
            "f1": f1[i],
            "suporte": int(suporte[i]),
        })

seed_df = pd.DataFrame(por_seed)
classe_df = pd.DataFrame(por_classe)

rng = np.random.default_rng(42)

for modelo in MODELOS:
    dados = seed_df[seed_df["modelo"] == modelo]

    linha = {"modelo": modelo}

    for metrica in ["accuracy", "f1_macro"]:
        valores = dados[metrica].to_numpy()

        medias_bootstrap = np.mean(
            rng.choice(
                valores,
                size=(100000, len(valores)),
                replace=True,
            ),
            axis=1,
        )

        linha[f"{metrica}_media"] = valores.mean()
        linha[f"{metrica}_dp"] = valores.std(ddof=1)
        linha[f"{metrica}_ic95_inf"] = np.percentile(
            medias_bootstrap,
            2.5,
        )
        linha[f"{metrica}_ic95_sup"] = np.percentile(
            medias_bootstrap,
            97.5,
        )

    resumo.append(linha)

resumo_df = pd.DataFrame(resumo)

def matriz_metrica(metrica):
    return seed_df.pivot(
        index="seed",
        columns="modelo",
        values=metrica,
    ).sort_index()

testes = []

for metrica in ["accuracy", "f1_macro"]:
    matriz = matriz_metrica(metrica)

    friedman = stats.friedmanchisquare(
        *[matriz[m].to_numpy() for m in MODELOS]
    )

    testes.append({
        "metrica": metrica,
        "teste": "Friedman",
        "comparacao": "todos",
        "estatistica": friedman.statistic,
        "p_valor": friedman.pvalue,
        "p_holm": friedman.pvalue,
    })

    pares = []

    for modelo_a, modelo_b in combinations(MODELOS, 2):
        teste = stats.wilcoxon(
            matriz[modelo_a],
            matriz[modelo_b],
            alternative="two-sided",
        )

        pares.append({
            "metrica": metrica,
            "teste": "Wilcoxon_pareado",
            "comparacao": f"{modelo_a}_vs_{modelo_b}",
            "estatistica": teste.statistic,
            "p_valor": teste.pvalue,
        })

    ordem = sorted(
        range(len(pares)),
        key=lambda i: pares[i]["p_valor"],
    )

    ajustados = [0.0] * len(pares)
    max_anterior = 0.0
    quantidade = len(pares)

    for posicao, indice in enumerate(ordem):
        ajustado = min(
            1.0,
            pares[indice]["p_valor"] *
            (quantidade - posicao),
        )
        ajustado = max(ajustado, max_anterior)
        ajustados[indice] = ajustado
        max_anterior = ajustado

    for indice, par in enumerate(pares):
        par["p_holm"] = ajustados[indice]
        testes.append(par)

testes_df = pd.DataFrame(testes)

seed_df.to_csv(
    OUT / "metricas_por_seed.csv",
    sep=";",
    index=False,
)

classe_df.to_csv(
    OUT / "metricas_por_classe.csv",
    sep=";",
    index=False,
)

resumo_df.to_csv(
    OUT / "resumo_modelos.csv",
    sep=";",
    index=False,
)

testes_df.to_csv(
    OUT / "testes_estatisticos.csv",
    sep=";",
    index=False,
)

print("===== RESUMO =====")
print(resumo_df.to_string(index=False))

print()
print("===== MÉTRICAS POR CLASSE =====")
print(classe_df.to_string(index=False))

print()
print("===== TESTES ESTATÍSTICOS =====")
print(testes_df.to_string(index=False))

print(f"\nResultados: {OUT}")
