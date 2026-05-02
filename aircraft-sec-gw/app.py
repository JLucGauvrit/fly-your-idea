import socket
import json
import os
import threading
import time

import requests

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("LISTEN_UDP_PORT", "9001"))

SAT_GW_HOST = os.environ.get("SAT_GW_HOST", "satellite-sec-gw")
SAT_GW_PORT = int(os.environ.get("SAT_GW_PORT", "9002"))

FPGA_URL = os.environ.get("FPGA_API_URL", "http://fpga-emulator:7000")


def wait_for_fpga(timeout: int = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{FPGA_URL}/docs", timeout=2)
            if r.status_code == 200:
                print(f"[aircraft-sec-gw] FPGA API prête : {FPGA_URL}")
                return
        except requests.RequestException:
            pass
        print("[aircraft-sec-gw] FPGA non disponible, nouvelle tentative dans 3s…")
        time.sleep(3)
    raise RuntimeError(f"FPGA API inaccessible après {timeout}s")


def handle_packet(data: bytes, send_sock: socket.socket):
    try:
        payload = json.loads(data.decode("utf-8"))
        seq = payload.get("seq", "?")

        enc = requests.post(f"{FPGA_URL}/encrypt", json={"data": payload}, timeout=5)
        enc.raise_for_status()
        enc_result = enc.json()

        sig = requests.post(
            f"{FPGA_URL}/sign",
            json={"data": enc_result["ciphertext"]},
            timeout=5,
        )
        sig.raise_for_status()
        sig_result = sig.json()

        secure_pkt = {
            "ciphertext": enc_result["ciphertext"],
            "signature": sig_result["signature"],
            "kem_algo": enc_result["algorithm"],
            "sig_algo": sig_result["algorithm"],
        }

        out = json.dumps(secure_pkt).encode("utf-8")
        send_sock.sendto(out, (SAT_GW_HOST, SAT_GW_PORT))
        print(
            f"[aircraft-sec-gw] #{seq:04} → chiffré+signé → {SAT_GW_HOST}:{SAT_GW_PORT} "
            f"({len(out)} octets)"
        )

    except Exception as exc:
        print(f"[aircraft-sec-gw] Erreur traitement paquet: {exc}")


def main():
    wait_for_fpga()

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind((LISTEN_HOST, LISTEN_PORT))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[aircraft-sec-gw] Écoute UDP sur {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"[aircraft-sec-gw] Relais vers {SAT_GW_HOST}:{SAT_GW_PORT}")

    while True:
        data, _addr = recv_sock.recvfrom(65535)
        t = threading.Thread(target=handle_packet, args=(data, send_sock), daemon=True)
        t.start()


if __name__ == "__main__":
    main()
