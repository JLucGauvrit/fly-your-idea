# Quantum-Ready Sky

> **Securing tomorrow's aeronautical datalinks through hardware cryptography and intelligent supervision.**

A functional simulation of a post-quantum-secured satellite-to-aircraft communication link, combining FPGA-accelerated cryptography and an AI supervision agent for real-time anomaly detection.

---

## Context and Problem

Modern connected aircraft rely on SATCOM and IP-based datalinks for communications, real-time maintenance, cabin connectivity, and ground-infrastructure exchanges. This connectivity improves operational efficiency but widens the attack surface of aeronautical systems.

Classical cryptographic protocols (RSA, ECC) are mathematically vulnerable to **Shor's algorithm** running on future quantum computers. Aeronautical systems face a critical transition challenge: aircraft certification and deployment cycles span **30 years**, yet the cryptographic standards they depend on may become obsolete within that timeframe.

Existing Intrusion Detection Systems (IDS) in aviation are largely static, relying on known threat signatures. They struggle to identify zero-day exploits or subtle behavioral anomalies within high-speed data flows without introducing unacceptable latency.

---

## Solution: The Cyber-Shield Architecture

The project proposes a **defense-in-depth** architecture built on three pillars:

### 1. Post-Quantum Cryptography (PQC) — FPGA-accelerated

A hardware module implemented on FPGA handles all critical cryptographic operations on the datalink:

- **Key encapsulation**: CRYSTALS-Kyber (NIST standard)
- **Digital signature**: CRYSTALS-Dilithium (NIST standard)
- **High-throughput symmetric encryption** for data streams

FPGA implementation provides:
- Low-latency crypto operations compatible with real-time aeronautical constraints (ARINC 664 / AFDX)
- Hardware isolation of security functions
- **Cryptographic agility** — quantum algorithms can be updated via firmware without physical avionics modifications, critical for 30-year aircraft lifecycles

### 2. Embedded AI Supervision Agent

An AI agent analyzes communication flows and system telemetry continuously. Rather than passive encryption, it provides **active supervision**:

- Models normal network communication patterns via unsupervised learning
- Detects anomalies and attack signatures in real time
- Detectable threats: packet injection, spoofing, behavioral anomalies indicating equipment compromise

### 3. Segmented Network Architecture

Communication flows through four isolated network segments, each with appropriate trust levels:

```
[Aircraft]                    [Space segment]              [Ground]
  Avionics ──UDP──▶ PQC GW ══════════════════▶ PQC GW ──UDP──▶ Ground service
                  (encrypt+sign)   SATCOM    (verify+decrypt)

                        ▲  ← Attacker (spoofing / injection)
                        
                [net_management]
            FPGA Emulator · AI Agent · Telemetry Bus · Grafana
```

---

## Architecture of This Simulation

| Service | Role | Network(s) |
|---|---|---|
| `aircraft-app` | Generates UDP telemetry (JSON) every 2 s | aircraft_internal |
| `aircraft-sec-gw` | Encrypts + signs via FPGA API, relays to space segment | aircraft_internal · satcom_space · management |
| `fpga-emulator` | FastAPI mock of PQC cryptographic module (port 7000) | management |
| `satellite-sec-gw` | Verifies + decrypts via FPGA API, relays to ground | satcom_space · ground_internal · management |
| `satellite-app` | Receives and logs decrypted telemetry | ground_internal |
| `redteam-console` | Forges and injects spoofed UDP packets into the space segment | satcom_space |
| `satcom-link-sim` | Network emulation stub (tc/netem ready) | satcom_space |
| `blue-ai-langchain` | AI agent placeholder (future LangChain integration) | management |
| `telemetry-bus` | NATS message broker | management |
| `grafana` | Observability dashboard | management |

UDP port assignments: `9001` (aircraft internal) → `9002` (space segment) → `9003` (ground internal).  
FPGA API HTTP calls flow through `net_management`, which both gateways share.

---

## Getting Started

```bash
# Build all images and start the full stack
docker-compose up --build

# Follow a specific service
docker-compose logs -f satellite-app
```

Expected output once running:

```
[aircraft-app]       #0000 envoyé  alt=35042.3 ft  spd=481.2 kts
[aircraft-sec-gw]    #0000 → chiffré+signé → satellite-sec-gw:9002
[satellite-sec-gw]   #0000 vérifié+décrypté → satellite-app:9003
[satellite-app]      Reçu de l'avion (src=...) #0000 : alt=35042.3 ft ...
```

The FPGA emulator API is browsable at **http://localhost:7000/docs**.

---

## Red Team Testing

The `redteam-console` container injects forged raw IP/UDP packets directly into `net_satcom_space`, simulating an attacker with access to the SATCOM link:

```bash
# Single spoofed packet injection
docker exec -it redteam-attacker python app.py --mode inject

# Replay attack — 10 packets at 1 s interval
docker exec -it redteam-attacker python app.py --mode replay --count 10 --interval 1

# Continuous injection loop
docker exec -it redteam-attacker python app.py --mode loop --interval 3
```

The container requires `NET_ADMIN` and `NET_RAW` Linux capabilities (set in `docker-compose.yml`). Forged packets are detected by `satellite-sec-gw` (signature contains `"FORGED"` → `/verify` returns invalid → packet dropped, alert logged).

---

## Key Innovations

| Innovation | Why it matters |
|---|---|
| **Cryptographic agility via FPGA** | Algorithms (Kyber, Dilithium) can be swapped via firmware over a 30-year aircraft lifecycle without hardware replacement |
| **Active AI supervision** | Detects sophisticated spoofing that appears technically valid to traditional signature-based IDS |
| **Defense-in-depth** | Prevention (PQC) + detection (AI) are independent layers; compromising one does not disable the other |
| **Energy efficiency** | FPGAs outperform general-purpose CPUs for intensive cryptographic workloads, reducing avionics bay power draw |
| **Secure telemetry** | Authenticated real-time telemetry enables more reliable predictive maintenance and flight path optimization |

---

## Prototype Validation Plan

1. **FPGA hardware emulation** — implement CRYSTALS-Kyber on development boards; benchmark throughput and latency against ARINC 664/AFDX real-time constraints
2. **AI behavioral modeling** — train the unsupervised learning agent on network datasets; evaluate detection accuracy against Red Team scenarios (injection, spoofing)
3. **Security dashboard** — visualize real-time data flows between simulated cockpit and ground station; demonstrate FPGA mitigation and AI anomaly flagging

---

## Inspiration

This project was inspired by a previous data-center security architecture. Working on high-availability infrastructures revealed that traditional perimeter defenses are no longer sufficient against sophisticated, persistent threats. The modern connected aircraft is a "Data Center of the Sky" facing identical challenges with far stricter constraints: weight, power, and 30-year operational lifespans. The goal is to transpose server-grade defense-in-depth — combining PQC and AI-driven anomaly detection — into FPGA-based avionics, moving from reactive security to a proactive posture that remains resilient against threats that do not yet exist.
