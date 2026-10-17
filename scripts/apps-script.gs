/**
 * ZYPUC · CENTRO DE DATOS (Google Apps Script) · versión 2
 * ------------------------------------------------------------
 * Une la tienda con esta hoja de Google:
 *  - Pedidos: llegan solos cuando el cliente envía su pedido.
 *  - Reseñas: llegan solas; marcas "Aprobada" y aparecen en la tienda.
 *  - Rastreo: cambias "Estado" del pedido y el cliente lo ve al instante.
 *  - Avisos: clientes que quieren saber si un producto baja de precio.
 *  - Estadísticas: vistas, "al carrito" y compartidos por producto (sin datos personales).
 *  - Encargos: lo que los clientes piden y no está en la tienda ("Pídelo y te lo cotizamos").
 *  - Cupones: códigos de descuento que ustedes crean, activan y limitan desde la hoja.
 *  - Correo diario con el resumen y correo cuando un producto baja de precio.
 *
 * INSTALACIÓN (una sola vez):
 *  1) En la hoja: Extensiones → Apps Script. Borra lo que haya y pega TODO este código. Guarda (ícono de disquete).
 *  2) Arriba elige la función "configurar" y toca "Ejecutar". Acepta los permisos (Revisar permisos → tu cuenta →
 *     Configuración avanzada → Ir a Zypuc (no seguro) → Permitir). Es seguro: el script es tuyo.
 *  3) Implementar → Nueva implementación → tipo "Aplicación web".
 *     Ejecutar como: "Yo".  Quién tiene acceso: "Cualquier persona".  → Implementar.
 *  4) Copia la "URL de la aplicación web" (termina en /exec) y pásasela a Claude o pégala en el Panel Zypuc.
 */

const CONFIG = {
  CLAVE_EQUIPO: '__CLAVE__',            // la misma contraseña del modo equipo (LeoZypuc)
  CORREO: '',                            // vacío = tu propio correo de Google
  TIENDA: 'https://djpacker17.github.io/Zypuc/',
  ZONA: 'America/Lima'
};

const HOJAS = {
  'Pedidos': ['Fecha', 'Código', 'Estado', 'Nota para el cliente', 'Nombre', 'Teléfono', 'Entrega', 'Pago', 'Productos', 'Total (S/)', 'Actualizado', 'Cupón'],
  'Reseñas': ['Fecha', 'Nombre', 'Producto', 'Estrellas', 'Reseña', 'Aprobada'],
  'Avisos': ['Fecha', 'Producto (id)', 'Producto', 'Precio al pedir (S/)', 'WhatsApp', 'Nombre', 'Estado', 'Precio actual (S/)'],
  'Estadísticas': ['Fecha', 'Producto (id)', 'Producto', 'Vistas', 'Al carrito', 'Compartidos'],
  'Encargos': ['Fecha', 'Producto pedido', 'Link', 'Presupuesto (S/)', 'Nombre', 'WhatsApp', 'Estado', 'Respuesta'],
  'Cupones': ['Código', 'Tipo (% o S/)', 'Valor', 'Compra mínima (S/)', 'Vence (aaaa-mm-dd)', 'Activo (sí/no)', 'Usos', 'Máximo de usos', 'Nota']
};
const ESTADOS_ENCARGO = ['nuevo', 'cotizado', 'pedido', 'descartado'];
const ESTADOS = ['recibido', 'pagado', 'comprado', 'en-camino', 'entregado', 'cancelado'];

