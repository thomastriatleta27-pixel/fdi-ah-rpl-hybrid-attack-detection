#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

EXECUTOR="$SCRIPT_DIR/executar-cenario.sh"

CONTIKI_NG_ROOT="${CONTIKI_NG_ROOT:-$HOME/contiki-ng}"
SEED_INICIAL="${SEED_INICIAL:-1}"
SEED_FINAL="${SEED_FINAL:-10}"

mostrar_uso() {
    cat <<EOF
Uso:
  $0 --executar

Este script executa os quatro cenários experimentais:
  normal, sinkhole, sybil e hybrid.

Por padrão, são executadas as seeds de 1 a 10, totalizando
40 simulações de 3.600 segundos.

Variáveis opcionais:
  CONTIKI_NG_ROOT=/caminho/contiki-ng
  SEED_INICIAL=1
  SEED_FINAL=10

Exemplo para executar somente a seed 1:
  SEED_INICIAL=1 SEED_FINAL=1 $0 --executar

ATENÇÃO:
  resultados existentes não serão sobrescritos.
EOF
}

if [ "${1:-}" != "--executar" ]; then
    mostrar_uso
    exit 0
fi

if [ ! -x "$EXECUTOR" ]; then
    echo "ERRO: executor não encontrado ou sem permissão:"
    echo "$EXECUTOR"
    exit 1
fi

if ! [[ "$SEED_INICIAL" =~ ^[0-9]+$ ]] ||
   ! [[ "$SEED_FINAL" =~ ^[0-9]+$ ]]; then
    echo "ERRO: SEED_INICIAL e SEED_FINAL devem ser números inteiros."
    exit 1
fi

if [ "$SEED_INICIAL" -gt "$SEED_FINAL" ]; then
    echo "ERRO: SEED_INICIAL não pode ser maior que SEED_FINAL."
    exit 1
fi

export CONTIKI_NG_ROOT
export SEED_INICIAL
export SEED_FINAL

CENARIOS=(
    normal
    sinkhole
    sybil
    hybrid
)

echo "============================================================"
echo "Reprodução dos experimentos FDI-AH"
echo "Contiki-NG: $CONTIKI_NG_ROOT"
echo "Seeds: $SEED_INICIAL até $SEED_FINAL"
echo "Cenários: ${CENARIOS[*]}"
echo "============================================================"

for cenario in "${CENARIOS[@]}"; do
    echo
    echo "============================================================"
    echo "Executando cenário: $cenario"
    echo "============================================================"

    "$EXECUTOR" "$cenario"
done

echo
echo "============================================================"
echo "Todos os cenários solicitados foram executados e validados."
echo "============================================================"
