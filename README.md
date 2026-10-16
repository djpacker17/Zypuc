# Zypuc · Tienda en línea

Tienda de Zypuc (tecnología, deporte, repostería y regalitos) con entrega en Pucallpa.
Los pedidos llegan por WhatsApp al **+51 951 434 075**.

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `index.html` | La tienda completa. Se abre con doble clic o desde GitHub Pages. |
| `productos.json` | **La lista de productos.** Aquí se agregan, quitan o editan productos. |
| `precios.json` | Lo escribe solo el actualizador de precios. No hace falta tocarlo. |
| `resenas.json` | Reseñas publicadas (se generan desde el Panel Zypuc). |
| `pedidos.json` | Estado de cada pedido para "Rastrea tu pedido" (se genera desde el Panel Zypuc). |
| `scripts/privado.py` | Cifra y descifra los links de compra. |
| `scripts/actualizar_precios.py` | Programa que visita los links de cada producto y lee el precio. |
| `.github/workflows/precios.yml` | Le dice a GitHub que corra el actualizador cada 6 horas. |
| `logo-claro.png`, `logo-oscuro.png` | Logo para fondo claro y para modo oscuro. |
| `manifest.webmanifest`, `sw.js`, `icon-*.png` | Permiten instalar la tienda como app en el celular y abrirla sin internet. |

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

## Minijuego Zypi Catch

Sección "Juego" de la tienda. Zypi atrapa productos con su canasta y esquiva etiquetas de precio inflado. Tiene combos, poderes (imán, escudo, x2, cámara lenta, +1 vida), niveles, sonido y récord guardado en cada dispositivo. Con 500 y 2000 puntos se desbloquean logros.

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
