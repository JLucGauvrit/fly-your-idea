import socket
import json
import os

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("LISTEN_UDP_PORT", "9003"))


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    print(f"[satellite-app] Écoute UDP sur {LISTEN_HOST}:{LISTEN_PORT} — en attente de données avion")

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            payload = json.loads(data.decode("utf-8"))
            seq = payload.get("seq", "?")
            print(
                f"[satellite-app] Reçu de l'avion (src={addr[0]}) "
                f"#{seq:04} : alt={payload.get('altitude_ft')} ft  "
                f"spd={payload.get('speed_kts')} kts  "
                f"fuel={payload.get('fuel_kg')} kg"
            )
        except (json.JSONDecodeError, AttributeError):
            print(f"[satellite-app] Paquet brut depuis {addr}: {data!r}")


if __name__ == "__main__":
    main()
