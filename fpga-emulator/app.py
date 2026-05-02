import base64
import json
import hashlib
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="PQC FPGA Emulator", version="0.1.0")


class Payload(BaseModel):
    data: Any = None


def _short_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


@app.post("/kem/init")
async def kem_init():
    return {
        "status": "success",
        "kem_algorithm": "CRYSTALS-Kyber-1024",
        "public_key": "mocked_kyber_pubkey_" + "a1b2c3d4e5f67890",
        "private_key": "mocked_kyber_privkey_" + "0987f6e5d4c3b2a1",
    }


@app.post("/sign")
async def sign(payload: Payload):
    sig = "DILITHIUM3_SIG_" + _short_hash(payload.data)
    return {
        "status": "success",
        "algorithm": "CRYSTALS-Dilithium3",
        "signature": sig,
    }


@app.post("/verify")
async def verify(payload: Payload):
    # Mock: toujours valide sauf si la signature contient "FORGED"
    sig = ""
    if isinstance(payload.data, dict):
        sig = str(payload.data.get("signature", ""))
    is_valid = "FORGED" not in sig
    return {
        "status": "success",
        "algorithm": "CRYSTALS-Dilithium3",
        "valid": is_valid,
        "reason": "ok" if is_valid else "signature_invalide_detectee",
    }


@app.post("/encrypt")
async def encrypt(payload: Payload):
    # Mock "chiffrement" : base64 du JSON original préfixé d'un tag
    encoded = base64.b64encode(
        json.dumps(payload.data, default=str).encode()
    ).decode()
    ciphertext = f"KYBER1024::{encoded}"
    return {
        "status": "success",
        "algorithm": "CRYSTALS-Kyber-1024",
        "ciphertext": ciphertext,
    }


@app.post("/decrypt")
async def decrypt(payload: Payload):
    ciphertext = str(payload.data or "")
    try:
        if "::" in ciphertext:
            _, encoded = ciphertext.split("::", 1)
            plaintext = json.loads(base64.b64decode(encoded).decode())
        else:
            plaintext = {"error": "ciphertext_invalide", "raw": ciphertext}
    except Exception as exc:
        plaintext = {"error": str(exc), "raw": ciphertext}
    return {
        "status": "success",
        "algorithm": "CRYSTALS-Kyber-1024",
        "plaintext": plaintext,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7000, log_level="info")
