import socket
import json
import time
import random
import os

GATEWAY_HOST = os.environ.get("AIRCRAFT_GW_HOST", "aircraft-sec-gw")
GATEWAY_PORT = int(os.environ.get("AIRCRAFT_GW_PORT", "9001"))


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"[aircraft-app] Démarrage — envoi telemetry vers {GATEWAY_HOST}:{GATEWAY_PORT} toutes les 2s")

    seq = 0
    while True:
        telemetry = {
            "seq": seq,
            "timestamp": round(time.time(), 3),
            "altitude_ft": round(35000 + random.uniform(-300, 300), 1),
            "speed_kts": round(480 + random.uniform(-15, 15), 1),
            "heading_deg": round(245 + random.uniform(-3, 3), 1),
            "engine_n1_pct": round(88.5 + random.uniform(-1.5, 1.5), 2),
            "fuel_kg": round(max(0, 12000 - seq * 0.45), 1),
            "vertical_speed_fpm": round(random.uniform(-50, 50), 1),
        }

        raw = json.dumps(telemetry).encode("utf-8")
        try:
            sock.sendto(raw, (GATEWAY_HOST, GATEWAY_PORT))
            print(f"[aircraft-app] #{seq:04d} envoyé  alt={telemetry['altitude_ft']} ft  spd={telemetry['speed_kts']} kts")
        except OSError as exc:
            print(f"[aircraft-app] Erreur envoi #{seq}: {exc}")

        seq += 1
        time.sleep(2)


if __name__ == "__main__":
    main()
