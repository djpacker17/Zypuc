"""Actualizador de precios de Zypuc.

Lee productos.json, visita los links de cada producto (tienda donde compramos
y tienda con la que comparamos) y guarda los precios encontrados en precios.json.
La tienda (index.html) lee precios.json y recalcula todo sola.

Reglas para no molestar a las tiendas ni mostrar datos falsos:
- Pocas visitas: una por link, con pausa entre cada una, unas pocas veces al día.
- Si no se puede leer un precio, se conserva el último precio bueno con su fecha.
  La tienda deja de mostrar "En X cuesta..." cuando ese dato tiene más de 7 días.
- Si el precio nuevo es absurdo (menos de 40 % o más de 250 % del anterior),
  se descarta y se avisa en el resumen.

Uso:  python scripts/actualizar_precios.py
"""
from __future__ import annotations

import html
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PRODUCTOS = RAIZ / "productos.json"
PRECIOS = RAIZ / "precios.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-PE,es;q=0.9",
}
PRECIO_RE = r"([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)"


def a_numero(txt: str) -> float | None:
    """Convierte '1,299.90', '1.299,90', '129' o '129.00' a número."""
    t = str(txt).strip().replace("S/", "").replace(" ", "")
    if not t:
        return None
    if "," in t and "." in t:
        t = t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")
    elif "," in t:
        partes = t.split(",")
        t = t.replace(",", ".") if len(partes[-1]) in (1, 2) else t.replace(",", "")
    try:
        v = float(t)
    except ValueError:
        return None
    return v if 0.5 <= v <= 100000 else None


# ---------- lectores de precio ----------

def precio_json_ld(doc: str) -> float | None:
    for bloque in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', doc, re.S | re.I):
        try:
            data = json.loads(html.unescape(bloque.strip()))
        except Exception:
            continue
        pila = data if isinstance(data, list) else [data]
        while pila:
            nodo = pila.pop()
            if isinstance(nodo, list):
                pila.extend(nodo)
                continue
            if not isinstance(nodo, dict):
                continue
            ofertas = nodo.get("offers")
            if ofertas:
                for o in (ofertas if isinstance(ofertas, list) else [ofertas]):
                    if isinstance(o, dict):
                        for k in ("price", "lowPrice"):
                            v = a_numero(o.get(k, ""))
                            if v:
                                return v
            pila.extend(v for v in nodo.values() if isinstance(v, (dict, list)))
    return None


def precio_meta(doc: str) -> float | None:
    m = re.search(r'<meta[^>]+(?:property|itemprop|name)="(?:product:price:amount|price)"[^>]+content="([^"]+)"', doc, re.I)
    return a_numero(m.group(1)) if m else None


def texto_plano(doc: str) -> str:
    doc = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", doc, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", doc)))


def precio_ripley(doc: str) -> float | None:
    """Ripley muestra 'Internet S/ 184.00' (y a veces 'Tarjeta Ripley S/ ...')."""
    txt = texto_plano(doc)
    for etiqueta in ("Internet", "Precio Internet", "Precio oferta"):
        m = re.search(etiqueta + r"\s*S/\s*" + PRECIO_RE, txt)
        if m:
            return a_numero(m.group(1))
    return precio_json_ld(doc) or precio_meta(doc)


def iter_resultados(obj):
    """Recorre el JSON de Next.js de Falabella buscando tarjetas de producto."""
    pila = [obj]
    while pila:
        n = pila.pop()
        if isinstance(n, dict):
            if "displayName" in n and "prices" in n:
                yield n
            pila.extend(n.values())
        elif isinstance(n, list):
            pila.extend(n)


def precio_tarjeta(item: dict) -> float | None:
    valores = []
    for p in item.get("prices") or []:
        if not isinstance(p, dict):
            continue
        for v in (p.get("price") or []):
            n = a_numero(v)
            if n:
                valores.append(n)
    return min(valores) if valores else None


def precio_falabella_listado(doc: str, vendedor: str, palabras: list[str]) -> float | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', doc, re.S)
    if not m:
        return None
    data = json.loads(m.group(1))
    candidatos = []
    for item in iter_resultados(data):
        nombre = f"{item.get('brand', '')} {item.get('displayName', '')}".lower()
        seller = str(item.get("sellerName") or item.get("seller") or "").lower()
        if palabras and not all(w.lower() in nombre for w in palabras):
            continue
        if vendedor and vendedor.lower() not in seller:
            continue
        p = precio_tarjeta(item)
        if p:
            candidatos.append(p)
    return min(candidatos) if candidatos else None


def leer_precio(link: dict) -> tuple[float | None, str]:
    url = link["url"]
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    doc = r.text
    if "ripley.com.pe" in url:
        return precio_ripley(doc), "ripley"
    if "falabella.com.pe" in url and "/product/" in url:
        return (precio_json_ld(doc) or precio_meta(doc)), "falabella-producto"
    if "falabella.com.pe" in url:
        return precio_falabella_listado(doc, link.get("seller", ""), link.get("match", [])), "falabella-listado"
    return (precio_json_ld(doc) or precio_meta(doc)), "generico"


def main() -> int:
    productos = json.loads(PRODUCTOS.read_text(encoding="utf-8"))["productos"]
    previo = json.loads(PRECIOS.read_text(encoding="utf-8")) if PRECIOS.exists() else {"items": {}}
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    salida = {"updated": ahora, "items": {}}
    resumen = []

    for p in productos:
        for lado in ("buy", "ref"):
            link = p.get(lado)
            if not link or not link.get("url"):
                continue
            anterior = previo.get("items", {}).get(p["id"], {}).get(lado) or {
                "price": link.get("price"), "checked": link.get("checked")}
            nuevo = dict(anterior)
            nuevo["lastTry"] = ahora
            try:
                precio, metodo = leer_precio(link)
            except Exception as e:  # red caída, bloqueo, etc.
                precio, metodo = None, f"error: {type(e).__name__}"
            base = anterior.get("price") or link.get("price")
            if precio and base and not (0.4 * base <= precio <= 2.5 * base):
                resumen.append(f"⚠️ {p['id']} ({lado}): precio raro {precio} vs {base}, descartado")
                precio = None
            if precio:
                nuevo.update(price=round(precio, 2), checked=ahora, ok=True, method=metodo)
                resumen.append(f"✅ {p['id']} ({lado}): S/ {precio:.2f} [{metodo}]")
            else:
                nuevo.update(ok=False, method=metodo)
                resumen.append(f"❌ {p['id']} ({lado}): no se pudo leer [{metodo}], se mantiene S/ {base}")
            salida["items"].setdefault(p["id"], {})[lado] = nuevo
            time.sleep(random.uniform(3, 6))

    PRECIOS.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(resumen))
    resumen_md = Path(__import__("os").environ.get("GITHUB_STEP_SUMMARY", "")) if __import__("os").environ.get("GITHUB_STEP_SUMMARY") else None
    if resumen_md:
        resumen_md.write_text("## Precios Zypuc\n\n" + "\n".join(f"- {l}" for l in resumen) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
