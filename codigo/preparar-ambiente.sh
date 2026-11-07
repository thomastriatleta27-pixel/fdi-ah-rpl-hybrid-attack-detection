#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

REPO_ROOT="$(
    cd "$SCRIPT_DIR/.."
    pwd
)"

CONTIKI_NG_ROOT="${CONTIKI_NG_ROOT:-$HOME/contiki-ng}"
DEPLOY_ROOT="$CONTIKI_NG_ROOT/experimentos/final"

if [ ! -d "$CONTIKI_NG_ROOT/tools/cooja" ]; then
    echo "ERRO: diretório do Cooja não encontrado:"
    echo "$CONTIKI_NG_ROOT/tools/cooja"
    echo
    echo "Informe a localização do Contiki-NG com:"
    echo "CONTIKI_NG_ROOT=/caminho/contiki-ng $0"
    exit 1
fi

instalar_projeto() {
    origem="$1"
    destino="$2"
    shift 2

    mkdir -p "$destino"

    for arquivo in "$@"; do
        install -m 0644 \
            "$origem/$arquivo" \
            "$destino/$arquivo"
    done
}

echo "Instalando firmwares no Contiki-NG..."

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/normal" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah" \
    Makefile fdi-ah.c project-conf.h

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/sinkhole" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah-sinkhole" \
    Makefile fdi-ah-sinkhole.c project-conf.h

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/sybil" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah-sybil" \
    Makefile fdi-ah-sybil.c project-conf.h

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/hybrid" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah-hybrid" \
    Makefile fdi-ah-hybrid.c project-conf.h

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/baseline" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah-baseline" \
    Makefile fdi-ah-baseline.c project-conf.h

instalar_projeto \
    "$REPO_ROOT/codigo/firmware/baseline-measure" \
    "$CONTIKI_NG_ROOT/examples/fdi-ah-baseline-measure" \
    Makefile fdi-ah-baseline-measure.c project-conf.h

PATCH="$REPO_ROOT/codigo/contiki-ng-patch/contiki-ng-alteracoes.patch"

if [ -s "$PATCH" ]; then
    echo "Verificando alterações do Contiki-NG..."

    if git -C "$CONTIKI_NG_ROOT" apply --check "$PATCH"; then
        git -C "$CONTIKI_NG_ROOT" apply "$PATCH"
        echo "Patch aplicado."
    elif git -C "$CONTIKI_NG_ROOT" apply --reverse --check "$PATCH"; then
        echo "Patch já se encontra aplicado."
    else
        echo "ERRO: o patch não pode ser aplicado nem identificado como já aplicado."
        echo "Verifique se está sendo utilizada a versão correta do Contiki-NG."
        exit 1
    fi
fi

mkdir -p \
    "$DEPLOY_ROOT/csc" \
    "$DEPLOY_ROOT/scripts" \
    "$DEPLOY_ROOT/logs/definitivo/normal" \
    "$DEPLOY_ROOT/logs/definitivo/sinkhole" \
    "$DEPLOY_ROOT/logs/definitivo/sybil" \
    "$DEPLOY_ROOT/logs/definitivo/hybrid" \
    "$DEPLOY_ROOT/logs/definitivo/execution-status"

echo "Instalando cenários e scripts do Cooja..."

for cenario in normal sinkhole sybil hybrid; do
    cp -v \
        "$REPO_ROOT/cooja/cenarios/$cenario/"*.csc \
        "$DEPLOY_ROOT/csc/"

    for origem_js in "$REPO_ROOT/cooja/scripts/$cenario/"*.js; do
        nome_js="$(basename "$origem_js")"
        destino_js="$DEPLOY_ROOT/scripts/$nome_js"

        sed \
            "s#/home/joaorosa/contiki-ng/experimentos/final#$DEPLOY_ROOT#g" \
            "$origem_js" \
            > "$destino_js"
    done
done

echo "Compilando os firmwares..."

for projeto in \
    fdi-ah \
    fdi-ah-sinkhole \
    fdi-ah-sybil \
    fdi-ah-hybrid \
    fdi-ah-baseline \
    fdi-ah-baseline-measure
do
    make \
        -C "$CONTIKI_NG_ROOT/examples/$projeto" \
        TARGET=sky
done

echo
echo "Ambiente preparado com sucesso."
echo "Contiki-NG: $CONTIKI_NG_ROOT"
echo "Experimentos: $DEPLOY_ROOT"
