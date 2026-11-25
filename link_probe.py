"""
Starter telemetry & link-probing prototype for a channel-bonding client.
Measures per-target / per-source-IP reachability, RTT, and packet loss.
"""

import argparse
import json
import socket
import statistics
import time
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class LinkStats:
    source_ip: str
    target_host: str
    target_port: int
    sent: int
    received: int
    loss_pct: float
    min_ms: Optional[float]
    avg_ms: Optional[float]
    max_ms: Optional[float]
    jitter_ms: Optional[float]


def get_local_ips() -> List[str]:
    """Return candidate local IPv4 addresses across active interfaces."""
    ips = set()
    try:
        # Connects a UDP socket to an external address to discover the primary outbound IP
        # without sending any packets.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("1.1.1.1", 53))
            ips.add(s.getsockname()[0])
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            addr = info[4][0]
            if not addr.startswith("127."):
                ips.add(addr)
    except socket.gaierror:
        pass

    return sorted(ips) if ips else ["0.0.0.0"]


def probe_tcp_rtt(source_ip: str, host: str, port: int, timeout: float = 1.0) -> Optional[float]:
    """
    Measure connection handshake RTT in milliseconds from a bound source IP.
    Note: On Linux, binding to a specific local IP works best when paired with
    source-based routing rules (`ip rule`) so traffic leaves the intended NIC.
    """
    start = time.perf_counter()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            if source_ip != "0.0.0.0":
                sock.bind((source_ip, 0))
            sock.connect((host, port))
        return (time.perf_counter() - start) * 1000.0
    except OSError:
        return None


def measure_link(
    source_ip: str,
    host: str,
    port: int,
    count: int = 10,
    interval: float = 0.2,
    timeout: float = 1.0,
) -> LinkStats:
    rtts_ms: List[float] = []

    for _ in range(count):
        rtt = probe_tcp_rtt(source_ip, host, port, timeout=timeout)
        if rtt is not None:
            rtts_ms.append(rtt)
        time.sleep(interval)

    sent = count
    received = len(rtts_ms)
    loss_pct = ((sent - received) / sent) * 100.0 if sent else 0.0

    if rtts_ms:
        min_ms = round(min(rtts_ms), 2)
        avg_ms = round(statistics.mean(rtts_ms), 2)
        max_ms = round(max(rtts_ms), 2)
        jitter_ms = (
            round(
                statistics.mean(abs(rtts_ms[i] - rtts_ms[i - 1]) for i in range(1, len(rtts_ms))),
                2,
            )
            if len(rtts_ms) > 1
            else 0.0
        )
    else:
        min_ms = avg_ms = max_ms = jitter_ms = None

    return LinkStats(
        source_ip=source_ip,
        target_host=host,
        target_port=port,
        sent=sent,
        received=received,
        loss_pct=round(loss_pct, 1),
        min_ms=min_ms,
        avg_ms=avg_ms,
        max_ms=max_ms,
        jitter_ms=jitter_ms,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Starter link telemetry probe")
    parser.add_argument("--host", default="1.1.1.1", help="Target IP/hostname (e.g. your VPS)")
    parser.add_argument("--port", type=int, default=443, help="Target TCP port (e.g. 443 or 80)")
    parser.add_argument("--count", type=int, default=10, help="Number of probes per round")
    parser.add_argument("--json", action="store_true", help="Print output as JSON")
    args = parser.parse_args()

    sources = get_local_ips()
    results = [measure_link(src, args.host, args.port, count=args.count) for src in sources]

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            print(
                f"src={r.source_ip} -> {r.target_host}:{r.target_port} | "
                f"loss={r.loss_pct}% | avg={r.avg_ms}ms | min={r.min_ms}ms | "
                f"max={r.max_ms}ms | jitter={r.jitter_ms}ms"
            )


if __name__ == "__main__":
    main()