/* ===================== Instalación ===================== */
function configurar() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.setSpreadsheetTimeZone(CONFIG.ZONA);
  Object.keys(HOJAS).forEach(function (nombre) {
    const sh = ss.getSheetByName(nombre) || ss.insertSheet(nombre);
    const cab = HOJAS[nombre];
    sh.getRange(1, 1, 1, cab.length).setValues([cab]).setFontWeight('bold').setBackground('#1262d4').setFontColor('#ffffff');
    sh.setFrozenRows(1);
    sh.autoResizeColumns(1, cab.length);
  });
  const ped = ss.getSheetByName('Pedidos');
  ped.getRange('C2:C1000').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(ESTADOS, true).build());
  const res = ss.getSheetByName('Reseñas'), libre = ultimaFila(res) + 1; // quita casillas sueltas en filas vacías
  if (res.getMaxRows() >= libre) res.getRange(libre, 6, res.getMaxRows() - libre + 1, 1).removeCheckboxes().clearContent();
  ss.getSheetByName('Encargos').getRange('G2:G1000').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(ESTADOS_ENCARGO, true).build());
  const cup = ss.getSheetByName('Cupones');
  cup.getRange('F2:F200').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['sí', 'no'], true).build());
  cup.getRange('B2:B200').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['%', 'S/'], true).build());
  if (ultimaFila(cup) < 2) cup.getRange(2, 1, 1, 9).setValues([['BIENVENIDA', '%', 5, 30, '', 'no', 0, 100, 'Ejemplo: cambia "Activo" a "sí" para usarlo']]);
  const hoja1 = ss.getSheetByName('Hoja 1') || ss.getSheetByName('Sheet1');
  if (hoja1 && ss.getSheets().length > 1 && hoja1.getLastRow() === 0) ss.deleteSheet(hoja1);
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('resumenDiario').timeBased().everyDays(1).atHour(7).inTimezone(CONFIG.ZONA).create();
  ScriptApp.newTrigger('revisarAvisos').timeBased().everyHours(6).create();
  SpreadsheetApp.getUi && SpreadsheetApp.getActive().toast('¡Listo! Ahora implementa la aplicación web (paso 3).', 'Zypuc', 8);
}

/* ===================== Utilidades ===================== */
function json(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function hoja(n) { return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(n); }
function ahora() { return Utilities.formatDate(new Date(), CONFIG.ZONA, 'yyyy-MM-dd HH:mm'); }
function hoy() { return Utilities.formatDate(new Date(), CONFIG.ZONA, 'yyyy-MM-dd'); }
function txt(v, max) { return String(v == null ? '' : v).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max || 300); }
function esEquipo(k) { return k && String(k) === CONFIG.CLAVE_EQUIPO; }
function filas(n) {
  const v = hoja(n).getDataRange().getValues(); v.shift();
  v.forEach(function (r, i) { r.fila = i + 2; });
  return v.filter(function (r) { return r[0] !== '' && r[0] !== null; }); // ignora filas vacías
}
function ultimaFila(sh) { // última fila con fecha (ignora casillas vacías)
  const col = sh.getRange(1, 1, sh.getMaxRows(), 1).getValues();
  let ult = col.length; while (ult > 1 && (col[ult - 1][0] === '' || col[ult - 1][0] === null)) ult--;
  return ult;
}
function agregar(sh, fila) { const n = ultimaFila(sh) + 1; sh.getRange(n, 1, 1, fila.length).setValues([fila]); return n; }
function fecha(v) { return v instanceof Date ? Utilities.formatDate(v, CONFIG.ZONA, 'yyyy-MM-dd HH:mm') : String(v || ''); }
function correo() { return CONFIG.CORREO || Session.getEffectiveUser().getEmail(); }
function antiSpam(clave, max) {
  const c = CacheService.getScriptCache(); const n = Number(c.get(clave) || 0);
  if (n > (max || 30)) return false; c.put(clave, String(n + 1), 3600); return true;
}
function siActivo(v) { return v === true || /^s[ií]$/i.test(String(v).trim()); }

/* ===================== Cupones ===================== */
function validarCupon(codigo, total) {
  const code = txt(codigo, 30).toUpperCase();
  const no = function (m) { return { ok: true, valido: false, mensaje: m }; };
  if (!code) return no('Escribe un código.');
  if (!hoja('Cupones')) return no('Ese cupón no existe.');
  const f = filas('Cupones').filter(function (r) { return String(r[0]).trim().toUpperCase() === code; })[0];
  if (!f) return no('Ese cupón no existe.');
  if (!siActivo(f[5])) return no('Ese cupón no está activo.');
  if (f[4] && fecha(f[4]).slice(0, 10) < hoy()) return no('Ese cupón ya venció.');
  if (Number(f[7]) && Number(f[6]) >= Number(f[7])) return no('Ese cupón ya se agotó.');
  const minimo = Number(f[3]) || 0, t = Number(total) || 0;
  if (t < minimo) return no('Este cupón es para compras desde S/ ' + minimo.toFixed(2) + '.');
  const tipo = String(f[1]).indexOf('%') >= 0 ? '%' : 'S/', valor = Number(f[2]) || 0;
  let desc = tipo === '%' ? t * valor / 100 : valor;
  desc = Math.round(Math.min(desc, t) * 10) / 10;
  if (desc <= 0) return no('Ese cupón no tiene descuento.');
  return { ok: true, valido: true, code: code, tipo: tipo, valor: valor, desc: desc, fila: f.fila, mensaje: '¡Cupón aplicado! Ahorras S/ ' + desc.toFixed(2) + '.' };
}

