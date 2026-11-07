# Dataset Card — FDI-AH

## Resumo

O conjunto de dados FDI-AH foi produzido para investigar a separabilidade
comportamental dos cenários Normal, Sinkhole, Sybil e Hybrid em redes IoT
baseadas no protocolo RPL.

## Origem

Os dados foram gerados em 40 simulações no Cooja/Contiki-NG:

- 30 motes TelosB/Sky;
- dez seeds por cenário;
- 3.600 segundos por execução;
- intervalo de amostragem aproximado de dez segundos;
- nó 16 como atacante;
- três identidades adicionais no cenário Sybil;
- Sinkhole e Sybil coordenados no cenário Hybrid.

## Representações

| Representação | Unidade | Dimensão | Distribuição |
|---|---|---:|---:|
| Nível dos nós | Nó em uma janela | 430.800 x 46 | 107.700 por classe |
| Agregada | Rede em uma janela | 14.360 x 203 | 3.590 por classe |
| Temporal | Seis janelas consecutivas | 14.160 x 6 x 200 | 3.540 por classe |

## Eventos processados

A extração considerou eventos de estado, energia, RPL, vizinhança,
depuração e transmissão/recepção de dados. Eventos explícitos
`FDI_ATTACK` foram utilizados somente para auditoria dos cenários e não
como características preditivas.

## Características

As características incluem indicadores de:

- CPU, LPM, transmissão e recepção;
- Rank e plano de controle do RPL;
- vizinhança;
- transmissão e recepção de dados;
- comportamento agregado da rede.

A agregação utiliza média, desvio-padrão, mínimo, máximo e taxa de valores
ausentes. Cenário, seed, nó e janela são metadados.

## Integridade

- nenhuma chave duplicada no nível dos nós;
- nenhuma chave duplicada na representação agregada;
- classes balanceadas;
- nenhuma sequência atravessa seeds ou cenários;
- 1.864 valores ausentes na representação temporal, aproximadamente
  0,011 por cento das células.

LSTM e GRU utilizaram imputação mediana ajustada apenas sobre o conjunto
de treinamento de cada fold. O XGBoost tratou valores ausentes
nativamente.

## Divisão experimental

A avaliação empregou GroupKFold com cinco folds e agrupamento por seed.
Dados da mesma seed não aparecem simultaneamente no treinamento e no
teste.

## Usos recomendados

- pesquisa sobre detecção de ataques em RPL;
- comparação de classificadores;
- análise de ataques coordenados;
- estudo de separabilidade entre Sybil e Hybrid;
- avaliação de políticas de confirmação de alertas.

## Usos não recomendados

- tomada automática de decisão em redes de produção;
- generalização direta para qualquer topologia RPL;
- inferência de consumo energético absoluto em joules;
- comparação direta com datasets que utilizem protocolos experimentais
  incompatíveis.

## Limitações

O conjunto foi produzido por simulação, com uma topologia principal,
30 nós, um único atacante e configurações específicas dos ataques. A
rotulagem no nível do cenário pode incluir períodos de transição anteriores
à manifestação completa do ataque.

O custo energético da instrumentação não foi isolado em relação a um
firmware sem coleta.

## Dados pessoais e ética

O conjunto não contém dados pessoais nem tráfego de usuários reais.

## Licença

O dataset completo e as amostras são disponibilizados sob CC BY 4.0.
