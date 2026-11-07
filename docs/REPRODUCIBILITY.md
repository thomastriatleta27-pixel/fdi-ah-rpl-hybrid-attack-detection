# Reprodutibilidade

## 1. Ambiente de referência

- Ubuntu Server;
- Contiki-NG commit
  `9658fada01f422d350ff7ae9b0204c22382bc0ac`;
- Cooja;
- plataforma TelosB/Sky;
- Python e dependências registrados em `configs`.

## 2. Preparação

Clone o Contiki-NG e selecione o commit utilizado. Depois, na raiz deste
repositório, defina:

    export CONTIKI_NG_ROOT=/caminho/para/contiki-ng

Execute:

    ./codigo/preparar-ambiente.sh

O script instala os firmwares, aplica o patch do Contiki-NG, copia os
cenários e prepara os scripts do Cooja.

## 3. Execução das simulações

Consulte a ajuda:

    ./codigo/execucao/executar-todos.sh

Para executar as quatro classes e as dez seeds:

    ./codigo/execucao/executar-todos.sh --executar

Resultados já existentes não são sobrescritos.

## 4. Validação dos logs

O pacote de logs publicado no Zenodo contém um validador autônomo. Na raiz
desse pacote, execute:

    ./validacao/verificar-logs-definitivos.sh

A validação original aprovou 40 de 40 logs.

## 5. Construção do dataset

A ordem principal dos scripts é:

1. `extrair_dataset_principal_4classes_3600s.py`;
2. `agregar_dataset_principal_por_janela.py`;
3. `criar_sequencias_principal_60s.py`.

Use preferencialmente as versões em `codigo/pipeline-portavel`.

## 6. Treinamento

- XGBoost:
  `treinar_xgboost_principal_60s.py`;
- LSTM e GRU:
  `treinar_recorrente_principal_5fold.py`.

Os hiperparâmetros utilizados estão registrados diretamente nesses
scripts.

## 7. Comparações e avaliação operacional

Execute, conforme o resultado pretendido:

- `comparar_modelos_principal_por_seed.py`;
- `analisar_politicas_alerta_principal.py`;
- `calcular_tempo_deteccao_principal.py`;
- `calcular_tempo_deteccao_principal_k6.py`;
- `calcular_falsos_alertas_operacionais_principal.py`;
- `gerar_tabela_principal_modelos.py`;
- `gerar_graficos_principal.py`.

## 8. Pipelines original e portável

`pipeline-original` preserva os scripts executados no ambiente da
pesquisa.

`pipeline-portavel` altera somente a definição do diretório-base,
utilizando `CONTIKI_NG_ROOT`. O arquivo
`configs/diff-pipeline-portavel.patch` documenta essas diferenças.

## 9. Integridade

Cada pacote do Zenodo contém `MANIFEST.sha256`. Após extrair um pacote:

    sha256sum -c MANIFEST.sha256

O arquivo `docs/zenodo-SHA256SUMS.txt` contém os hashes externos dos
arquivos compactados.

## 10. Obtenção dos artefatos completos

Os logs definitivos, os datasets, as sequências temporais, os modelos,
os resultados e o pacote integral de código estão preservados no Zenodo:

- DOI: [10.5281/zenodo.24036265](https://doi.org/10.5281/zenodo.24036265);
- versão dos artefatos: `v1.0.0`;
- repositório do código: [https://github.com/thomastriatleta27-pixel/fdi-ah-rpl-hybrid-attack-detection](https://github.com/thomastriatleta27-pixel/fdi-ah-rpl-hybrid-attack-detection).

Após baixar os arquivos compactados, valide-os com:

    sha256sum -c SHA256SUMS.txt

Em seguida, depois de extrair cada pacote, valide seu conteúdo com:

    sha256sum -c MANIFEST.sha256

