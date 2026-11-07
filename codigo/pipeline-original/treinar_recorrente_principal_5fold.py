import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

parser = argparse.ArgumentParser()
parser.add_argument(
    "--model",
    choices=["lstm", "gru"],
    required=True,
)
args = parser.parse_args()
model_type = args.model

BASE = Path("/home/joaorosa/contiki-ng")
NPZ = BASE / "experimentos/final/ml/dados/sequencias_principal_4classes_60s.npz"
OUT = BASE / f"experimentos/final/ml/resultados_principal_4classes/{model_type}"

CLASSES = np.array(["normal", "sinkhole", "sybil", "hybrid"])
OUT.mkdir(parents=True, exist_ok=True)

tf.config.threading.set_intra_op_parallelism_threads(8)
tf.config.threading.set_inter_op_parallelism_threads(2)

print("Carregando sequências...")
dados = np.load(NPZ)

X = dados["X"]
y = dados["y"]
groups = dados["groups"]
windows = dados["windows"]

print(f"X: {X.shape}")
print(f"y: {y.shape}")
print(f"Modelo: {model_type.upper()}")

def transformar(array, imputer, scaler):
    formato = array.shape
    plano = array.reshape(-1, formato[-1])
    plano = imputer.transform(plano)
    plano = scaler.transform(plano)
    return plano.reshape(formato).astype(np.float32)

def criar_modelo():
    tf.keras.backend.clear_session()

    entrada = tf.keras.layers.Input(
        shape=(X.shape[1], X.shape[2])
    )

    if model_type == "lstm":
        camada = tf.keras.layers.LSTM(64)(entrada)
    else:
        camada = tf.keras.layers.GRU(64)(entrada)

    camada = tf.keras.layers.Dropout(0.30)(camada)
    camada = tf.keras.layers.Dense(32, activation="relu")(camada)
    camada = tf.keras.layers.Dropout(0.20)(camada)
    saida = tf.keras.layers.Dense(
        len(CLASSES),
        activation="softmax",
    )(camada)

    modelo = tf.keras.Model(entrada, saida)

    modelo.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=0.001
        ),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )

    return modelo

gkf = GroupKFold(n_splits=5)

metricas = []
predicoes = []
matriz_total = np.zeros((4, 4), dtype=np.int64)

for fold, (train_val_idx, test_idx) in enumerate(
    gkf.split(X, y, groups),
    start=1,
):
    tf.keras.utils.set_random_seed(42 + fold)

    seeds_disponiveis = sorted(
        np.unique(groups[train_val_idx]).tolist()
    )

    val_seed = seeds_disponiveis[-1]

    fit_idx = train_val_idx[
        groups[train_val_idx] != val_seed
    ]

    val_idx = train_val_idx[
        groups[train_val_idx] == val_seed
    ]

    train_seeds = sorted(np.unique(groups[fit_idx]).tolist())
    test_seeds = sorted(np.unique(groups[test_idx]).tolist())

    print()
    print(f"===== {model_type.upper()} FOLD {fold} =====")
    print(f"Treino: seeds {train_seeds}")
    print(f"Validação: seed {val_seed}")
    print(f"Teste: seeds {test_seeds}")

    plano_treino = X[fit_idx].reshape(
        -1,
        X.shape[-1],
    )

    imputer = SimpleImputer(
        strategy="median",
        keep_empty_features=True,
    )

    scaler = StandardScaler()

    plano_treino = imputer.fit_transform(plano_treino)
    scaler.fit(plano_treino)

    X_train = transformar(
        X[fit_idx],
        imputer,
        scaler,
    )

    X_val = transformar(
        X[val_idx],
        imputer,
        scaler,
    )

    X_test = transformar(
        X[test_idx],
        imputer,
        scaler,
    )

    modelo = criar_modelo()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=5,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=2,
            min_lr=1e-5,
        ),
    ]

    inicio_treino = time.perf_counter()

    historico = modelo.fit(
        X_train,
        y[fit_idx],
        validation_data=(X_val, y[val_idx]),
        epochs=30,
        batch_size=128,
        callbacks=callbacks,
        verbose=2,
        shuffle=True,
    )

    tempo_treino = time.perf_counter() - inicio_treino

    inicio_inferencia = time.perf_counter()

    probabilidades = modelo.predict(
        X_test,
        batch_size=256,
        verbose=0,
    )

    tempo_inferencia = time.perf_counter() - inicio_inferencia
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

    epochs_executadas = len(historico.history["loss"])

    metricas.append({
        "fold": fold,
        "train_seeds": "-".join(map(str, train_seeds)),
        "validation_seed": val_seed,
        "test_seeds": "-".join(map(str, test_seeds)),
        "train_samples": len(fit_idx),
        "validation_samples": len(val_idx),
        "test_samples": len(test_idx),
        "epochs": epochs_executadas,
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
        historico.history
    ).to_csv(
        OUT / f"historico_fold{fold}.csv",
        sep=";",
        index=False,
    )

    pd.DataFrame(
        matriz,
        index=CLASSES,
        columns=CLASSES,
    ).to_csv(
        OUT / f"matriz_confusao_fold{fold}.csv",
        sep=";",
    )

    modelo.save(OUT / f"modelo_{model_type}_fold{fold}.keras")

    joblib.dump(
        {
            "imputer": imputer,
            "scaler": scaler,
        },
        OUT / f"preprocessamento_fold{fold}.joblib",
    )

    print(f"Acurácia: {accuracy:.6f}")
    print(f"F1 macro: {f1:.6f}")
    print(f"Épocas: {epochs_executadas}")
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

colunas_resumo = [
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
    for coluna in colunas_resumo
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
        "epochs",
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
