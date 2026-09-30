import base64
import json
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import AES_GCM_KEY, APP_PASSWORD, APP_USERNAME

basic = HTTPBasic()


def require_user(
    credentials: HTTPBasicCredentials = Depends(basic),
):
    username_ok = secrets.compare_digest(
        credentials.username,
        APP_USERNAME,
    )
    password_ok = secrets.compare_digest(
        credentials.password,
        APP_PASSWORD,
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def _cipher():
    try:
        key = bytes.fromhex(AES_GCM_KEY)
    except ValueError as exc:
        raise RuntimeError(
            "AES_GCM_KEY must be 64 hexadecimal characters"
        ) from exc

    if len(key) != 32:
        raise RuntimeError(
            "AES_GCM_KEY must decode to exactly 32 bytes"
        )

    return AESGCM(key)


def encrypt_message(message: dict) -> bytes:
    nonce = os.urandom(12)
    ciphertext = _cipher().encrypt(
        nonce,
        json.dumps(message).encode("utf-8"),
        b"factory-demo-v1",
    )

    envelope = {
        "v": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }

    return json.dumps(envelope).encode("utf-8")


def decrypt_message(payload: bytes) -> dict:
    envelope = json.loads(payload)

    nonce = base64.b64decode(envelope["nonce"])
    ciphertext = base64.b64decode(envelope["ciphertext"])

    cleartext = _cipher().decrypt(
        nonce,
        ciphertext,
        b"factory-demo-v1",
    )

    return json.loads(cleartext)