/* ===================== Lectura (GET) ===================== */
function doGet(e) {
  const p = (e && e.parameter) || {};
  try {
    if (p.action === 'resenas') {
      const r = filas('Reseñas').filter(function (f) { return f[5] === true; }).reverse().slice(0, 80)
        .map(function (f) { return { date: fecha(f[0]).slice(0, 10), name: f[1], product: f[2], stars: Number(f[3]) || 5, text: f[4] }; });
      return json({ ok: true, resenas: r });
    }
    if (p.action === 'pedido') {
      const code = txt(p.code, 12).toUpperCase();
      const f = filas('Pedidos').filter(function (x) { return String(x[1]).toUpperCase() === code; }).pop();
      if (!f) return json({ ok: true, pedido: null });
      return json({ ok: true, pedido: { estado: f[2] || 'recibido', nota: f[3] || '', fecha: fecha(f[10] || f[0]).slice(0, 10), creado: fecha(f[0]).slice(0, 10) } });
    }
    if (p.action === 'cupon') {
      if (!antiSpam('cup', 300)) return json({ ok: true, valido: false, mensaje: 'Intenta en unos minutos.' });
      const v = validarCupon(p.code, p.total); delete v.fila; return json(v);
    }
    if (p.action === 'equipo') {
      if (!esEquipo(p.key)) return json({ ok: false, error: 'clave' });
      return json({ ok: true, datos: resumenEquipo() });
    }
    return json({ ok: true, zypuc: 'centro de datos activo', version: 2, hora: ahora() });
  } catch (err) { return json({ ok: false, error: String(err) }); }
}

function resumenEquipo() {
  const ped = filas('Pedidos').map(function (f, i) { return { fila: f.fila, fecha: fecha(f[0]), code: f[1], estado: f[2], nota: f[3], nombre: f[4], telefono: String(f[5]), entrega: f[6], pago: f[7], items: f[8], total: f[9] }; }).reverse().slice(0, 60);
  const res = filas('Reseñas').map(function (f, i) { return { fila: f.fila, fecha: fecha(f[0]), name: f[1], product: f[2], stars: f[3], text: f[4], aprobada: f[5] === true }; }).reverse().slice(0, 60);
  const avi = filas('Avisos').map(function (f, i) { return { fila: f.fila, fecha: fecha(f[0]), id: f[1], producto: f[2], precio: f[3], telefono: String(f[4]), nombre: f[5], estado: f[6], actual: f[7] }; }).reverse().slice(0, 80);
  const desde = Utilities.formatDate(new Date(Date.now() - 30 * 864e5), CONFIG.ZONA, 'yyyy-MM-dd');
  const agg = {};
  filas('Estadísticas').forEach(function (f) {
    if (fecha(f[0]).slice(0, 10) < desde) return;
    const k = f[1]; agg[k] = agg[k] || { id: k, producto: f[2], vistas: 0, carrito: 0, compartidos: 0 };
    agg[k].vistas += Number(f[3]) || 0; agg[k].carrito += Number(f[4]) || 0; agg[k].compartidos += Number(f[5]) || 0;
  });
  const stats = Object.keys(agg).map(function (k) { return agg[k]; }).sort(function (a, b) { return b.vistas - a.vistas; });
  const enc = hoja('Encargos') ? filas('Encargos').map(function (f) { return { fila: f.fila, fecha: fecha(f[0]), producto: f[1], link: f[2], presupuesto: f[3], nombre: f[4], telefono: String(f[5]), estado: f[6], respuesta: f[7] }; }).reverse().slice(0, 60) : [];
  return { pedidos: ped, resenas: res, avisos: avi, stats: stats, encargos: enc };
}

