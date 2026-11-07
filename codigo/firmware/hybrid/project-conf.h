#ifndef PROJECT_CONF_H_
#define PROJECT_CONF_H_

/* =========================================================
 * FDI-AH - Configurações de monitoramento
 * ========================================================= */

/* Ativa o Energest para monitoramento de CPU, LPM e rádio */
#define ENERGEST_CONF_ON 1

/* Ativa contadores de pacotes do módulo Link Stats */
#define LINK_STATS_CONF_PACKET_COUNTERS 1


/* =========================================================
 * Dimensionamento da tabela de Source Routing
 * ========================================================= */
#define UIP_SR_CONF_LINK_NUM 40


/* =========================================================
 * FDI-AH - Ataque Sybil
 * ========================================================= */
/* Habilita o comportamento Sybil somente neste firmware */
#define FDI_AH_SYBIL 1
#define FDI_AH_SINKHOLE 1

/*
 * Reserva entradas IPv6 adicionais exclusivamente para o cenário Sybil.
 * Mantém espaço para os endereços legítimos e para identidades
 * experimentais adicionais.
 */
#define UIP_CONF_DS6_ADDR_NBU 5

#endif /* PROJECT_CONF_H_ */

