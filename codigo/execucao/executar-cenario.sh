#!/usr/bin/env bash

set -euo pipefail

mostrar_uso() {
    echo "Uso:"
    echo "  $0 normal"
    echo "  $0 sinkhole"
    echo "  $0 sybil"
    echo "  $0 hybrid"
    echo
    echo "Variáveis opcionais:"
    echo "  CONTIKI_NG_ROOT=/caminho/contiki-ng"
    echo "  SEED_INICIAL=1"
    echo "  SEED_FINAL=10"
}

CENARIO="${1:-}"

case "$CENARIO" in
    normal|sinkhole|sybil|hybrid)
        ;;
    *)
        mostrar_uso
        exit 2
        ;;
esac

CONTIKI_NG_ROOT="${CONTIKI_NG_ROOT:-$HOME/contiki-ng}"
DEPLOY_ROOT="$CONTIKI_NG_ROOT/experimentos/final"
COOJA="$CONTIKI_NG_ROOT/tools/cooja"
CSC_DIR="$DEPLOY_ROOT/csc"
LOG_DIR="$DEPLOY_ROOT/logs/definitivo/$CENARIO"
RUN_DIR="$DEPLOY_ROOT/logs/definitivo/execution-status"

SEED_INICIAL="${SEED_INICIAL:-1}"
SEED_FINAL="${SEED_FINAL:-10}"

if [ ! -d "$COOJA" ]; then
    echo "ERRO: Cooja não encontrado em:"
    echo "$COOJA"
    exit 1
fi

mkdir -p "$LOG_DIR" "$RUN_DIR"

cd "$COOJA"

for NUMERO in $(seq "$SEED_INICIAL" "$SEED_FINAL"); do
    SEED="$(printf '%02d' "$NUMERO")"

    CSC="$CSC_DIR/definitivo-$CENARIO-seed${SEED}-3600s.csc"
    DATA_LOG="$LOG_DIR/definitivo-$CENARIO-seed${SEED}-3600s.log"
    RUN_LOG="$RUN_DIR/$CENARIO-seed${SEED}-cooja.log"

    echo
    echo "Iniciando cenário=$CENARIO seed=$SEED"
    date -u '+%Y-%m-%dT%H:%M:%SZ'

    if [ ! -f "$CSC" ]; then
        echo "ERRO: cenário não encontrado:"
        echo "$CSC"
        exit 1
    fi

    if [ -e "$DATA_LOG" ] || [ -e "$RUN_LOG" ]; then
        echo "ERRO: já existe um arquivo de resultado para esta seed."
        echo "DATA_LOG=$DATA_LOG"
        echo "RUN_LOG=$RUN_LOG"
        echo "Os resultados existentes não serão sobrescritos."
        exit 1
    fi

    if ! ./gradlew --no-daemon run \
        --args="--no-gui --autostart $CSC" \
        > "$RUN_LOG" 2>&1
    then
        echo "ERRO: falha na execução do Cooja."
        echo "Consulte: $RUN_LOG"
        exit 1
    fi

    if ! grep -Fq "TEST OK" "$RUN_LOG" ||
       ! grep -Fq "BUILD SUCCESSFUL" "$RUN_LOG"
    then
        echo "ERRO: execução não foi concluída corretamente."
        echo "Consulte: $RUN_LOG"
        exit 1
    fi

    if [ ! -s "$DATA_LOG" ]; then
        echo "ERRO: o log de dados não foi produzido."
        echo "$DATA_LOG"
        exit 1
    fi

    ENERGY="$(
        grep -F -c "FDI_METRIC,ENERGY" "$DATA_LOG" || true
    )"

    SINKHOLE="$(
        grep -F -c "FDI_ATTACK,SINKHOLE" "$DATA_LOG" || true
    )"

    SYBIL="$(
        grep -F -c "FDI_ATTACK,SYBIL" "$DATA_LOG" || true
    )"

    TX="$(
        grep -F -c "FDI_DATA,TX" "$DATA_LOG" || true
    )"

    RX="$(
        grep -F -c "FDI_DATA,RX" "$DATA_LOG" || true
    )"

    if [ "$ENERGY" -ne 10770 ]; then
        echo "ERRO: quantidade inesperada de registros ENERGY."
        echo "Esperado=10770 Obtido=$ENERGY"
        exit 1
    fi

    case "$CENARIO" in
        normal)
            if [ "$SINKHOLE" -ne 0 ] || [ "$SYBIL" -ne 0 ]; then
                echo "ERRO: eventos de ataque encontrados no cenário normal."
                exit 1
            fi
            ;;

        sinkhole)
            if [ "$SINKHOLE" -eq 0 ] || [ "$SYBIL" -ne 0 ]; then
                echo "ERRO: assinatura Sinkhole incompatível."
                exit 1
            fi
            ;;

        sybil)
            if [ "$SINKHOLE" -ne 0 ] || [ "$SYBIL" -ne 3 ]; then
                echo "ERRO: assinatura Sybil incompatível."
                exit 1
            fi
            ;;

        hybrid)
            if [ "$SINKHOLE" -eq 0 ] || [ "$SYBIL" -ne 3 ]; then
                echo "ERRO: assinatura Hybrid incompatível."
                exit 1
            fi
            ;;
    esac

    echo "Execução validada:"
    echo "cenario=$CENARIO seed=$SEED ENERGY=$ENERGY SINKHOLE=$SINKHOLE SYBIL=$SYBIL TX=$TX RX=$RX"
done

echo
echo "Todas as seeds solicitadas foram concluídas."
echo "Cenário: $CENARIO"
echo "Seeds: $SEED_INICIAL até $SEED_FINAL"
