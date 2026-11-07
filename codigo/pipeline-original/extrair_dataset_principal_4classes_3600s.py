import re
import csv
import math
import statistics
from pathlib import Path
from collections import defaultdict

BASE = Path("/home/joaorosa/contiki-ng")
LOG_BASE = BASE / "experimentos/final/logs/definitivo"
OUT = BASE / "experimentos/final/resultados/dataset/dataset_fdi_ah_principal_4classes_3600s.csv"

SCENARIOS = ["normal", "sinkhole", "sybil", "hybrid"]

LINE_RE = re.compile(r"^(\d+)\s+ID:(\d+)\s+(.*)$")

STATUS_RE = re.compile(
    r"FDI_STATUS,joined=(\d+),reachable=(\d+)"
)

ENERGY_RE = re.compile(
    r"FDI_METRIC,ENERGY,"
    r"cpu=(\d+),lpm=(\d+),tx=(\d+),rx_listen=(\d+)"
)

RPL_RE = re.compile(
    r"FDI_METRIC,RPL,neighbors=(\d+),local_rank=(\d+)"
)

NEIGHBOR_RE = re.compile(
    r"FDI_NEIGHBOR,"
    r"ip=([^,]+),"
    r"parent=(\d+),"
    r"preferred=(\d+),"
    r"rank=(\d+),"
    r"metric=(\d+),"
    r"etx=(\d+),"
    r"rssi=(-?\d+),"
    r"fresh=(\d+)"
)

DATA_TX_RE = re.compile(
    r"FDI_DATA,TX,src=(\d+),seq=(\d+)"
)

DATA_RX_RE = re.compile(
    r"FDI_DATA,RX,src=(\d+),seq=(\d+)"
)

DBG_TYPES = {
    "DIS_TX": "dis_tx_count",
    "DIS_RX": "dis_rx_count",
    "DIO_TX": "dio_tx_count",
    "DIO_RX": "dio_rx_count",
    "DAO_TX": "dao_tx_count",
    "DAO_RX": "dao_rx_count",
    "DAO_ACK_TX": "dao_ack_tx_count",
    "DAO_ACK_RX": "dao_ack_rx_count",
}

FIELDS = [
    # Metadados
    "scenario",
    "seed",
    "node_id",
    "timestamp_us",
    "timestamp_s",
    "window",

    # Estado
    "joined",
    "reachable",
    "local_rank",
    "local_rank_valid",
    "neighbors_count",

    # Energest - deltas
    "cpu_delta",
    "lpm_delta",
    "radio_tx_delta",
    "radio_rx_listen_delta",

    # Vizinhanca
    "preferred_exists",
    "preferred_rank",
    "preferred_etx",
    "preferred_rssi",
    "preferred_fresh",
    "candidate_parent_count",

    "neighbor_rank_mean",
    "neighbor_rank_min",
    "neighbor_rank_max",

    "neighbor_etx_mean",
    "neighbor_etx_min",
    "neighbor_etx_max",

    "neighbor_rssi_mean",
    "neighbor_rssi_min",
    "neighbor_rssi_max",

    # Controle RPL
    "dis_tx_count",
    "dis_rx_count",
    "dio_tx_count",
    "dio_rx_count",
    "dao_tx_count",
    "dao_rx_count",
    "dao_ack_tx_count",
    "dao_ack_rx_count",

    # Trafego
    "data_tx_count",
    "data_rx_count",
    "pdr",

    # Latencia
    "latency_count",
    "latency_mean_ms",
    "latency_min_ms",
    "latency_max_ms",
    "latency_std_ms",
]


def mean_or_none(values):
    return statistics.mean(values) if values else None


def min_or_none(values):
    return min(values) if values else None


def max_or_none(values):
    return max(values) if values else None


def std_or_none(values):
    if len(values) <= 1:
        return 0.0 if len(values) == 1 else None
    return statistics.pstdev(values)


def safe_delta(current, previous):
    if current is None or previous is None:
        return None

    d = current - previous

    # Evita interpretar reset/wrap como consumo negativo.
    if d < 0:
        return None

    return d


