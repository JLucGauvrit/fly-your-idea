import socket
import json
import os
import threading
import time

import requests

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("LISTEN_UDP_PORT", "9002"))

SAT_APP_HOST = os.environ.get("SAT_APP_HOST", "satellite-app")
SAT_APP_PORT = int(os.environ.get("SAT_APP_PORT", "9003"))

FPGA_URL = os.environ.get("FPGA_API_URL", "http://fpga-emulator:7000")


def wait_for_fpga(timeout: int = 60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{FPGA_URL}/docs", timeout=2)
            if r.status_code == 200:
                print(f"[satellite-sec-gw] FPGA API prête : {FPGA_URL}")
                return
        except requests.RequestException:
            pass
        print("[satellite-sec-gw] FPGA non disponible, nouvelle tentative dans 3s…")
        time.sleep(3)
    raise RuntimeError(f"FPGA API inaccessible après {timeout}s")


def handle_packet(data: bytes, src_addr: tuple, send_sock: socket.socket):
    try:
        secure_pkt = json.loads(data.decode("utf-8"))

        # --- Vérification signature ---
        verify = requests.post(
            f"{FPGA_URL}/verify", json={"data": secure_pkt}, timeout=5
        )
        verify.raise_for_status()
        verify_result = verify.json()

        if not verify_result.get("valid", False):
            print(
                f"[satellite-sec-gw] *** ALERTE SECURITE *** Signature invalide "
                f"depuis {src_addr} — paquet rejeté. "
                f"Raison: {verify_result.get('reason', 'inconnue')}"
            )
            return

        # --- Déchiffrement ---
        dec = requests.post(
            f"{FPGA_URL}/decrypt",
            json={"data": secure_pkt.get("ciphertext")},
            timeout=5,
        )
        dec.raise_for_status()
        dec_result = dec.json()

        plaintext = dec_result.get("plaintext")
        out = json.dumps(plaintext).encode("utf-8")
        send_sock.sendto(out, (SAT_APP_HOST, SAT_APP_PORT))

        seq = plaintext.get("seq", "?") if isinstance(plaintext, dict) else "?"
        print(
            f"[satellite-sec-gw] #{seq:04} vérifié+décrypté → {SAT_APP_HOST}:{SAT_APP_PORT}"
        )

    except Exception as exc:
        print(f"[satellite-sec-gw] Erreur traitement paquet depuis {src_addr}: {exc}")


def main():
    wait_for_fpga()

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind((LISTEN_HOST, LISTEN_PORT))

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[satellite-sec-gw] Écoute UDP sur {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"[satellite-sec-gw] Relais en clair vers {SAT_APP_HOST}:{SAT_APP_PORT}")

    while True:
        data, addr = recv_sock.recvfrom(65535)
        t = threading.Thread(
            target=handle_packet, args=(data, addr, send_sock), daemon=True
        )
        t.start()


if __name__ == "__main__":
    main()
