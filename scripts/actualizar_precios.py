"""Actualizador de precios de Zypuc.

Lee productos.json, visita los links de cada producto (tienda donde compramos
y tienda con la que comparamos) y guarda los precios encontrados en precios.json.
La tienda (index.html) lee precios.json y se actualiza sola.

Privacidad: el precio de compra, la tienda donde compramos y la comisión van
cifrados con la clave del equipo (secreto ZYPUC_CLAVE). Este script calcula el
precio Zypuc y publica solo ese ("sale"); lo de compra queda en "priv".

Reglas para no molestar a las tiendas ni mostrar datos falsos:
- Pocas visitas: una por link, con pausa entre cada una, unas pocas veces al día.
- Si no se puede leer un precio, se conserva el último precio bueno con su fecha.
  La tienda deja de mostrar "En X cuesta..." cuando ese dato tiene más de 7 días.
- Guarda un historial diario de cada precio (la tienda dibuja el gráfico).
- Si el precio nuevo es absurdo (menos de 40 % o más de 250 % del anterior),
  se descarta y se avisa en el resumen.

Uso:  python scripts/actualizar_precios.py
"""
from __future__ import annotations

import html
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from privado import cifrar, clave, descifrar  # noqa: E402

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


def imagen_tarjeta(item: dict) -> str | None:
    for k in ("mediaUrls", "imageUrls", "images"):
        v = item.get(k)
        if isinstance(v, list) and v and isinstance(v[0], str) and v[0].startswith("http"):
            return v[0]
    v = item.get("imageUrl") or item.get("image")
    return v if isinstance(v, str) and v.startswith("http") else None


ULTIMA_IMAGEN: dict = {}
ESTADO: dict = {}  # p. ej. {'stock': 'agotado'} cuando la tienda muestra el producto sin unidades


def precio_falabella_listado(doc: str, vendedor: str, palabras: list[str], fuera: list[str] | None = None) -> float | None:
    ULTIMA_IMAGEN.clear()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', doc, re.S)
    if not m:
        return None
    data = json.loads(m.group(1))
    candidatos = []
    for item in iter_resultados(data):
        nombre = sin_tildes(f"{item.get('brand', '')} {item.get('displayName', '')}")
        seller = sin_tildes(item.get("sellerName") or item.get("seller") or "")
        if palabras and not all(sin_tildes(w) in nombre for w in palabras):
            continue
        if any(sin_tildes(w) in nombre for w in (fuera if fuera is not None else EXCLUIR)):
            continue
        if vendedor and sin_tildes(vendedor) not in seller:
            continue
        p = precio_tarjeta(item)
        if p:
            candidatos.append((p, imagen_tarjeta(item)))
    if not candidatos:
        return None
    precio, img = min(candidatos, key=lambda c: c[0])
    if img:
        ULTIMA_IMAGEN["url"] = img
    return precio


VTEX = ("oechsle.pe", "plazavea.com.pe", "promart.pe", "coolbox.pe")
# Accesorios que comparten nombre con el producto (no deben contar como "el mismo producto")
EXCLUIR = ["funda", "case ", "protector", "correa", "cargador", "repuesto", "llavero", "mica ", "estuche"]


