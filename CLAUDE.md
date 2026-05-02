# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**Quantum-Ready Sky** — educational simulation of a satellite-to-aircraft secure data link protected by post-quantum cryptography (PQC). All crypto is mocked. The stack is entirely Docker-based; there is no build system, no test suite, and no linter configured.

## Essential commands

```bash
# Build and start everything
docker-compose up --build

# Follow logs for one service
docker-compose logs -f satellite-sec-gw

# Restart a single service after editing its app.py
docker-compose restart aircraft-sec-gw

# Trigger a red-team attack (container sleeps by default)
docker exec -it redteam-attacker python app.py --mode inject
docker exec -it redteam-attacker python app.py --mode replay --count 10 --interval 1
docker exec -it redteam-attacker python app.py --mode loop --interval 3

# Browse the FPGA mock API (exposed on host)
# http://localhost:7000/docs
```

## Architecture

### Network segmentation (4 Docker bridge networks)

```
net_aircraft_internal   aircraft-app ←→ aircraft-sec-gw
net_satcom_space        aircraft-sec-gw ←→ satellite-sec-gw   ← redteam-console injects here
net_ground_internal     satellite-sec-gw ←→ satellite-app
net_management          fpga-emulator, both gateways, telemetry-bus, grafana, blue-ai-langchain
```

### UDP data plane (end-to-end flow)

```
aircraft-app  →(UDP:9001)→  aircraft-sec-gw  →(UDP:9002)→  satellite-sec-gw  →(UDP:9003)→  satellite-app
```

Each gateway handles packets in a `threading.Thread` per datagram (blocking `socket.recvfrom` main loop).

### HTTP control plane (crypto calls)

Both gateways call `fpga-emulator:7000` synchronously via `requests` before forwarding each packet:

- **aircraft-sec-gw**: `POST /encrypt` → `POST /sign` → emit secure packet
- **satellite-sec-gw**: `POST /verify` (drops packet if invalid) → `POST /decrypt` → emit plaintext

Both gateways run `wait_for_fpga()` on startup (polls `/docs` up to 60 s) before binding their UDP socket.

### Mock crypto contract (fpga-emulator)

| Endpoint | Behaviour |
|---|---|
| `POST /encrypt` | base64-encodes the JSON payload, returns `"KYBER1024::<b64>"` |
| `POST /decrypt` | strips `KYBER1024::` prefix, base64-decodes, returns original object |
| `POST /sign` | returns `"DILITHIUM3_SIG_<sha256[:16]>"` |
| `POST /verify` | returns `valid: false` if the signature string contains `"FORGED"`, else `true` |
| `POST /kem/init` | returns static mocked key pair |

The base64 round-trip means `satellite-app` receives the exact original telemetry dict.

### Red-team detection mechanism

`redteam-console` (Scapy, `NET_ADMIN`+`NET_RAW` caps) forges raw IP/UDP packets with a spoofed source IP directly into `net_satcom_space`. Forged packets always contain `"FORGED"` in the signature field. `satellite-sec-gw` calls `/verify`, detects the string, logs `*** ALERTE SECURITE ***`, and drops the packet — it never reaches `satellite-app`.

### blue-ai-langchain

Placeholder only — infinite `time.sleep(60)` loop. Do not implement LangChain logic here without explicit instruction.

## Environment variables (all services)

Every configurable value has a hardcoded default matching the docker-compose service names, so services work both inside Docker and (with manual env vars) locally.

| Service | Key vars |
|---|---|
| aircraft-app | `AIRCRAFT_GW_HOST`, `AIRCRAFT_GW_PORT` |
| aircraft-sec-gw | `FPGA_API_URL`, `LISTEN_UDP_PORT`, `SAT_GW_HOST`, `SAT_GW_PORT` |
| satellite-sec-gw | `FPGA_API_URL`, `LISTEN_UDP_PORT`, `SAT_APP_HOST`, `SAT_APP_PORT` |
| satellite-app | `LISTEN_UDP_PORT` |
| redteam-console | `TARGET_GW_HOST`, `TARGET_GW_PORT`, `SPOOF_SRC_IP` |

## Adding a new service

1. Create `<service-name>/app.py` and `<service-name>/Dockerfile` (use `python:3.9-slim`).
2. Add `build: ./<service-name>` in `docker-compose.yml` and attach it to the correct network(s).
3. If the service needs the FPGA, add it to `net_management` and call `wait_for_fpga()` before binding any socket.
