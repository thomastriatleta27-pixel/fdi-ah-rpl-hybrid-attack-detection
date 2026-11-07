#ifndef PROJECT_CONF_H_
#define PROJECT_CONF_H_

/* =========================================================
 * FDI-AH - Configuracoes de monitoramento
 * ========================================================= */

/* Ativa o Energest para monitoramento de CPU, LPM e radio */
#define ENERGEST_CONF_ON 1

/* Ativa contadores de pacotes do modulo Link Stats */
#define LINK_STATS_CONF_PACKET_COUNTERS 1

/* =========================================================
 * FDI-AH - Cenario experimental Sinkhole
 * ========================================================= */
#define FDI_AH_SINKHOLE 1

/* Tabela de Source Routing dimensionada para o cenario de 30 nos */
#define UIP_SR_CONF_LINK_NUM 40

#endif /* PROJECT_CONF_H_ */
