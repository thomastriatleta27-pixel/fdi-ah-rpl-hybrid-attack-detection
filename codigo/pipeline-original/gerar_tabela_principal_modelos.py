import json
from pathlib import Path
import pandas as pd

BASE = Path("/home/joaorosa/contiki-ng/experimentos/final/ml/resultados_principal_4classes")
COMP = BASE / "comparacao_final"

ordem = ["XGBoost_60s", "LSTM", "GRU"]
diretorios = {
    "XGBoost_60s": BASE / "xgboost_60s",
    "LSTM": BASE / "lstm",
    "GRU": BASE / "gru",
}

resumo = pd.read_csv(COMP / "resumo_modelos.csv", sep=";")
classes = pd.read_csv(COMP / "metricas_por_classe.csv", sep=";")
tempo = pd.read_csv(COMP / "resumo_tempo_deteccao.csv", sep=";")
alertas = pd.read_csv(
    COMP / "resumo_falsos_alertas_operacionais.csv",
    sep=";",
)

linhas = []

for modelo in ordem:
    geral = resumo[resumo["modelo"] == modelo].iloc[0]
    classe = classes[classes["modelo"] == modelo]
    deteccao = tempo[tempo["modelo"] == modelo]
    alerta = alertas[alertas["modelo"] == modelo].iloc[0]

    with (
        diretorios[modelo] / "resumo_metricas.json"
    ).open(encoding="utf-8") as arquivo:
        metricas = json.load(arquivo)

    def valor_classe(nome, metrica):
        return classe.loc[
            classe["classe"] == nome,
            metrica,
        ].iloc[0]

    def atraso(ataque):
        return deteccao.loc[
            deteccao["ataque"] == ataque,
            "delay_mean_s",
        ].iloc[0]

    linhas.append({
        "modelo": modelo,
        "acuracia_media": geral["accuracy_media"],
        "acuracia_dp": geral["accuracy_dp"],
        "acuracia_ic95_inf": geral["accuracy_ic95_inf"],
        "acuracia_ic95_sup": geral["accuracy_ic95_sup"],
        "f1_macro_media": geral["f1_macro_media"],
        "f1_macro_dp": geral["f1_macro_dp"],
        "f1_normal": valor_classe("normal", "f1"),
        "f1_hybrid": valor_classe("hybrid", "f1"),
        "recall_hybrid": valor_classe("hybrid", "recall"),
        "f1_sinkhole": valor_classe("sinkhole", "f1"),
        "recall_sinkhole": valor_classe("sinkhole", "recall"),
        "f1_sybil": valor_classe("sybil", "f1"),
        "atraso_hybrid_s": atraso("hybrid"),
        "atraso_sinkhole_s": atraso("sinkhole"),
        "atraso_sybil_s": atraso("sybil"),
        "falsos_alertas_hora": alerta["falsos_alertas_por_hora"],
        "inferencia_ms_amostra":
            metricas["inference_ms_per_sample"]["media"],
    })

final = pd.DataFrame(linhas)

csv = COMP / "tabela_consolidada_modelos.csv"
tex = COMP / "tabela_consolidada_modelos.tex"

final.to_csv(csv, sep=";", index=False, float_format="%.6f")

tabela_tex = final[[
    "modelo",
    "acuracia_media",
    "f1_macro_media",
    "f1_hybrid",
    "recall_hybrid",
    "atraso_hybrid_s",
    "falsos_alertas_hora",
    "inferencia_ms_amostra",
]].rename(columns={
    "modelo": "Modelo",
    "acuracia_media": "Acurácia",
    "f1_macro_media": "F1 macro",
    "f1_hybrid": "F1 Hybrid",
    "recall_hybrid": "Recall Hybrid",
    "atraso_hybrid_s": "Atraso Hybrid (s)",
    "falsos_alertas_hora": "Falsos alertas/h",
    "inferencia_ms_amostra": "Inferência (ms)",
})

tabela_tex.to_latex(
    tex,
    index=False,
    float_format="%.3f",
    caption="Comparação consolidada dos modelos.",
    label="tab:comparacao_modelos",
)

print("===== TABELA CONSOLIDADA =====")
print(final.to_string(index=False))
print()
print(f"CSV: {csv}")
print(f"LaTeX: {tex}")
