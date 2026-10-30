# Zypuc · Tienda en línea

Tienda de Zypuc (tecnología, deporte, repostería y regalitos) con entrega en Pucallpa.
Los pedidos llegan por WhatsApp al **+51 939 670 295**.

## Marca

- **Eslogan:** Lo que buscas, cerca.
- **Colores:** azul eléctrico `#0B5ED7`, turquesa `#14B8A6`, ámbar `#F59E0B` (acento), azul noche `#0F172A` y blanco.
- **Tipografías (Google Fonts):** Fredoka para títulos y Nunito Sans para textos.
- Texto oscuro sobre turquesa o ámbar; texto blanco solo sobre azul o azul noche.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `index.html` | La tienda completa. Se abre con doble clic o desde GitHub Pages. |
| `productos.json` | **La lista de productos.** Aquí se agregan, quitan o editan productos. |
| `precios.json` | Lo escribe solo el actualizador de precios. No hace falta tocarlo. |
| `resenas.json` | Reseñas publicadas (se generan desde el Panel Zypuc). |
| `pedidos.json` | Estado de cada pedido para "Rastrea tu pedido" (se genera desde el Panel Zypuc). |
| `scripts/privado.py` | Cifra y descifra los links de compra. |
| `scripts/apps-script.gs` | Código del Centro de datos (Google Sheets). La copia real, con la clave, está en tu Drive. |
| `scripts/actualizar_precios.py` | Programa que visita los links de cada producto y lee el precio. |
| `.github/workflows/precios.yml` | Le dice a GitHub que corra el actualizador cada 6 horas. |
| `logo-claro.png`, `logo-oscuro.png` | Logo para fondo claro y para modo oscuro. |
| `marca/` | Logo en SVG y PNG (claro, oscuro, grande), Zypi solo (`zypi.svg`, el mismo que usa la mascota flotante) y el ícono para foto de perfil. |
| `og.png` | Imagen que aparece al compartir el link por WhatsApp o Facebook. |
| `manifest.webmanifest`, `sw.js`, `app-icon-*.png`, `apple-touch-icon-v3.png`, `favicon*` | Permiten instalar la tienda como app en el celular (con atajos a Productos, Antojitos y Rastrear) y abrirla sin internet. |

## Cómo se calcula el precio

```
Precio Zypuc = (precio en la tienda donde compramos + envío a Pucallpa) × (1 + comisión)
```

Se redondea al siguiente ",90". El envío (S/ 8 por unidad) y la comisión (15 %) se cambian en `config` dentro de `productos.json`. Un producto puede tener su propio `"envio"` o `"comision"` (por ejemplo, la bicicleta tiene envío S/ 25).

El aviso **"En Ripley cuesta S/ X · Ver en Ripley"** solo aparece si:
1. esa tienda de verdad lo vende más caro que nuestro precio, y
2. el precio de esa tienda se revisó hace 7 días o menos.

Si el actualizador no puede leer un precio, guarda el último precio bueno con su fecha. Pasados 7 días sin poder revisarlo, el aviso desaparece solo. Así nunca mostramos una comparación vieja o falsa.

## Qué tiendas se revisan solas

| Tienda | ¿El actualizador la lee? |
|---|---|
| Falabella | Sí (páginas de producto y búsquedas) |
| Oechsle, Plaza Vea, Promart, Coolbox | Sí (usan una API pública de catálogo) |
| Ripley | No: bloquea a GitHub |

- Las **compras** están todas en tiendas que se leen solas.
- En las comparaciones con Oechsle, Plaza Vea, Promart o Coolbox el actualizador busca el **precio más bajo de esa tienda** para ese producto (no el de un vendedor caro), así la comparación siempre es honesta.
- Las comparaciones con **Ripley** se confirman a mano: **Panel → Revisar comparaciones** (toma 2 minutos a la semana). Si no se confirman, se ocultan solas a los 7 días.

## Minijuegos

**Zypi Catch**: Zypi atrapa productos con su canasta y esquiva etiquetas de precio inflado. Tiene combos, poderes (imán, escudo, x2, cámara lenta, +1 vida) y tres modos:
- **Clásico**: 3 vidas, la dificultad sube por niveles.
- **Contrarreloj**: 60 segundos; cada etiqueta inflada resta 3 segundos.
- **Zen**: sin etiquetas malas ni vidas, para relajarse.

**Memoria Zypuc**: voltea cartas y encuentra las parejas (Fácil 4×3, Normal 4×4, Difícil 6×4).

Los récords se guardan por modo y por nivel en cada dispositivo. Varios logros secretos se desbloquean jugando.

## Centro de datos (Google Sheets)

Con la hoja **Zypuc · Centro de datos** de tu Drive conectada, la tienda:
- guarda cada pedido en la pestaña **Pedidos** (además del WhatsApp de siempre). Cambias el **Estado** ahí y "Rastrea tu pedido" se actualiza solo;
- recibe reseñas en **Reseñas**: marcas la casilla **Aprobada** y se publican;
- guarda los "Avísame si baja de precio" en **Avisos** y te manda un correo cuando el precio baja;
- cuenta vistas, carritos y compartidos por producto (anónimo) en **Estadísticas**;
- te manda un resumen diario por correo a las 7 a. m.

Para conectarlo: abre la hoja → Extensiones → Apps Script → pega el código → Implementar → Aplicación web (acceso: cualquier usuario) → copia la URL que termina en `/exec` y ponla en `config.sheetsApi` de `productos.json` (o en **Panel → Centro de datos**, que genera el archivo listo).

## Cupones de descuento

