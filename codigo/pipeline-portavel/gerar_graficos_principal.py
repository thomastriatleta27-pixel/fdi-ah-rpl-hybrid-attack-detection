import matplotlib
matplotlib.use("Agg")

from pathlib import Path
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

BASE = Path(os.environ.get("CONTIKI_NG_ROOT", Path.home() / "contiki-ng")).expanduser().resolve() / "experimentos/final/ml/resultados_principal_4classes"
COMP = BASE / "comparacao_final"
OUT = COMP / "graficos"
OUT.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")
cores = {
    "XGBoost_60s": "#4C78A8",
    "LSTM": "#F58518",
    "GRU": "#54A24B",
}

# 1. Desempenho geral com IC95%
df = pd.read_csv(COMP / "resumo_modelos.csv", sep=";")
modelos = df["modelo"].tolist()
x = np.arange(len(modelos))
largura = 0.34

fig, ax = plt.subplots(figsize=(10, 6))

for deslocamento, metrica, nome in [
    (-largura / 2, "accuracy", "Acurácia"),
    (largura / 2, "f1_macro", "F1 macro"),
]:
    medias = df[f"{metrica}_media"].to_numpy()
    inferior = df[f"{metrica}_ic95_inf"].to_numpy()
    superior = df[f"{metrica}_ic95_sup"].to_numpy()

    ax.bar(
        x + deslocamento,
        medias,
        largura,
        label=nome,
        yerr=[medias - inferior, superior - medias],
        capsize=5,
    )

ax.set_xticks(x, modelos)
ax.set_ylim(0.35, 0.75)
ax.set_ylabel("Pontuação")
ax.set_title("Desempenho médio com IC95% — validação por seed")
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "01_desempenho_modelos.png", dpi=300)
fig.savefig(OUT / "01_desempenho_modelos.pdf")
plt.close(fig)

# 2. F1 por classe
classe = pd.read_csv(COMP / "metricas_por_classe.csv", sep=";")
pivot = classe.pivot(index="classe", columns="modelo", values="f1")
pivot = pivot.reindex(["normal", "sinkhole", "sybil", "hybrid"])
pivot = pivot.reindex(columns=modelos)

fig, ax = plt.subplots(figsize=(11, 6))
pivot.plot(
    kind="bar",
    ax=ax,
    color=[cores.get(m) for m in pivot.columns],
)
ax.set_ylim(0, 1.05)
ax.set_xlabel("Classe")
ax.set_ylabel("F1-score")
ax.set_title("F1-score por classe")
ax.tick_params(axis="x", rotation=0)
ax.legend(title="Modelo")
fig.tight_layout()
fig.savefig(OUT / "02_f1_por_classe.png", dpi=300)
fig.savefig(OUT / "02_f1_por_classe.pdf")
plt.close(fig)

# 3. Matrizes de confusão normalizadas
diretorios = {
    "XGBoost 60 s": BASE / "xgboost_60s",
    "LSTM": BASE / "lstm",
    "GRU": BASE / "gru",
}

fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

for ax, (nome, diretorio) in zip(axes, diretorios.items()):
    matriz = pd.read_csv(
        diretorio / "matriz_confusao_total.csv",
        sep=";",
        index_col=0,
    )
    normalizada = matriz.div(matriz.sum(axis=1), axis=0) * 100

    sns.heatmap(
        normalizada,
        annot=True,
        fmt=".1f",
        cmap="Blues",
        vmin=0,
        vmax=100,
        cbar=False,
        ax=ax,
    )
    ax.set_title(nome)
    ax.set_xlabel("Classe predita")
    ax.set_ylabel("Classe real")

fig.suptitle("Matrizes de confusão normalizadas (%)", y=1.02)
fig.tight_layout()
fig.savefig(OUT / "03_matrizes_confusao.png", dpi=300, bbox_inches="tight")
fig.savefig(OUT / "03_matrizes_confusao.pdf", bbox_inches="tight")
plt.close(fig)

# 4. Tempo de detecção — política primária 0,50/k=3
tempo = pd.read_csv(COMP / "resumo_tempo_deteccao.csv", sep=";")

fig, ax = plt.subplots(figsize=(11, 6))
sns.barplot(
    data=tempo,
    x="ataque",
    y="delay_mean_s",
    hue="modelo",
    hue_order=modelos,
    palette=cores,
    ax=ax,
)
ax.set_xlabel("Ataque")
ax.set_ylabel("Atraso médio (s)")
ax.set_title("Tempo médio de detecção — limiar 0,50 e k=3")
ax.legend(title="Modelo")
fig.tight_layout()
fig.savefig(OUT / "04_tempo_deteccao.png", dpi=300)
fig.savefig(OUT / "04_tempo_deteccao.pdf")
plt.close(fig)

# 5. Trade-off operacional do XGBoost
trade = pd.read_csv(
    COMP / "comparacao_politicas_xgboost.csv",
    sep=";",
)

trade = (
    trade.groupby(
        ["limiar", "confirmacoes"],
        observed=True,
    )
    .agg(
        falsos_alertas_hora=(
            "falsos_alertas_hora",
            "first",
        ),
        atraso_medio_ataques_s=(
            "atraso_medio_s",
            "mean",
        ),
    )
    .reset_index()
)

fig, ax = plt.subplots(figsize=(10, 7))

ax.scatter(
    trade["falsos_alertas_hora"],
    trade["atraso_medio_ataques_s"],
    s=120,
    color=cores["XGBoost_60s"],
)

for linha in trade.itertuples(index=False):
    ax.annotate(
        f"L={linha.limiar:.1f}, k={linha.confirmacoes}",
        (
            linha.falsos_alertas_hora,
            linha.atraso_medio_ataques_s,
        ),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=10,
    )

ax.set_xlabel("Falsos alertas por hora")
ax.set_ylabel("Atraso médio dos ataques (s)")
ax.set_title(
    "Trade-off operacional do XGBoost"
)

fig.tight_layout()
fig.savefig(
    OUT / "05_tradeoff_xgboost.png",
    dpi=300,
)
fig.savefig(
    OUT / "05_tradeoff_xgboost.pdf",
)
plt.close(fig)

print("===== GRÁFICOS GERADOS =====")
for arquivo in sorted(OUT.iterdir()):
    print(arquivo.name)
