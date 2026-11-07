#include "contiki.h"

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <inttypes.h>

#include "sys/log.h"
#include "sys/energest.h"
#include "sys/node-id.h"

#include "net/link-stats.h"
#include "net/ipv6/uiplib.h"
#include "net/ipv6/simple-udp.h"
#include "random.h"
#include "net/routing/routing.h"

#include "net/routing/rpl-lite/rpl.h"
#include "net/routing/rpl-lite/rpl-neighbor.h"

#include "net/nbr-table.h"

#define LOG_MODULE "FDI-AH"
#define LOG_LEVEL LOG_LEVEL_INFO

#define MONITOR_INTERVAL (10 * CLOCK_SECOND)

#define FDI_UDP_CLIENT_PORT 8765
#define FDI_UDP_SERVER_PORT 5678
#define FDI_DATA_INTERVAL   (10 * CLOCK_SECOND)

typedef struct {
  uint16_t source_id;
  uint32_t sequence;
} fdi_data_packet_t;

static struct simple_udp_connection fdi_udp_conn;

PROCESS(fdi_ah_process, "FDI-AH Monitoring Process");
PROCESS(fdi_data_process, "FDI-AH UDP Data Process");

AUTOSTART_PROCESSES(&fdi_ah_process, &fdi_data_process);

static void
fdi_udp_rx_callback(struct simple_udp_connection *c,
                    const uip_ipaddr_t *sender_addr,
                    uint16_t sender_port,
                    const uip_ipaddr_t *receiver_addr,
                    uint16_t receiver_port,
                    const uint8_t *data,
                    uint16_t datalen)
{
  if(node_id == 1 && datalen == sizeof(fdi_data_packet_t)) {
    fdi_data_packet_t packet;

    /*
     * Copia o payload para uma estrutura local alinhada.
     * Evita leitura desalinhada no MSP430/Sky.
     */
    memcpy(&packet, data, sizeof(packet));

    printf("FDI_DATA,RX,src=%u,seq=%lu\n",
           (unsigned)packet.source_id,
           (unsigned long)packet.sequence);
  }
}

/*---------------------------------------------------------------------------*/
static void
print_energest(void)
{
  energest_flush();

  printf(
    "FDI_METRIC,ENERGY,"
    "cpu=%" PRIu64 ","
    "lpm=%" PRIu64 ","
    "tx=%" PRIu64 ","
    "rx_listen=%" PRIu64 "\n",
    energest_type_time(ENERGEST_TYPE_CPU),
    energest_type_time(ENERGEST_TYPE_LPM),
    energest_type_time(ENERGEST_TYPE_TRANSMIT),
    energest_type_time(ENERGEST_TYPE_LISTEN)
  );
}

static void
print_rpl_neighbors(void)
{
  rpl_nbr_t *nbr;

  printf("FDI_METRIC,RPL,neighbors=%d,local_rank=%u\n",
         rpl_neighbor_count(),
         (unsigned)curr_instance.dag.rank);

  for(nbr = nbr_table_head(rpl_neighbors);
      nbr != NULL;
      nbr = nbr_table_next(rpl_neighbors, nbr)) {

    const uip_ipaddr_t *ipaddr;
    const struct link_stats *stats;
    char ipbuf[UIPLIB_IPV6_MAX_STR_LEN];

    ipaddr = rpl_neighbor_get_ipaddr(nbr);
    stats = rpl_neighbor_get_link_stats(nbr);

    if(ipaddr != NULL) {
      uiplib_ipaddr_snprint(ipbuf, sizeof(ipbuf), ipaddr);
    } else {
      snprintf(ipbuf, sizeof(ipbuf), "none");
    }

    printf(
      "FDI_NEIGHBOR,"
      "ip=%s,"
      "parent=%d,"
      "preferred=%d,"
      "rank=%u,"
      "metric=%u,"
      "etx=%u,"
      "rssi=%d,"
      "fresh=%d\n",
      ipbuf,
      rpl_neighbor_is_parent(nbr),
      nbr == curr_instance.dag.preferred_parent,
      (unsigned)rpl_neighbor_rank_via_nbr(nbr),
      (unsigned)rpl_neighbor_get_link_metric(nbr),
      stats != NULL ? stats->etx : 0,
      stats != NULL ? stats->rssi : LINK_STATS_RSSI_UNKNOWN,
      stats != NULL ? link_stats_is_fresh(stats) : 0
    );
  }
}

