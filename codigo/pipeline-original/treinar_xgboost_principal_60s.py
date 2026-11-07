import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupKFold

BASE = Path("/home/joaorosa/contiki-ng")
NPZ = BASE / "experimentos/final/ml/dados/sequencias_principal_4classes_60s.npz"
CONFIG = BASE / "experimentos/final/ml/dados/sequencias_principal_4classes_60s.json"
OUT = BASE / "experimentos/final/ml/resultados_principal_4classes/xgboost_60s"

CLASSES = np.array(["normal", "sinkhole", "sybil", "hybrid"])
OUT.mkdir(parents=True, exist_ok=True)

print("Carregando sequências...")
dados = np.load(NPZ)
X_seq = dados["X"]
y = dados["y"]
groups = dados["groups"]
windows = dados["windows"]

X = X_seq.reshape(len(X_seq), -1)

with CONFIG.open(encoding="utf-8") as f:
    configuracao = json.load(f)

features_originais = configuracao["features"]
feature_names = []

for passo in range(X_seq.shape[1]):
    deslocamento = passo - X_seq.shape[1] + 1

    for feature in features_originais:
        feature_names.append(
            f"t{deslocamento}_{feature}"
        )

print(f"Sequências: {len(X)}")
print(f"Formato: {X.shape}")
print(f"NaN: {np.isnan(X).sum()}")

gkf = GroupKFold(n_splits=5)

metricas = []
predicoes = []
matriz_total = np.zeros((4, 4), dtype=np.int64)
importancias = np.zeros(X.shape[1], dtype=np.float64)

for fold, (train_idx, test_idx) in enumerate(
    gkf.split(X, y, groups),
    start=1,
):
    train_seeds = sorted(np.unique(groups[train_idx]).tolist())
    test_seeds = sorted(np.unique(groups[test_idx]).tolist())

    print()
    print(f"===== XGBOOST 60S FOLD {fold} =====")
    print(f"Treino: seeds {train_seeds}")
    print(f"Teste: seeds {test_seeds}")

    modelo = xgb.XGBClassifier(
        objective="multi:softprob",
        num_class=4,
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        reg_alpha=0.0,
        reg_lambda=1.0,
        tree_method="hist",
        n_jobs=8,
        random_state=42,
        eval_metric="mlogloss",
    )

    inicio = time.perf_counter()
    modelo.fit(X[train_idx], y[train_idx])
    tempo_treino = time.perf_counter() - inicio

    inicio = time.perf_counter()
    probabilidades = modelo.predict_proba(X[test_idx])
    tempo_inferencia = time.perf_counter() - inicio

    pred = probabilidades.argmax(axis=1)

    accuracy = accuracy_score(y[test_idx], pred)
    balanced = balanced_accuracy_score(y[test_idx], pred)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y[test_idx],
        pred,
        average="macro",
        zero_division=0,
    )

    matriz = confusion_matrix(
        y[test_idx],
        pred,
        labels=np.arange(4),
    )

    matriz_total += matriz
    importancias += modelo.feature_importances_

    metricas.append({
        "fold": fold,
        "train_seeds": "-".join(map(str, train_seeds)),
        "test_seeds": "-".join(map(str, test_seeds)),
        "train_samples": len(train_idx),
        "test_samples": len(test_idx),
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "training_seconds": tempo_treino,
        "inference_seconds": tempo_inferencia,
        "inference_ms_per_sample":
            1000 * tempo_inferencia / len(test_idx),
    })

    fold_pred = pd.DataFrame({
        "fold": fold,
        "seed": groups[test_idx],
        "end_window": windows[test_idx],
        "true_id": y[test_idx],
        "predicted_id": pred,
        "true_label": CLASSES[y[test_idx]],
        "predicted_label": CLASSES[pred],
    })

    for classe_id, classe in enumerate(CLASSES):
        fold_pred[f"prob_{classe}"] = probabilidades[:, classe_id]

    predicoes.append(fold_pred)

    pd.DataFrame(
        matriz,
        index=CLASSES,
        columns=CLASSES,
    ).to_csv(
        OUT / f"matriz_confusao_fold{fold}.csv",
        sep=";",
    )

    modelo.save_model(
        OUT / f"modelo_xgboost_60s_fold{fold}.json"
    )

    print(f"Acurácia: {accuracy:.6f}")
    print(f"F1 macro: {f1:.6f}")
    print(f"Treinamento: {tempo_treino:.2f} s")

metricas_df = pd.DataFrame(metricas)

metricas_df.to_csv(
    OUT / "metricas_por_fold.csv",
    sep=";",
    index=False,
)

pd.concat(
    predicoes,
    ignore_index=True,
).to_csv(
    OUT / "predicoes_todos_folds.csv",
    sep=";",
    index=False,
)

pd.DataFrame(
    matriz_total,
    index=CLASSES,
    columns=CLASSES,
).to_csv(
    OUT / "matriz_confusao_total.csv",
    sep=";",
)

pd.DataFrame({
    "feature": feature_names,
    "importance_mean": importancias / 5,
}).sort_values(
    "importance_mean",
    ascending=False,
).to_csv(
    OUT / "importancia_features.csv",
    sep=";",
    index=False,
)

colunas = [
    "accuracy",
    "balanced_accuracy",
    "precision_macro",
    "recall_macro",
    "f1_macro",
    "training_seconds",
    "inference_ms_per_sample",
]

resumo = {
    coluna: {
        "media": float(metricas_df[coluna].mean()),
        "desvio_padrao": float(
            metricas_df[coluna].std(ddof=1)
        ),
    }
    for coluna in colunas
}

with (
    OUT / "resumo_metricas.json"
).open("w", encoding="utf-8") as f:
    json.dump(resumo, f, indent=2, ensure_ascii=False)

print()
print("===== RESULTADO FINAL =====")
print(metricas_df[
    [
        "fold",
        "test_seeds",
        "accuracy",
        "precision_macro",
        "recall_macro",
        "f1_macro",
    ]
].to_string(index=False))

print()
print("Médias:")
for nome, valores in resumo.items():
    print(
        f"{nome}: {valores['media']:.6f} "
        f"(DP={valores['desvio_padrao']:.6f})"
    )

print(f"\nResultados: {OUT}")