/* ===================== Escritura (POST) ===================== */
function doPost(e) {
  let d = {};
  try { d = JSON.parse(e.postData.contents || '{}'); } catch (err) { return json({ ok: false, error: 'json' }); }
  if (d.web) return json({ ok: true }); // trampa para robots
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    switch (d.action) {
      case 'pedido': return json(nuevoPedido(d));
      case 'resena': return json(nuevaResena(d));
      case 'aviso': return json(nuevoAviso(d));
      case 'eventos': return json(sumarEventos(d));
      case 'estado': return json(cambiarEstado(d));
      case 'aprobar': return json(aprobarResena(d));
      case 'encargo': return json(nuevoEncargo(d));
      case 'encargoEstado': return json(cambiarEncargo(d));
      default: return json({ ok: false, error: 'accion' });
    }
  } catch (err) { return json({ ok: false, error: String(err) }); }
  finally { lock.releaseLock(); }
}

function nuevoPedido(d) {
  const code = txt(d.code, 12).toUpperCase(); if (!/^Z[A-Z0-9]{4,8}$/.test(code)) return { ok: false, error: 'codigo' };
  if (!antiSpam('ped')) return { ok: false, error: 'limite' };
  const sh = hoja('Pedidos');
  if (filas('Pedidos').some(function (f) { return String(f[1]).toUpperCase() === code; })) return { ok: true, repetido: true };
  let cupon = '';
  if (d.cupon) {
    const v = validarCupon(d.cupon, Number(d.subtotal) || Number(d.total));
    if (v.valido) { const c = hoja('Cupones').getRange(v.fila, 7); c.setValue((Number(c.getValue()) || 0) + 1); cupon = v.code + ' (-S/ ' + v.desc.toFixed(2) + ')'; }
    else cupon = txt(d.cupon, 30) + ' (no válido: ' + v.mensaje + ')';
  }
  agregar(sh, [ahora(), code, 'recibido', '', txt(d.name, 80), "'" + txt(d.phone, 20), txt(d.address, 200), txt(d.payment, 20), txt(d.items, 900), Number(d.total) || 0, ahora(), cupon]);
  return { ok: true };
}
function nuevaResena(d) {
  const name = txt(d.name, 60), text = txt(d.text, 600), stars = Math.max(1, Math.min(5, Number(d.stars) || 0));
  if (!name || text.length < 12) return { ok: false, error: 'datos' };
  if (!antiSpam('res')) return { ok: false, error: 'limite' };
  const rf = agregar(hoja('Reseñas'), [ahora(), name, txt(d.product, 120), stars, text, false]);
  hoja('Reseñas').getRange(rf, 6).insertCheckboxes();
  return { ok: true };
}
function nuevoAviso(d) {
  const phone = txt(d.phone, 20).replace(/[^\d+]/g, ''); if (phone.length < 9) return { ok: false, error: 'telefono' };
  if (!antiSpam('avi')) return { ok: false, error: 'limite' };
  agregar(hoja('Avisos'), [ahora(), txt(d.id, 60), txt(d.product, 120), Number(d.price) || 0, "'" + phone, txt(d.name, 60), 'esperando', '']);
  return { ok: true };
}
function sumarEventos(d) {
  const ev = Array.isArray(d.events) ? d.events.slice(0, 60) : []; if (!ev.length) return { ok: true };
  if (!antiSpam('ev' + (d.s || '').slice(0, 8))) return { ok: true };
  const sh = hoja('Estadísticas'), dia = hoy(), datos = sh.getDataRange().getValues(), idx = {};
  for (let i = 1; i < datos.length; i++) if (fecha(datos[i][0]).slice(0, 10) === dia) idx[datos[i][1]] = i + 1;
  const col = { view: 4, cart: 5, share: 6 };
  ev.forEach(function (x) {
    const id = txt(x.id, 60), c = col[x.type]; if (!id || !c) return;
    let fila = idx[id];
    if (!fila) { fila = agregar(sh, [dia, id, txt(x.name, 120), 0, 0, 0]); idx[id] = fila; }
    const r = sh.getRange(fila, c); r.setValue((Number(r.getValue()) || 0) + 1);
  });
  return { ok: true };
}
function cambiarEstado(d) {
  if (!esEquipo(d.key)) return { ok: false, error: 'clave' };
  const code = txt(d.code, 12).toUpperCase(), estado = ESTADOS.indexOf(d.estado) >= 0 ? d.estado : null;
  if (!estado) return { ok: false, error: 'estado' };
  const sh = hoja('Pedidos'), v = sh.getDataRange().getValues();
  for (let i = v.length - 1; i >= 1; i--) if (String(v[i][1]).toUpperCase() === code) {
    sh.getRange(i + 1, 3, 1, 2).setValues([[estado, txt(d.nota, 200)]]); sh.getRange(i + 1, 11).setValue(ahora()); return { ok: true };
  }
  agregar(sh, [ahora(), code, estado, txt(d.nota, 200), '', '', '', '', '(creado desde el panel)', '', ahora()]);
  return { ok: true, creado: true };
}
function nuevoEncargo(d) {
  const prod = txt(d.producto, 200); if (prod.length < 3) return { ok: false, error: 'datos' };
  if (!antiSpam('enc')) return { ok: false, error: 'limite' };
  const sh = hoja('Encargos'); if (!sh) return { ok: false, error: 'falta la hoja Encargos (corre configurar)' };
  agregar(sh, [ahora(), prod, txt(d.link, 300), txt(d.presupuesto, 20), txt(d.name, 60), "'" + txt(d.phone, 20), 'nuevo', '']);
  return { ok: true };
}
function cambiarEncargo(d) {
  if (!esEquipo(d.key)) return { ok: false, error: 'clave' };
  const fila = Number(d.fila), estado = ESTADOS_ENCARGO.indexOf(d.estado) >= 0 ? d.estado : null;
  if (fila < 2 || !estado) return { ok: false };
  hoja('Encargos').getRange(fila, 7, 1, 2).setValues([[estado, txt(d.respuesta, 200)]]); return { ok: true };
}
function aprobarResena(d) {
  if (!esEquipo(d.key)) return { ok: false, error: 'clave' };
  const fila = Number(d.fila); if (fila < 2) return { ok: false };
  hoja('Reseñas').getRange(fila, 6).setValue(!!d.aprobada); return { ok: true };
}

