"""
RedTeam Console — Quantum-Ready Sky
Usages :
  python app.py --mode inject              # un seul paquet forgé
  python app.py --mode replay --count 10  # 10 rejeux
  python app.py --mode loop --interval 3  # boucle infinie
"""
import argparse
import json
import os
import socket
import time

from scapy.all import IP, UDP, Raw, conf, send

TARGET_GW_HOST = os.environ.get("TARGET_GW_HOST", "satellite-sec-gw")
TARGET_GW_PORT = int(os.environ.get("TARGET_GW_PORT", "9002"))
SPOOF_SRC_IP = os.environ.get("SPOOF_SRC_IP", "10.10.10.100")

conf.verb = 0  # silence scapy


def resolve_ip(hostname: str) -> str:
    try:
        ip = socket.gethostbyname(hostname)
        print(f"[redteam] {hostname} → {ip}")
        return ip
    except socket.gaierror as exc:
        print(f"[redteam] Résolution DNS échouée pour '{hostname}': {exc}")
        return hostname


def forge_packet(target_ip: str, target_port: int, src_ip: str, payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def inject(target_ip: str, target_port: int, src_ip: str, payload: dict):
    raw = json.dumps(payload).encode("utf-8")
    pkt = IP(src=src_ip, dst=target_ip) / UDP(sport=6666, dport=target_port) / Raw(load=raw)
    send(pkt)
    print(
        f"[redteam] INJECT → {target_ip}:{target_port}  "
        f"src_spoofed={src_ip}  "
        f"sig={payload.get('signature', '?')[:30]}…"
    )


def build_evil_packet(label: str = "") -> dict:
    return {
        "ciphertext": f"INJECTED_evil_payload_{label or int(time.time())}",
        "signature": f"FORGED_DILITHIUM3_{label or int(time.time())}",
        "kem_algo": "CRYSTALS-Kyber-1024",
        "sig_algo": "CRYSTALS-Dilithium3",
    }


def main():
    parser = argparse.ArgumentParser(description="RedTeam Console — Quantum-Ready Sky")
    parser.add_argument("--mode", choices=["inject", "replay", "loop"], default="inject")
    parser.add_argument("--target", default=TARGET_GW_HOST)
    parser.add_argument("--port", type=int, default=TARGET_GW_PORT)
    parser.add_argument("--src-ip", default=SPOOF_SRC_IP)
    parser.add_argument("--count", type=int, default=5, help="Nombre de paquets (mode replay)")
    parser.add_argument("--interval", type=float, default=2.0, help="Intervalle en secondes")
    args = parser.parse_args()

    target_ip = resolve_ip(args.target)

    print(f"[redteam] Mode={args.mode}  cible={target_ip}:{args.port}  src_ip={args.src_ip}")
    print(f"[redteam] Attention : la signature 'FORGED' sera détectée et rejetée par satellite-sec-gw")

    if args.mode == "inject":
        inject(target_ip, args.port, args.src_ip, build_evil_packet("single"))

    elif args.mode == "replay":
        print(f"[redteam] Replay x{args.count} avec intervalle {args.interval}s")
        for i in range(args.count):
            inject(target_ip, args.port, args.src_ip, build_evil_packet(f"replay_{i}"))
            if i < args.count - 1:
                time.sleep(args.interval)
        print(f"[redteam] Replay terminé ({args.count} paquets)")

    elif args.mode == "loop":
        print(f"[redteam] Boucle infinie (intervalle={args.interval}s) — Ctrl+C pour arrêter")
        i = 0
        while True:
            inject(target_ip, args.port, args.src_ip, build_evil_packet(f"loop_{i}"))
            i += 1
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
