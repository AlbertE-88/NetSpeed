# Multi-Link Channel Bonding & Telemetry Prototype

A work-in-progress project exploring how to combine multiple network interfaces (such as Wi-Fi, Ethernet, and mobile tethering) through a relay server to improve throughput, resilience, and latency.

## Architecture Overview

A full Speedify-style system splits work between two sides and two layers:

* **Client & Control Plane (Python):** Discovers candidate local IP addresses/interfaces, probes link health (RTT, jitter, packet loss), and coordinates path selection and configuration.
* **Packet Data Plane & Relay (Planned in Go):** Captures traffic via a virtual `TUN` interface, wraps/encrypts packets over UDP tunnels, balances or duplicates traffic across links, and reassembles packets on a remote relay server (such as a Linux VPS).

## Current Status

* `link_probe.py`: A zero-dependency starter probe using the Python standard library that measures TCP handshake RTT, packet loss, and jitter from local IP addresses to a target host and port.

## Quick Start