/* ===================== Precios (para avisos y resumen) ===================== */
function datosTienda() {
  const get = function (f) { return JSON.parse(UrlFetchApp.fetch(CONFIG.TIENDA + f + '?t=' + Date.now(), { muteHttpExceptions: true }).getContentText()); };
  return { prod: get('productos.json'), precios: get('precios.json') };
}
function precioZypuc(p, cfg, live) {
  if (!p.buy || p.consult) return null;
  let compra = p.buy.price; const l = live && live.items && live.items[p.id] && live.items[p.id].buy;
  if (l && l.price > 0) compra = l.price;
  const x = (compra + (p.envio != null ? p.envio : cfg.envioPorUnidad)) * (1 + (p.comision != null ? p.comision : cfg.comision) / 100);
  const e = Math.floor(x); return x <= e + 0.9 ? e + 0.9 : e + 1.9;
}
function revisarAvisos() {
  const t = datosTienda(), cfg = t.prod.config, mapa = {};
  t.prod.productos.forEach(function (p) { mapa[p.id] = p; });
  const sh = hoja('Avisos'), v = sh.getDataRange().getValues(), bajaron = [];
  for (let i = 1; i < v.length; i++) {
    if (v[i][6] !== 'esperando') continue;
    const p = mapa[v[i][1]]; if (!p) continue;
    const actual = precioZypuc(p, cfg, t.precios); if (!actual) continue;
    sh.getRange(i + 1, 8).setValue(actual);
    if (actual < Number(v[i][3])) { sh.getRange(i + 1, 7).setValue('bajó'); bajaron.push({ fila: v[i], actual: actual, p: p }); }
  }
  if (!bajaron.length) return;
  const html = '<h2>📉 Bajaron de precio</h2><p>Avísales por WhatsApp:</p><ul>' + bajaron.map(function (b) {
    const tel = String(b.fila[4]).replace(/[^\d]/g, ''), num = tel.length === 9 ? '51' + tel : tel;
    const msg = encodeURIComponent('Hola' + (b.fila[5] ? ' ' + b.fila[5] : '') + ', te escribimos de Zypuc: ' + b.p.name + ' bajó a S/ ' + b.actual.toFixed(2) + ' (antes S/ ' + Number(b.fila[3]).toFixed(2) + '). ' + CONFIG.TIENDA);
    return '<li><b>' + b.p.name + '</b>: S/ ' + Number(b.fila[3]).toFixed(2) + ' → <b>S/ ' + b.actual.toFixed(2) + '</b> · <a href="https://wa.me/' + num + '?text=' + msg + '">Escribir a ' + (b.fila[5] || tel) + '</a></li>';
  }).join('') + '</ul>';
  MailApp.sendEmail({ to: correo(), subject: 'Zypuc · ' + bajaron.length + ' producto(s) bajaron de precio', htmlBody: html });
}

