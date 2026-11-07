#!/usr/bin/env bash

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CONTIKI_NG_ROOT="${CONTIKI_NG_ROOT:-$HOME/contiki-ng}"
LOG_ROOT="${LOG_ROOT:-$CONTIKI_NG_ROOT/experimentos/final/logs/definitivo}"
RELATORIO="${RELATORIO:-$REPO_ROOT/configs/validacao-logs-definitivos.tsv}"

mkdir -p "$(dirname "$RELATORIO")"

printf '%s\n' \
  $'CENARIO\tSEED\tSTATUS\tMOTIVOS\tARQUIVO\tTAMANHO_BYTES\tSHA256\tLINHAS\tNOS\tIDS_AUSENTES\tTIMESTAMP_MIN\tTIMESTAMP_MAX\tDURACAO_S\tSAMPLE_START\tSAMPLE_END\tENERGY\tSINKHOLE\tSYBIL\tTX\tRX\tATAQUES_FORA_NO16\tSTART_MIN_POR_NO\tSTART_MAX_POR_NO\tEND_MIN_POR_NO\tEND_MAX_POR_NO' \
  > "$RELATORIO"

TOTAL=0
APROVADOS=0
ERROS=0

for CENARIO in normal sinkhole sybil hybrid; do
    for NUMERO in $(seq -w 1 10); do
        TOTAL=$((TOTAL + 1))
        SEED=$((10#$NUMERO))
        ARQUIVO="$LOG_ROOT/$CENARIO/definitivo-$CENARIO-seed${NUMERO}-3600s.log"
        MOTIVOS=""

        registrar_erro() {
            if [ -n "$MOTIVOS" ]; then
                MOTIVOS="$MOTIVOS;"
            fi
            MOTIVOS="$MOTIVOS$1"
        }

        if [ ! -f "$ARQUIVO" ]; then
            registrar_erro "arquivo_ausente"

            printf '%s\t%s\tERRO\t%s\t%s\n' \
              "$CENARIO" "$SEED" "$MOTIVOS" "$ARQUIVO" \
              >> "$RELATORIO"

            echo "[ERRO] $CENARIO seed=$NUMERO: arquivo ausente"
            ERROS=$((ERROS + 1))
            continue
        fi

        IFS=$'\t' read -r \
          LINHAS NOS IDS_AUSENTES TIMESTAMP_MIN TIMESTAMP_MAX \
          SAMPLE_START SAMPLE_END ENERGY SINKHOLE SYBIL TX RX \
          ATAQUES_FORA_NO16 START_MIN START_MAX END_MIN END_MAX \
          < <(
            awk '
              BEGIN {
                timestamp_min = -1
                timestamp_max = 0
              }

              {
                linhas++
                timestamp = $1 + 0

                if (timestamp_min < 0 || timestamp < timestamp_min) {
                  timestamp_min = timestamp
                }

                if (timestamp > timestamp_max) {
                  timestamp_max = timestamp
                }

                id = 0

                if ($2 ~ /^ID:[0-9]+$/) {
                  split($2, partes, ":")
                  id = partes[2] + 0
                  ids[id] = 1
                }

                if (index($0, "FDI_SAMPLE_START")) {
                  sample_start++
                  if (id > 0) start_por_no[id]++
                }

                if (index($0, "FDI_SAMPLE_END")) {
                  sample_end++
                  if (id > 0) end_por_no[id]++
                }

                if (index($0, "FDI_METRIC,ENERGY")) energy++
                if (index($0, "FDI_ATTACK,SINKHOLE")) sinkhole++
                if (index($0, "FDI_ATTACK,SYBIL")) sybil++
                if (index($0, "FDI_DATA,TX")) tx++
                if (index($0, "FDI_DATA,RX")) rx++

                if (index($0, "FDI_ATTACK,") && id != 16) {
                  ataques_fora_no16++
                }
              }

              END {
                nos = 0
                for (id in ids) nos++

                ids_ausentes = 0
                start_min = 999999
                start_max = -1
                end_min = 999999
                end_max = -1

                for (id = 1; id <= 30; id++) {
                  if (!(id in ids)) ids_ausentes++

                  inicio = ((id in start_por_no) ? start_por_no[id] : 0)
                  fim = ((id in end_por_no) ? end_por_no[id] : 0)

                  if (inicio < start_min) start_min = inicio
                  if (inicio > start_max) start_max = inicio
                  if (fim < end_min) end_min = fim
                  if (fim > end_max) end_max = fim
                }

                printf "%.0f\t%d\t%d\t%.0f\t%.0f\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n", \
                  linhas, nos, ids_ausentes, timestamp_min, timestamp_max, \
                  sample_start, sample_end, energy, sinkhole, sybil, tx, rx, \
                  ataques_fora_no16, start_min, start_max, end_min, end_max
              }
            ' "$ARQUIVO"
          )

        [ "$NOS" -eq 30 ] ||
            registrar_erro "nos=$NOS"

        [ "$IDS_AUSENTES" -eq 0 ] ||
            registrar_erro "ids_ausentes=$IDS_AUSENTES"

        [ "$SAMPLE_START" -eq 10770 ] ||
            registrar_erro "sample_start=$SAMPLE_START"

        [ "$SAMPLE_END" -eq 10770 ] ||
            registrar_erro "sample_end=$SAMPLE_END"

        [ "$ENERGY" -eq 10770 ] ||
            registrar_erro "energy=$ENERGY"

        [ "$START_MIN" -eq 359 ] ||
            registrar_erro "start_min=$START_MIN"

        [ "$START_MAX" -eq 359 ] ||
            registrar_erro "start_max=$START_MAX"

        [ "$END_MIN" -eq 359 ] ||
            registrar_erro "end_min=$END_MIN"

        [ "$END_MAX" -eq 359 ] ||
            registrar_erro "end_max=$END_MAX"

        [ "$ATAQUES_FORA_NO16" -eq 0 ] ||
            registrar_erro "ataques_fora_no16=$ATAQUES_FORA_NO16"

        [ "$TX" -gt 0 ] ||
            registrar_erro "tx=$TX"

        [ "$RX" -gt 0 ] ||
            registrar_erro "rx=$RX"

        if [ "$TIMESTAMP_MAX" -lt 3590000000 ] ||
           [ "$TIMESTAMP_MAX" -gt 3605000000 ]; then
            registrar_erro "timestamp_max=$TIMESTAMP_MAX"
        fi

        case "$CENARIO" in
          normal)
            [ "$SINKHOLE" -eq 0 ] ||
                registrar_erro "sinkhole=$SINKHOLE"

            [ "$SYBIL" -eq 0 ] ||
                registrar_erro "sybil=$SYBIL"
            ;;

          sinkhole)
            [ "$SINKHOLE" -gt 0 ] ||
                registrar_erro "sinkhole=$SINKHOLE"

            [ "$SYBIL" -eq 0 ] ||
                registrar_erro "sybil=$SYBIL"
            ;;

          sybil)
            [ "$SINKHOLE" -eq 0 ] ||
                registrar_erro "sinkhole=$SINKHOLE"

            [ "$SYBIL" -eq 3 ] ||
                registrar_erro "sybil=$SYBIL"
            ;;

          hybrid)
            [ "$SINKHOLE" -gt 0 ] ||
                registrar_erro "sinkhole=$SINKHOLE"

            [ "$SYBIL" -eq 3 ] ||
                registrar_erro "sybil=$SYBIL"
            ;;
        esac

        TAMANHO_BYTES="$(stat -c '%s' "$ARQUIVO")"
        SHA256="$(sha256sum "$ARQUIVO" | awk '{print $1}')"

        DURACAO_S="$(
            awk -v t="$TIMESTAMP_MAX" \
              'BEGIN {printf "%.6f", t / 1000000}'
        )"

        if [ -z "$MOTIVOS" ]; then
            STATUS="OK"
            APROVADOS=$((APROVADOS + 1))
        else
            STATUS="ERRO"
            ERROS=$((ERROS + 1))
        fi

        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$CENARIO" "$SEED" "$STATUS" "$MOTIVOS" "$ARQUIVO" \
          "$TAMANHO_BYTES" "$SHA256" "$LINHAS" "$NOS" "$IDS_AUSENTES" \
          "$TIMESTAMP_MIN" "$TIMESTAMP_MAX" "$DURACAO_S" \
          "$SAMPLE_START" "$SAMPLE_END" "$ENERGY" \
          "$SINKHOLE" "$SYBIL" "$TX" "$RX" \
          "$ATAQUES_FORA_NO16" \
          "$START_MIN" "$START_MAX" "$END_MIN" "$END_MAX" \
          >> "$RELATORIO"

        echo "[$STATUS] cenario=$CENARIO seed=$NUMERO ENERGY=$ENERGY SINKHOLE=$SINKHOLE SYBIL=$SYBIL TX=$TX RX=$RX"
    done
done

echo
echo "Logs verificados: $TOTAL"
echo "Logs aprovados: $APROVADOS"
echo "Logs com erro: $ERROS"
echo "Relatório: $RELATORIO"

if [ "$ERROS" -ne 0 ]; then
    exit 1
fi
