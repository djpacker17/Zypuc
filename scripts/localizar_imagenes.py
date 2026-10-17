"""Guarda las fotos de los productos dentro de la web (carpeta img/).

Así la tienda no depende de los servidores de otras tiendas y las fotos no delatan
dónde compramos cada producto. Se corre después de actualizar_precios.py.
"""
from __future__ import annotations

import io
import json
import pathlib
import time

import requests
from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PRODUCTOS = RAIZ / "productos.json"
PRECIOS = RAIZ / "precios.json"
CARPETA = RAIZ / "img"
LADO = 800  # px, lado mayor
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def descargar(url: str, destino: pathlib.Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200 or len(r.content) < 1500:
            return False
        im = Image.open(io.BytesIO(r.content))
        im = im.convert("RGBA") if im.mode in ("P", "LA") else im
        if im.mode == "RGBA":  # fondo blanco para fotos con transparencia
            fondo = Image.new("RGB", im.size, (255, 255, 255))
            fondo.paste(im, mask=im.split()[-1])
            im = fondo
        im = im.convert("RGB")
        im.thumbnail((LADO, LADO), Image.LANCZOS)
        destino.parent.mkdir(exist_ok=True)
        im.save(destino, "JPEG", quality=82, optimize=True, progressive=True)
        return True
    except Exception as e:  # noqa: BLE001
        print("  no se pudo:", type(e).__name__)
        return False


def main() -> int:
    datos = json.loads(PRODUCTOS.read_text(encoding="utf-8"))
    precios = json.loads(PRECIOS.read_text(encoding="utf-8")) if PRECIOS.exists() else {"items": {}}
    items = precios.get("items", {})
    nuevas = fallidas = 0
    for p in datos["productos"]:
        pid = p["id"]
        local = f"img/{pid}.jpg"
        archivo = RAIZ / local
        vivo = (items.get(pid, {}).get("buy") or {}).get("image")
        if archivo.exists() and p.get("image") == local:
            continue
        fuentes = [u for u in (p.get("image"), vivo) if u and str(u).startswith("http")]
        if not fuentes:
            continue
        if any(descargar(u, archivo) for u in dict.fromkeys(fuentes)):  # prueba cada foto hasta que una funcione
            p["image"] = local
            p.pop("imageAuto", None)
            nuevas += 1
        else:
            fallidas += 1
        time.sleep(0.4)
    # Las direcciones de las fotos originales no se publican: delatan la tienda de compra.
    con_local = {p["id"] for p in datos["productos"] if str(p.get("image", "")).startswith("img/")}
    for pid, it in items.items():
        if pid in con_local and isinstance(it.get("buy"), dict):
            it["buy"].pop("image", None)
    PRODUCTOS.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    if PRECIOS.exists():
        PRECIOS.write_text(json.dumps(precios, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fotos nuevas: {nuevas} · sin descargar: {fallidas} · en la web: {len(con_local)}/{len(datos['productos'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