/* ===================== Correo diario ===================== */
function resumenDiario() {
  const ayer = Utilities.formatDate(new Date(Date.now() - 864e5), CONFIG.ZONA, 'yyyy-MM-dd HH:mm');
  const nuevos = filas('Pedidos').filter(function (f) { return fecha(f[0]) >= ayer; });
  const abiertos = filas('Pedidos').filter(function (f) { return ['entregado', 'cancelado'].indexOf(f[2]) < 0 && f[1]; });
  const pend = filas('Reseñas').filter(function (f) { return f[5] !== true && f[1]; });
  const encargos = hoja('Encargos') ? filas('Encargos').filter(function (f) { return fecha(f[0]) >= ayer; }) : [];
  let fallos = [], vencen = [];
  try {
    const t = datosTienda();
    t.prod.productos.forEach(function (p) {
      const l = t.precios.items && t.precios.items[p.id];
      if (p.buy && (!l || !l.buy || l.buy.ok === false)) fallos.push(p.name);
      if (p.ref && /ripley/i.test(p.ref.url || '')) {
        const dias = Math.floor((Date.now() - new Date(String(p.ref.checked).slice(0, 10) + 'T12:00:00').getTime()) / 864e5);
        if (dias >= 4) vencen.push(p.name + ' (' + (7 - dias > 0 ? 'se oculta en ' + (7 - dias) + ' días' : 'ya oculta') + ')');
      }
    });
  } catch (err) { fallos.push('No se pudo leer la tienda: ' + err); }
  const top = resumenEquipo().stats.slice(0, 5);
  if (!nuevos.length && !pend.length && !fallos.length && !vencen.length && !abiertos.length && !encargos.length) return;
  const li = function (a) { return a.length ? '<ul>' + a.map(function (x) { return '<li>' + x + '</li>'; }).join('') + '</ul>' : '<p>—</p>'; };
  const html = '<div style="font-family:Arial,sans-serif;max-width:620px">' +
    '<h2 style="color:#1262d4">Zypuc · resumen del día</h2>' +
    '<h3>🛍️ Pedidos nuevos (24 h): ' + nuevos.length + '</h3>' + li(nuevos.map(function (f) { return '<b>' + f[1] + '</b> · ' + f[4] + ' · S/ ' + f[9] + ' · ' + f[8]; })) +
    '<h3>📦 Pedidos abiertos: ' + abiertos.length + '</h3>' + li(abiertos.slice(-15).map(function (f) { return f[1] + ' → ' + f[2]; })) +
    '<h3>🔎 Encargos nuevos (24 h): ' + encargos.length + '</h3>' + li(encargos.map(function (f) { return '<b>' + f[1] + '</b>' + (f[3] ? ' · hasta S/ ' + f[3] : '') + (f[4] ? ' · ' + f[4] : ''); })) +
    '<h3>⭐ Reseñas por aprobar: ' + pend.length + '</h3>' + li(pend.slice(-10).map(function (f) { return f[1] + ' (' + f[3] + '★): ' + String(f[4]).slice(0, 80); })) +
    '<h3>⚠️ Precios que no se pudieron leer</h3>' + li(fallos) +
    '<h3>🔎 Comparaciones con Ripley por confirmar</h3>' + li(vencen) +
    '<h3>👀 Más vistos (30 días)</h3>' + li(top.map(function (s) { return s.producto + ': ' + s.vistas + ' vistas · ' + s.carrito + ' al carrito'; })) +
    '<p><a href="' + CONFIG.TIENDA + '">Abrir la tienda</a> · <a href="' + SpreadsheetApp.getActiveSpreadsheet().getUrl() + '">Abrir la hoja</a></p></div>';
  MailApp.sendEmail({ to: correo(), subject: 'Zypuc · ' + nuevos.length + ' pedido(s) nuevo(s) · ' + pend.length + ' reseña(s) por aprobar', htmlBody: html });
}