En la pestaña **Cupones** de la hoja de Google cada fila es un cupón: código, tipo (`%` o `S/`), valor, compra mínima, fecha de vencimiento, **Activo** (`sí`/`no`) y máximo de usos. El cliente lo escribe en el checkout; la hoja lo valida y suma un uso cuando llega el pedido. El pedido guarda qué cupón se usó.

## Encargos ("Pídelo y te lo cotizamos")

Lo que los clientes piden y no está en la tienda llega a la pestaña **Encargos** (y también por WhatsApp). En el Panel → Pedidos y reseñas se cambia el estado (nuevo, cotizado, pedido, descartado) y se anota la respuesta. Sirve para saber qué productos agregar.

## Agotados y "Bajó de precio"

- Si una tienda muestra el producto sin unidades, el actualizador lo marca **Agotado** y el botón de compra se desactiva hasta que vuelva.
- Si nuestro precio bajó S/ 3 o más en las últimas 2 semanas, el producto muestra la etiqueta **"Bajó S/ X"**.

## Seguridad

- Los links de compra van cifrados (AES-256) y solo se abren con la contraseña del equipo.
- Las fotos de los productos se guardan en `img/` (no delatan en qué tienda compramos).
- La página tiene reglas de seguridad del navegador (CSP), no se puede mostrar dentro de otra página y el código va compactado.
- Activa la verificación en dos pasos en GitHub y en la cuenta de Google de la hoja.
- `LICENSE`: todos los derechos reservados.

## Modo equipo (LeoZypuc)

En la tienda: **Cuenta → Equipo Zypuc** → usuario `LeoZypuc` y la contraseña del equipo (no está escrita en ningún archivo).
Al entrar ves en cada producto **dónde comprarlo**, el vendedor, el link y tu ganancia, y aparece el botón **Panel** con:

- **Revisar comparaciones:** confirma los precios de Ripley.
- **Productos:** tabla con precio Zypuc, dónde comprar, otra tienda, ganancia y si el precio se pudo revisar.
- **Comprar pedido:** arma el carrito del cliente y verás qué comprar, dónde y cuánto ganas.
- **Agregar / editar:** formulario para un producto nuevo o para cambiar dónde se compra. Genera el `productos.json` completo para pegarlo en GitHub.
- **Reseñas:** publica las reseñas que los clientes te mandan por WhatsApp (`resenas.json`).
- **Estados de pedidos:** actualiza lo que el cliente ve en "Rastrea tu pedido" (`pedidos.json`).

Los links de compra van **cifrados** dentro de `productos.json` (campo `priv`). Así, aunque el repositorio sea público, nadie ve dónde compramos sin la contraseña.

### Secreto para el actualizador (una sola vez)

Para que GitHub pueda revisar los precios de compra, necesita la contraseña:
**Settings → Secrets and variables → Actions → New repository secret** → Name: `ZYPUC_CLAVE`, Secret: la contraseña del equipo → **Add secret**.
Sin ese secreto, la tienda sigue funcionando con el último precio guardado.

## Agregar un producto

Lo más fácil: entra como LeoZypuc → **Panel → Agregar / editar**, llena el formulario y sigue los 3 pasos que aparecen (copiar, abrir en GitHub, pegar y guardar).

- Usa el **link exacto del producto** (o una búsqueda de Falabella con el nombre exacto): así el actualizador puede leer el precio.
- Para la foto: abre el producto en la tienda, clic derecho sobre la foto → "Copiar dirección de imagen". Si la dejas vacía y el producto es de Falabella, el actualizador intenta traer la foto solo.
- La "tienda más cara" es opcional. Solo se muestra si de verdad es más cara que nuestro precio.

## Correr el actualizador a mano

En GitHub: pestaña **Actions** → **Actualizar precios** → **Run workflow**. En el resumen de la ejecución aparece cada precio leído (✅), los que no se pudieron leer (❌) y los descartados por raros (⚠️).

## Publicar la tienda

En GitHub: **Settings → Pages → Branch: main / (root) → Save**. En un par de minutos la tienda queda en
`https://djpacker17.github.io/Zypuc/`.

## Zypi y los secretos (spoiler para el equipo)

Zypi es la mascota de la tienda: sigue el mouse con los ojos, habla al tocarlo, se puede arrastrar, salta al añadir al carrito, se duerme si nadie lo toca y cambia de accesorio según la categoría.

| Secreto | Cómo se activa |
|---|---|
| Tema Sakura nocturno | Escribir `sakura` en el buscador |
| Tema Ciudad neón | Escribir `neon` |
| Tema Modo arcade | Teclas ↑ ↑ ↓ ↓ ← → ← → B A (o escribir `arcade`) |
| Tema Bosque de luciérnagas | Escribir `bosque` |
| Tema Tormenta eléctrica | Escribir `rayo` |
| Tema Atardecer retro | Tocar el logo de arriba 7 veces seguidas |
| Mejores amigos | Dejar el mouse quieto sobre Zypi (o mantenerlo presionado en el celular) |
| ¡Qué mareo! | Tocar a Zypi 10 veces seguidas |
| Búho nocturno | Entrar después de las 11 p. m. |
| Explorador | Visitar las 4 categorías |
| Coleccionista | Guardar 5 favoritos |
| Primer pedido | Enviar un pedido por WhatsApp |

Con los 12 logros, Zypi se vuelve dorado. Los logros se ven en el pie de página → **Logros secretos**.

## Historial de precios

El actualizador guarda un precio por día en `precios.json`. En la ficha de cada producto aparece un gráfico con nuestro precio y el de la otra tienda.
