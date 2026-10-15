"""Cifrado de los datos privados de Zypuc (dónde compramos cada producto).

Los links de la tienda más barata viajan cifrados dentro de productos.json
("buy" -> "priv"). Solo se pueden leer con la contraseña del equipo:
- en la tienda, entrando como LeoZypuc;
- en GitHub Actions, con el secreto ZYPUC_CLAVE.

Formato: base64( iv de 12 bytes + texto cifrado AES-256-GCM ).
Clave: PBKDF2-HMAC-SHA256(contraseña, sal de config.adminSalt, 150 000 vueltas).
Es el mismo formato que usa la tienda en el navegador (WebCrypto).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VUELTAS = 150_000


def clave(contrasena: str, sal_hex: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal_hex), VUELTAS, 32)


def cifrar(dato, k: bytes) -> str:
    iv = os.urandom(12)
    texto = json.dumps(dato, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(iv + AESGCM(k).encrypt(iv, texto, None)).decode("ascii")


def descifrar(blob: str, k: bytes):
    crudo = base64.b64decode(blob)
    return json.loads(AESGCM(k).decrypt(crudo[:12], crudo[12:], None).decode("utf-8"))
