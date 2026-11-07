# FDI-AH

Artefatos da dissertação **Detecção Inteligente de Ataques Híbridos em
Redes IoT baseadas no protocolo RPL: Uma Abordagem via Machine Learning**.

O FDI-AH avalia a classificação dos cenários Normal, Sinkhole, Sybil e
Hybrid, sendo Hybrid a execução coordenada de Sinkhole e Sybil no mesmo
nó atacante.

## Responsáveis

- Autor: Thomás Silva de Araujo
- Instituição: Universidade Federal de Sergipe (UFS)
- Orientador: Admilson de Ribamar Lima Ribeiro
- Coorientador: Rubens de Souza Matos Júnior

## Experimento

- Cooja/Contiki-NG;
- 30 motes TelosB/Sky;
- quatro cenários;
- dez seeds por cenário;
- 40 execuções de 3.600 segundos;
- nó 16 como atacante;
- XGBoost, LSTM e GRU;
- GroupKFold com cinco folds e agrupamento por seed.

## Conjunto de dados

- 430.800 registros no nível dos nós;
- 14.360 janelas agregadas;
- 14.160 sequências no formato 6 x 200;
- quatro classes balanceadas.

O diretório `data/sample` contém amostras pequenas para inspeção. Os logs,
datasets completos, modelos e resultados serão disponibilizados no
Zenodo. O DOI será inserido antes da publicação da versão v1.0.0.

## Estrutura

- `codigo/firmware`: firmwares experimentais;
- `codigo/contiki-ng-patch`: alterações do Contiki-NG;
- `codigo/pipeline-original`: scripts exatos do experimento;
- `codigo/pipeline-portavel`: scripts com caminho configurável;
- `codigo/execucao`: execução dos cenários;
- `codigo/validacao`: validação dos logs;
- `cooja/cenarios`: configurações CSC;
- `cooja/scripts`: scripts de coleta;
- `configs`: versões, dependências e auditorias;
- `data/sample`: amostras do conjunto de dados;
- `docs`: documentação científica e operacional.

## Documentação

- [Reprodutibilidade](docs/REPRODUCIBILITY.md)
- [Dataset card](docs/DATASET_CARD.md)
- [Artefatos do Zenodo](docs/ARTIFACTS.md)

## Uso rápido

Defina a localização do Contiki-NG, se diferente de
`$HOME/contiki-ng`:

    export CONTIKI_NG_ROOT=/caminho/para/contiki-ng

Prepare os projetos, patches e cenários:

    ./codigo/preparar-ambiente.sh

Consulte a ajuda do executor:

    ./codigo/execucao/executar-todos.sh

A execução completa compreende 40 simulações de 3.600 segundos e pode
demandar várias horas.

## Limitações

Os resultados provêm de uma topologia simulada com 30 nós, um único nó
atacante e configurações específicas de Sinkhole e Sybil. O processamento
dos modelos foi realizado fora dos motes. O impacto energético isolado da
instrumentação não foi mensurado por um baseline controlado.

Os modelos e políticas de alerta não devem ser considerados prontos para
implantação em produção sem validação adicional.

## Licenças

- Código original: BSD 3-Clause;
- amostras de dados: CC BY 4.0;
- componentes de terceiros: consulte `THIRD_PARTY_NOTICES.md`.

## Citação

O arquivo `CITATION.cff` fornece os metadados básicos. A citação com DOI
será adicionada após a publicação no Zenodo.