def sin_tildes(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFD", str(t or "").lower()).encode("ascii", "ignore").decode()


def precio_vtex(link: dict) -> float | None:
    """Tiendas VTEX (Oechsle, Plaza Vea, Promart, Coolbox) tienen una API pública de catálogo.
    - Con "q" + "match": precio MÁS BAJO de esa tienda para ese producto (comparación honesta).
    - Sin "q": el producto exacto del link (…/nombre/p)."""
    from urllib.parse import urlparse, quote
    u = urlparse(link["url"])
    base = f"{u.scheme}://{u.netloc}"
    if link.get("q"):
        api = f"{base}/api/catalog_system/pub/products/search?ft={quote(link['q'])}&_from=0&_to=29"
    else:
        slug = u.path.strip("/").split("/")[0]
        api = f"{base}/api/catalog_system/pub/products/search/{slug}/p"
    r = requests.get(api, headers={**HEADERS, "Accept": "application/json"}, timeout=30)
    if r.status_code not in (200, 206):
        return None
    palabras = [sin_tildes(w) for w in link.get("match", [])]
    fuera = [sin_tildes(w) for w in link.get("excluir", EXCLUIR)]
    vendedor = sin_tildes(link.get("seller", "")) if not link.get("q") else ""
    candidatos = []
    encontrado = False
    for prod in r.json():
        nombre = sin_tildes(f"{prod.get('brand', '')} {prod.get('productName', '')}")
        if palabras and not all(w in nombre for w in palabras):
            continue
        if any(w in nombre for w in fuera):
            continue
        encontrado = True
        for it in prod.get("items") or []:
            img = ((it.get("images") or [{}])[0]).get("imageUrl")
            for sel in it.get("sellers") or []:
                of = sel.get("commertialOffer") or {}
                if of.get("AvailableQuantity", 0) > 0 and of.get("Price"):
                    if vendedor and vendedor not in sin_tildes(sel.get("sellerName")):
                        continue
                    candidatos.append((float(of["Price"]), img))
    if not candidatos and vendedor:  # el vendedor ya no lo tiene: tomamos la mejor oferta del mismo producto
        return precio_vtex({**link, "seller": ""})
    if not candidatos:
        if encontrado and not link.get("q"):  # el producto existe pero nadie tiene unidades
            ESTADO["stock"] = "agotado"
        return None
    precio, img = min(candidatos, key=lambda c: c[0])
    if img:
        ULTIMA_IMAGEN["url"] = img
    return precio


def leer_precio(link: dict) -> tuple[float | None, str]:
    url = link["url"]
    if any(d in url for d in VTEX):
        return precio_vtex(link), "vtex-minimo" if link.get("q") else "vtex"
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    doc = r.text
    if "ripley.com.pe" in url:
        return precio_ripley(doc), "ripley"
    if "falabella.com.pe" in url and "/product/" in url:
        p = precio_json_ld(doc) or precio_meta(doc)
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', doc)
        if p and m:
            ULTIMA_IMAGEN["url"] = html.unescape(m.group(1))
        return p, "falabella-producto"
    if "falabella.com.pe" in url:
        return precio_falabella_listado(doc, link.get("seller", ""), link.get("match", []), link.get("excluir")), "falabella-listado"
    return (precio_json_ld(doc) or precio_meta(doc)), "generico"


CARPETA_PRIVADA = RAIZ / ".privado"   # solo existe dentro de GitHub Actions; no se sube (ver .gitignore)
FOTOS_COMPRA = CARPETA_PRIVADA / "fotos-compra.json"
# Datos de compra que nunca se publican sin cifrar (van dentro de "priv")
CAMPOS_PRIVADOS = ("price", "url", "store", "seller", "q", "match", "excluir", "comision")


def redondeo90(x: float) -> float:
    """Igual que round90() de la tienda: sube al siguiente ",90"."""
    e = math.floor(x)
    return round(e + 0.9 if x <= e + 0.9 else e + 1.9, 2)


def precio_venta(p: dict, privado: dict, compra, cfg: dict, comision) -> float | None:
    """Precio Zypuc = (precio de compra + envío) × (1 + comisión), redondeado a ",90"."""
    if not compra or compra <= 0:
        return None
    com = privado.get("comision", comision)
    if com is None:
        return None
    envio = p.get("envio")
    envio = cfg.get("envioPorUnidad", 0) if envio is None else envio
    return redondeo90((compra + envio) * (1 + com / 100))


def main() -> int:
    datos = json.loads(PRODUCTOS.read_text(encoding="utf-8"))
    cfg = datos["config"]
    productos = datos["productos"]
    previo = json.loads(PRECIOS.read_text(encoding="utf-8")) if PRECIOS.exists() else {"items": {}}
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    salida = {"updated": ahora, "items": {}}
    resumen = []

    # ---------- clave del equipo ----------
    contrasena = os.environ.get("ZYPUC_CLAVE", "").strip()
    k = clave(contrasena, cfg["adminSalt"]) if contrasena and cfg.get("adminSalt") else None
    if k and cfg.get("adminCheck"):
        try:
            if descifrar(cfg["adminCheck"], k) != "zypuc-ok":
                raise ValueError
        except Exception:
            k = None
            resumen.append("🔒 La clave ZYPUC_CLAVE no es la correcta: no se revisaron los precios de compra.")
    elif not k:
        resumen.append("🔒 Falta el secreto ZYPUC_CLAVE: no se revisaron los precios de compra.")

    # ---------- lo privado se cifra (comisión, precio y tienda de compra) ----------
    cambio_productos = False
    cfg_priv: dict = {}
    if k and cfg.get("priv"):
        try:
            cfg_priv = descifrar(cfg["priv"], k)
        except Exception:
            resumen.append("🔒 No se pudo leer la configuración cifrada.")
    if k and "comision" in cfg:
        cfg_priv["comision"] = cfg.pop("comision")
        cfg["priv"] = cifrar(cfg_priv, k)
        cambio_productos = True
    comision = cfg_priv.get("comision", cfg.get("comision"))

    privados: dict = {}  # id -> datos de compra descifrados
    if k:
        for p in productos:
            b = p.get("buy")
            if not b:
                continue
            try:
                dp = descifrar(b["priv"], k) if b.get("priv") else {}
            except Exception:
                resumen.append(f"🔒 {p['id']}: no se pudo descifrar su link de compra.")
                continue
            sueltos = {c: b.pop(c) for c in CAMPOS_PRIVADOS if c in b}
            if "comision" in p:
                sueltos["comision"] = p.pop("comision")
            if sueltos:  # datos que estaban a la vista: pasan a la parte cifrada
                dp.update(sueltos)
                b["priv"] = cifrar(dp, k)
                cambio_productos = True
            venta = precio_venta(p, dp, dp.get("price"), cfg, comision)
            if venta and b.get("sale") != venta:
                b["sale"] = venta
                cambio_productos = True
            privados[p["id"]] = dp

    fotos_compra: dict = {}

    for p in productos:
        for lado in ("buy", "ref"):
            link = p.get(lado)
            if not link:
                continue
            guardado = previo.get("items", {}).get(p["id"], {})
            if lado == "buy":
                if p["id"] not in privados:  # sin clave: se conserva lo publicado, tal cual
                    for c in ("buy", "sale"):
                        if c in guardado:
                            salida["items"].setdefault(p["id"], {})[c] = guardado[c]
                    continue
                dp = privados[p["id"]]
                link = {**link, **dp}
                anterior = guardado.get("buy") or {}
                if "priv" in anterior:
                    try:
                        anterior = descifrar(anterior["priv"], k)
                    except Exception:
                        anterior = {}
                anterior = anterior or {"price": dp.get("price"), "checked": p["buy"].get("checked")}
            else:
                anterior = guardado.get(lado) or {"price": link.get("price"), "checked": link.get("checked")}
            if not link.get("url"):
                continue
            privado = lado == "buy"
            nuevo = {k2: v for k2, v in dict(anterior).items() if k2 != "method"}
            nuevo["lastTry"] = ahora
            ULTIMA_IMAGEN.clear()
            ESTADO.clear()
            precio, metodo = None, "sin intentar"
            for intento in range(2):  # un reintento si la red falla
                try:
                    precio, metodo = leer_precio(link)
                    break
                except Exception as e:  # red caída, bloqueo, etc.
                    precio, metodo = None, f"error: {type(e).__name__}"
                    time.sleep(4)
            if privado:  # no dejamos pistas de la tienda en los registros públicos
                metodo = "privado" if precio else ("privado: " + metodo.split(":")[0] if metodo.startswith(("HTTP", "error")) else "privado")
            etiqueta = "compra" if lado == "buy" else "otra tienda"
            base = anterior.get("price") or link.get("price")
            if precio and base and not (0.4 * base <= precio <= 2.5 * base):
                # Los registros de GitHub Actions son públicos: el precio de compra nunca se escribe ahí
                detalle = "precio raro" if privado else f"precio raro {precio} vs {base}"
                resumen.append(f"⚠️ {p['id']} ({etiqueta}): {detalle}, descartado")
                precio = None
            if lado == "buy":
                if precio:
                    nuevo.pop("stock", None)
                elif ESTADO.get("stock") == "agotado":
                    nuevo["stock"] = "agotado"
                    resumen.append(f"📦 {p['id']} (compra): agotado en la tienda")
            if precio:
                nuevo.update(price=round(precio, 2), checked=ahora, ok=True, method=metodo)
                resumen.append(f"✅ {p['id']} ({etiqueta}): " + ("revisado" if privado else f"S/ {precio:.2f}"))
            else:
                nuevo.update(ok=False, method=metodo)
                resumen.append(f"❌ {p['id']} ({etiqueta}): no se pudo leer [{metodo}], se mantiene el último precio"
                               + ("" if privado else f" (S/ {base})"))
            if ULTIMA_IMAGEN.get("url"):
                nuevo["image"] = ULTIMA_IMAGEN["url"]
            # Historial: un punto por día (el último precio leído ese día), máximo 120 días
            hist = [h for h in (anterior.get("history") or []) if isinstance(h, list) and len(h) == 2]
            if not hist and anterior.get("price"):
                hist = [[str(anterior.get("checked") or link.get("checked") or "")[:10], anterior["price"]]]
            if precio:
                hoy = ahora[:10]
                if hist and hist[-1][0] == hoy:
                    hist[-1] = [hoy, round(precio, 2)]
                else:
                    hist.append([hoy, round(precio, 2)])
            nuevo["history"] = hist[-120:]
            if privado:
                # Afuera solo queda el precio Zypuc (de venta); la compra va cifrada
                foto = nuevo.pop("image", None)
                if foto:
                    fotos_compra[p["id"]] = foto
                venta = {"price": precio_venta(p, dp, nuevo.get("price"), cfg, comision),
                         "checked": nuevo.get("checked"), "lastTry": ahora, "ok": bool(nuevo.get("ok"))}
                serie = []
                for dia, valor in nuevo["history"]:
                    v = precio_venta(p, dp, valor, cfg, comision)
                    if v:
                        serie.append([dia, v])
                venta["history"] = serie
                if nuevo.get("stock"):
                    venta["stock"] = nuevo["stock"]
                item = salida["items"].setdefault(p["id"], {})
                item["buy"] = {"priv": cifrar(nuevo, k)}
                if venta["price"]:
                    item["sale"] = venta
            else:
                salida["items"].setdefault(p["id"], {})[lado] = nuevo
            # Las APIs de catálogo responden rápido; las páginas HTML necesitan más pausa
            time.sleep(random.uniform(1, 2) if any(d in link.get("url", "") for d in VTEX) else random.uniform(3, 5))

    if cambio_productos:
        PRODUCTOS.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    PRECIOS.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    if fotos_compra:  # para localizar_imagenes.py; esta carpeta no se publica
        CARPETA_PRIVADA.mkdir(exist_ok=True)
        FOTOS_COMPRA.write_text(json.dumps(fotos_compra, ensure_ascii=False), encoding="utf-8")
    print("\n".join(resumen))
    resumen_md = Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None
    if resumen_md:
        resumen_md.write_text("## Precios Zypuc\n\n" + "\n".join(f"- {l}" for l in resumen) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