PROCESS_THREAD(fdi_data_process, ev, data)
{
  static struct etimer data_timer;
  static uint32_t sequence;
  static fdi_data_packet_t packet;
  static uip_ipaddr_t root_ipaddr;

  PROCESS_BEGIN();

  if(node_id == 1) {
    /*
     * Root: servidor UDP.
     * Escuta na porta 5678 e recebe dos sensores na porta 8765.
     */
    simple_udp_register(&fdi_udp_conn,
                        FDI_UDP_SERVER_PORT,
                        NULL,
                        FDI_UDP_CLIENT_PORT,
                        fdi_udp_rx_callback);
  } else {
    /*
     * Sensores: clientes UDP.
     * Usam a porta local 8765 e enviam para a porta 5678 do root.
     */
    simple_udp_register(&fdi_udp_conn,
                        FDI_UDP_CLIENT_PORT,
                        NULL,
                        FDI_UDP_SERVER_PORT,
                        NULL);
  }

  /*
   * Espalha deterministicamente o primeiro envio entre os sensores.
   * ID1 e a raiz e nao transmite dados.
   */
  if(node_id != 1) {
    etimer_set(&data_timer,
               (2 * CLOCK_SECOND) +
               ((node_id % 8) * CLOCK_SECOND));

    while(1) {
      PROCESS_WAIT_EVENT_UNTIL(etimer_expired(&data_timer));

      if(NETSTACK_ROUTING.node_is_reachable() &&
         NETSTACK_ROUTING.get_root_ipaddr(&root_ipaddr)) {

        sequence++;

        packet.source_id = node_id;
        packet.sequence = sequence;

        printf("FDI_DATA,TX,src=%u,seq=%lu\n",
               node_id,
               (unsigned long)sequence);

        simple_udp_sendto(&fdi_udp_conn,
                          &packet,
                          sizeof(packet),
                          &root_ipaddr);
      }

      /*
       * Periodo fixo de 10 s apos o offset inicial.
       */
      etimer_set(&data_timer, FDI_DATA_INTERVAL);
    }
  }

  PROCESS_END();
}

/*---------------------------------------------------------------------------*/
PROCESS_THREAD(fdi_ah_process, ev, data)
{
  static struct etimer monitor_timer;

  PROCESS_BEGIN();

  LOG_INFO("========================================\n");
  LOG_INFO("FDI-AH monitoring module started\n");
  LOG_INFO("Mote ID: %u\n", node_id);
  LOG_INFO("========================================\n");

  /*
   * Mote 1 atua como raiz da rede RPL.
   */
  if(node_id == 1) {

    LOG_INFO("Starting RPL DAG root...\n");

    if(NETSTACK_ROUTING.root_start() == 0) {
      LOG_INFO("RPL DAG root started successfully\n");
    } else {
      LOG_ERR("Failed to start RPL DAG root\n");
    }

  } else {

    LOG_INFO("Node %u operating as RPL sensor node\n", node_id);

  }

  etimer_set(&monitor_timer, MONITOR_INTERVAL);

  while(1) {

    PROCESS_WAIT_EVENT_UNTIL(
      etimer_expired(&monitor_timer)
    );

    etimer_reset(&monitor_timer);

    printf("FDI_SAMPLE_START\n");

    printf(
      "FDI_STATUS,joined=%d,reachable=%d\n",
      NETSTACK_ROUTING.node_has_joined(),
      NETSTACK_ROUTING.node_is_reachable()
    );

    print_energest();

    print_rpl_neighbors();

    printf("FDI_SAMPLE_END\n");
  }

  PROCESS_END();
}