def parse_log(path, scenario, seed):
    samples = []
    current = {}

    # Eventos independentes das amostras.
    dbg_events = defaultdict(list)

    # TX/RX indexados globalmente por (src,seq).
    tx_events = {}
    rx_events = {}

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()

            m = LINE_RE.match(line)
            if not m:
                continue

            ts = int(m.group(1))
            node = int(m.group(2))
            event = m.group(3)

            # -------------------------------------------------------
            # Eventos de controle RPL
            # -------------------------------------------------------
            if event.startswith("FDI_DBG,"):
                dbg_type = event.split(",", 2)[1]

                if dbg_type in DBG_TYPES:
                    dbg_events[node].append((ts, dbg_type))

            # -------------------------------------------------------
            # Trafego de dados
            # -------------------------------------------------------
            mtx = DATA_TX_RE.match(event)
            if mtx:
                src = int(mtx.group(1))
                seq = int(mtx.group(2))
                tx_events[(src, seq)] = ts

            mrx = DATA_RX_RE.match(event)
            if mrx:
                src = int(mrx.group(1))
                seq = int(mrx.group(2))

                # Primeiro RX correspondente.
                rx_events.setdefault((src, seq), ts)

            # -------------------------------------------------------
            # Inicio da amostra
            # -------------------------------------------------------
            if event == "FDI_SAMPLE_START":
                current[node] = {
                    "scenario": scenario,
                    "seed": seed,
                    "node_id": node,
                    "timestamp_us": ts,
                    "joined": None,
                    "reachable": None,
                    "cpu": None,
                    "lpm": None,
                    "radio_tx": None,
                    "radio_rx_listen": None,
                    "neighbors_count": None,
                    "local_rank_raw": None,
                    "neighbor_data": [],
                }
                continue

            if node not in current:
                continue

            s = current[node]

            ms = STATUS_RE.match(event)
            if ms:
                s["joined"] = int(ms.group(1))
                s["reachable"] = int(ms.group(2))
                continue

            me = ENERGY_RE.match(event)
            if me:
                s["cpu"] = int(me.group(1))
                s["lpm"] = int(me.group(2))
                s["radio_tx"] = int(me.group(3))
                s["radio_rx_listen"] = int(me.group(4))
                continue

            mr = RPL_RE.match(event)
            if mr:
                s["neighbors_count"] = int(mr.group(1))
                s["local_rank_raw"] = int(mr.group(2))
                continue

            mn = NEIGHBOR_RE.match(event)
            if mn:
                s["neighbor_data"].append({
                    "ip": mn.group(1),
                    "parent": int(mn.group(2)),
                    "preferred": int(mn.group(3)),
                    "rank": int(mn.group(4)),
                    "etx": int(mn.group(6)),
                    "rssi": int(mn.group(7)),
                    "fresh": int(mn.group(8)),
                })
                continue

            if event == "FDI_SAMPLE_END":
                samples.append(s)
                del current[node]

    # ---------------------------------------------------------------
    # Organiza amostras por no para calcular deltas
    # ---------------------------------------------------------------
    by_node = defaultdict(list)

    for s in samples:
        by_node[s["node_id"]].append(s)

    rows = []

    for node, node_samples in by_node.items():
        node_samples.sort(key=lambda x: x["timestamp_us"])

        previous = None

        for s in node_samples:
            ts = s["timestamp_us"]

            # Cada FDI_SAMPLE_START representa uma janela de 10 s
            # terminando aproximadamente no timestamp da proxima amostra.
            window_start = max(0, ts - 10_000_000)
            window_end = ts

            raw_rank = s["local_rank_raw"]
            rank_valid = int(
                raw_rank is not None and raw_rank not in (0, 65535)
            )

            local_rank = raw_rank if rank_valid else None

            nbrs = s["neighbor_data"]
            preferred = [n for n in nbrs if n["preferred"] == 1]
            parents = [n for n in nbrs if n["parent"] == 1]

            pref = preferred[0] if preferred else None

            ranks = [
                n["rank"] for n in nbrs
                if n["rank"] not in (0, 65535)
            ]
            etxs = [n["etx"] for n in nbrs]
            rssis = [n["rssi"] for n in nbrs]

            row = {
                "scenario": scenario,
                "seed": seed,
                "node_id": node,
                "timestamp_us": ts,
                "timestamp_s": ts / 1_000_000.0,
                "window": int(ts // 10_000_000),

                "joined": s["joined"],
                "reachable": s["reachable"],
                "local_rank": local_rank,
                "local_rank_valid": rank_valid,
                "neighbors_count": s["neighbors_count"],

                "cpu_delta": safe_delta(
                    s["cpu"],
                    previous["cpu"] if previous else None
                ),
                "lpm_delta": safe_delta(
                    s["lpm"],
                    previous["lpm"] if previous else None
                ),
                "radio_tx_delta": safe_delta(
                    s["radio_tx"],
                    previous["radio_tx"] if previous else None
                ),
                "radio_rx_listen_delta": safe_delta(
                    s["radio_rx_listen"],
                    previous["radio_rx_listen"] if previous else None
                ),

                "preferred_exists": int(bool(preferred)),
                "preferred_rank": pref["rank"] if pref else None,
                "preferred_etx": pref["etx"] if pref else None,
                "preferred_rssi": pref["rssi"] if pref else None,
                "preferred_fresh": pref["fresh"] if pref else None,
                "candidate_parent_count": len(parents),

                "neighbor_rank_mean": mean_or_none(ranks),
                "neighbor_rank_min": min_or_none(ranks),
                "neighbor_rank_max": max_or_none(ranks),

                "neighbor_etx_mean": mean_or_none(etxs),
                "neighbor_etx_min": min_or_none(etxs),
                "neighbor_etx_max": max_or_none(etxs),

                "neighbor_rssi_mean": mean_or_none(rssis),
                "neighbor_rssi_min": min_or_none(rssis),
                "neighbor_rssi_max": max_or_none(rssis),
            }

            # -------------------------------------------------------
            # Contadores RPL dentro da janela
            # -------------------------------------------------------
            counts = defaultdict(int)

            for event_ts, dbg_type in dbg_events[node]:
                if window_start < event_ts <= window_end:
                    counts[dbg_type] += 1

            for dbg_type, field in DBG_TYPES.items():
                row[field] = counts[dbg_type]

            # -------------------------------------------------------
            # Dados: TX originados pelo proprio no
            #
            # Para evitar perder pacotes perto da borda da janela,
            # associamos o pacote a janela pelo timestamp do TX.
            # -------------------------------------------------------
            tx_keys = [
                key for key, tx_ts in tx_events.items()
                if key[0] == node
                and window_start < tx_ts <= window_end
            ]

            received = []
            latencies_ms = []

            for key in tx_keys:
                tx_ts = tx_events[key]

                if key in rx_events:
                    rx_ts = rx_events[key]

                    # RX precisa ocorrer depois do TX.
                    if rx_ts >= tx_ts:
                        received.append(key)
                        latencies_ms.append(
                            (rx_ts - tx_ts) / 1000.0
                        )

            row["data_tx_count"] = len(tx_keys)
            row["data_rx_count"] = len(received)

            if tx_keys:
                row["pdr"] = len(received) / len(tx_keys)
            else:
                row["pdr"] = None

            row["latency_count"] = len(latencies_ms)
            row["latency_mean_ms"] = mean_or_none(latencies_ms)
            row["latency_min_ms"] = min_or_none(latencies_ms)
            row["latency_max_ms"] = max_or_none(latencies_ms)
            row["latency_std_ms"] = std_or_none(latencies_ms)

            rows.append(row)
            previous = s

    return rows, len(current)


def main():
    all_rows = []
    incomplete = 0

    for scenario in SCENARIOS:
        for seed in range(1, 11):
            seed_text = f"{seed:02d}"

            path = (
                LOG_BASE /
                scenario /
                f"definitivo-{scenario}-seed{seed_text}-3600s.log"
            )

            if not path.exists():
                raise FileNotFoundError(path)

            rows, opened = parse_log(path, scenario, seed)

            all_rows.extend(rows)
            incomplete += opened

            print(
                f"{scenario:10s} seed{seed_text}: "
                f"{len(rows)} amostras"
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for row in all_rows:
            writer.writerow(row)

    print()
    print("========================================")
    print(f"Dataset: {OUT}")
    print(f"Linhas: {len(all_rows)}")
    print(f"Amostras abertas/incompletas: {incomplete}")
    print("========================================")


if __name__ == "__main__":
    main()
