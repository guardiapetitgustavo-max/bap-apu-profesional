"use strict";
/* BAP APU Profesional — versión web. Datos en el navegador (localStorage). */

const CLAVE = "bapapu.web.v1";
const TIPOS = ["Mano de Obra", "Material", "Equipo", "Subcontrato"];
const COLOR = { "Mano de Obra": "var(--mo)", Material: "var(--mat)", Equipo: "var(--eq)", Subcontrato: "var(--sub)" };
const $ = (s, r = document) => r.querySelector(s);
const r2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;
const r4 = (n) => Math.round((Number(n) + Number.EPSILON) * 10000) / 10000;
const sol = (n) => "S/ " + r2(n).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const chipTipo = (t) => `<span class="chip t-${t === "Mano de Obra" ? "MO" : t}">${t === "Mano de Obra" ? "M. Obra" : t}</span>`;

// ---------- Estado ----------
let S = cargar();

function cargar() {
  try {
    const d = JSON.parse(localStorage.getItem(CLAVE));
    if (d && d.recursos) return d;
  } catch (e) { /* almacenamiento no disponible */ }
  return semillaInicial();
}

function semillaInicial() {
  const recursos = window.SEMILLA.recursos.map((r) => ({ ...r }));
  const plantillas = window.SEMILLA.plantillas.map((p, i) => ({ id: "p" + i, ...plantillaANormal(p, recursos) }));
  const d = {
    empresa: { nombre: "Constructora Demo S.A.C.", ruc: "20123456789" },
    recursos, plantillas, presupuestos: [], sigRecurso: recursos.length + 1,
  };
  const pres = nuevoPresupuesto(d, "Vivienda Los Pinos — Acabados", "Cliente Demo");
  ["TABIQUE DE DRYWALL 2 CARAS RF", "FALSO CIELO RASO DE DRYWALL", "EMPASTADO Y PINTADO BLANCO"].forEach((n, i) => {
    const p = plantillas.find((x) => x.descripcion.startsWith(n));
    if (p) pres.partidas.push(partidaDesdePlantilla(p, [86.5, 120, 340][i]));
  });
  numerar(pres);
  return d;
}

function guardar() {
  try { localStorage.setItem(CLAVE, JSON.stringify(S)); } catch (e) { aviso("No se pudo guardar en este navegador"); }
}

// Las plantillas originales traen "HERRAMIENTAS MANUALES %mo": se convierte en porcentaje de mano de obra.
function plantillaANormal(p, recursos) {
  let herr = 0;
  const insumos = [];
  for (const i of p.insumos) {
    if (i.unidad.toLowerCase().includes("%")) { herr = i.cantidad; continue; }
    const rec = recursos.find((r) => r.nombre.toLowerCase() === i.nombre.toLowerCase() && r.unidad.toLowerCase() === i.unidad.toLowerCase());
    const porCuadrilla = i.cuadrilla > 0 && p.rendimiento > 0;
    insumos.push({
      recursoId: rec ? rec.id : null, nombre: i.nombre, unidad: i.unidad, tipo: TIPOS.includes(i.tipo) ? i.tipo : "Material",
      cuadrilla: porCuadrilla ? i.cuadrilla : null, cantidad: porCuadrilla ? null : i.cantidad, precio: rec ? null : i.precio,
    });
  }
  return { descripcion: p.nombre, unidad: p.unidad, rendimiento: p.rendimiento || 0, herr, insumos };
}

function nuevoPresupuesto(d, nombre, cliente) {
  const p = { id: nid(), nombre, cliente, fecha: new Date().toISOString().slice(0, 10), jornada: 8, gg: 10, util: 8, igv: 18, partidas: [] };
  d.presupuestos.push(p);
  return p;
}

function partidaDesdePlantilla(pl, metrado = 1) {
  return { id: nid(), codigo: "", descripcion: pl.descripcion, unidad: pl.unidad, metrado, rendimiento: pl.rendimiento, herr: pl.herr,
    insumos: pl.insumos.map((i) => ({ ...i })) };
}

function numerar(pres) { pres.partidas.forEach((p, i) => (p.codigo = "01." + String(i + 1).padStart(2, "0"))); }

// ---------- Cálculo ----------
const recurso = (id) => S.recursos.find((r) => r.id === id);
const precioInsumo = (i) => (i.precio != null ? i.precio : recurso(i.recursoId)?.precio ?? 0);

function calcInsumo(i, partida, jornada) {
  const cantidad = i.cuadrilla != null ? (partida.rendimiento > 0 ? r4((i.cuadrilla * jornada) / partida.rendimiento) : 0) : Number(i.cantidad) || 0;
  const precio = precioInsumo(i);
  return { cantidad, precio, parcial: r2(cantidad * precio) };
}

function calcPartida(p, jornada) {
  const filas = p.insumos.map((i) => ({ i, ...calcInsumo(i, p, jornada) }));
  const por = Object.fromEntries(TIPOS.map((t) => [t, 0]));
  filas.forEach((f) => (por[f.i.tipo] = r2(por[f.i.tipo] + f.parcial)));
  const herramientas = r2(((Number(p.herr) || 0) / 100) * por["Mano de Obra"]);
  const pu = r2(TIPOS.reduce((s, t) => s + por[t], 0) + herramientas);
  return { filas, por, herramientas, pu, parcial: r2(pu * (Number(p.metrado) || 0)) };
}

function calcPresupuesto(pres) {
  const partidas = pres.partidas.map((p) => ({ p, ...calcPartida(p, pres.jornada) }));
  const cd = r2(partidas.reduce((s, x) => s + x.parcial, 0));
  const gg = r2((cd * pres.gg) / 100), util = r2((cd * pres.util) / 100);
  const subtotal = r2(cd + gg + util), igv = r2((subtotal * pres.igv) / 100);
  return { partidas, cd, gg, util, subtotal, igv, total: r2(subtotal + igv) };
}

// ---------- Utilidades UI ----------
function aviso(t) { const e = $("#toast"); e.textContent = t; e.classList.add("ver"); clearTimeout(aviso.t); aviso.t = setTimeout(() => e.classList.remove("ver"), 2200); }
function descargar(nombre, contenido, tipo) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([contenido], { type: tipo })); a.download = nombre; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const csv = (filas) => "﻿" + filas.map((f) => f.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");

// ---------- Rutas ----------
const RUTAS = { inicio: vInicio, presupuestos: vPresupuestos, presupuesto: vPresupuesto, recursos: vRecursos, biblioteca: vBiblioteca, empresa: vEmpresa };
function render() {
  const [ruta, a, b] = location.hash.replace(/^#\//, "").split("/");
  const r = RUTAS[ruta] ? ruta : "inicio";
  document.querySelectorAll("#menu a").forEach((x) => x.classList.toggle("on", x.dataset.r === (r === "presupuesto" ? "presupuestos" : r)));
  $("#empresaTag").innerHTML = `<strong>${esc(S.empresa.nombre)}</strong><br>RUC ${esc(S.empresa.ruc)}`;
  $("#app").innerHTML = RUTAS[r](a, b);
  enlazar(r, a, b);
}
window.addEventListener("hashchange", render);

// ---------- Vistas ----------
function vInicio() {
  const tot = S.presupuestos.map((p) => ({ p, c: calcPresupuesto(p) }));
  const monto = tot.reduce((s, x) => s + x.c.total, 0);
  const por = Object.fromEntries(TIPOS.map((t) => [t, 0]));
  tot.forEach(({ p, c }) => c.partidas.forEach((x) => TIPOS.forEach((t) => (por[t] += x.por[t] * (Number(x.p.metrado) || 0)))));
  const suma = TIPOS.reduce((s, t) => s + por[t], 0) || 1;
  return `<h1>Panel</h1><p class="sub">Resumen de ${esc(S.empresa.nombre)}</p>
  <div class="kpis">
    <div class="kpi" style="--c:var(--teal)"><span>Presupuestos</span><b>${S.presupuestos.length}</b></div>
    <div class="kpi" style="--c:var(--gold)"><span>Monto total con IGV</span><b>${sol(monto)}</b></div>
    <div class="kpi" style="--c:var(--violet)"><span>Recursos en catálogo</span><b>${S.recursos.length}</b></div>
    <div class="kpi" style="--c:var(--coral)"><span>Plantillas APU</span><b>${S.plantillas.length}</b></div>
  </div>
  <div class="card"><h2>Composición del costo directo</h2>
    <div class="barra">${TIPOS.map((t) => `<i style="width:${(por[t] / suma) * 100}%;background:${COLOR[t]}"></i>`).join("")}</div>
    <div class="leyenda">${TIPOS.map((t) => `<span><b style="background:${COLOR[t]}"></b>${t}: ${sol(por[t])}</span>`).join("")}</div>
  </div>
  <div class="card"><div class="fila entre"><h2>Presupuestos recientes</h2><a class="btn pri" href="#/presupuestos">Ver todos</a></div>
    ${tablaPresupuestos(tot.slice(-5).reverse())}</div>`;
}

function tablaPresupuestos(lista) {
  if (!lista.length) return `<p class="vacio">Aún no hay presupuestos.</p>`;
  return `<table><tr><th>Presupuesto</th><th>Cliente</th><th>Fecha</th><th class="num">Partidas</th><th class="num">Total</th></tr>
  ${lista.map(({ p, c }) => `<tr class="clic" data-ir="#/presupuesto/${p.id}"><td><strong>${esc(p.nombre)}</strong></td><td>${esc(p.cliente)}</td><td>${p.fecha}</td><td class="num">${p.partidas.length}</td><td class="num">${sol(c.total)}</td></tr>`).join("")}</table>`;
}

function vPresupuestos() {
  return `<div class="fila entre"><div><h1>Presupuestos</h1><p class="sub">Cada partida tiene su análisis de precio unitario</p></div>
  <button class="btn pri" id="nuevoPres">+ Nuevo presupuesto</button></div>
  <div class="card">${tablaPresupuestos(S.presupuestos.map((p) => ({ p, c: calcPresupuesto(p) })))}</div>`;
}

function vPresupuesto(id, partidaId) {
  const pres = S.presupuestos.find((p) => p.id === id);
  if (!pres) return `<p class="vacio">Presupuesto no encontrado.</p>`;
  const c = calcPresupuesto(pres);
  const sel = c.partidas.find((x) => x.p.id === partidaId) || c.partidas[0];
  return `<div class="fila entre no-print"><a href="#/presupuestos" class="btn mini">← Presupuestos</a>
    <div class="fila"><button class="btn" id="csvPres">⬇ Excel (CSV)</button><button class="btn oro" onclick="print()">🖨 PDF</button>
    <button class="btn peligro" id="borrarPres">Eliminar</button></div></div>
  <h1 style="margin-top:14px"><input id="pNombre" value="${esc(pres.nombre)}" style="font-size:26px;font-weight:800;width:100%;background:transparent;border:0;padding:0"></h1>
  <div class="card no-print"><div class="campos">
    <label>Cliente<input id="pCliente" value="${esc(pres.cliente)}"></label>
    <label>Fecha<input type="date" id="pFecha" value="${pres.fecha}"></label>
    <label>Jornada (h)<input type="number" step="0.5" id="pJornada" value="${pres.jornada}"></label>
    <label>Gastos generales %<input type="number" step="0.1" id="pGG" value="${pres.gg}"></label>
    <label>Utilidad %<input type="number" step="0.1" id="pUtil" value="${pres.util}"></label>
    <label>IGV %<input type="number" step="0.1" id="pIGV" value="${pres.igv}"></label>
  </div></div>
  <div class="grid2">
    <div>
      <div class="card"><div class="fila entre"><h2>Partidas</h2>
        <div class="fila no-print"><select id="plantillaSel"><option value="">Agregar desde biblioteca…</option>${S.plantillas.map((p) => `<option value="${p.id}">${esc(p.descripcion)}</option>`).join("")}</select>
        <button class="btn mini" id="partidaVacia">+ Vacía</button></div></div>
        ${c.partidas.length ? `<table><tr><th>Ítem</th><th>Descripción</th><th>Und</th><th class="num">Metrado</th><th class="num">P.U.</th><th class="num">Parcial</th><th class="no-print"></th></tr>
        ${c.partidas.map((x) => `<tr class="clic ${sel && x.p.id === sel.p.id ? "sel" : ""}" data-partida="${x.p.id}"><td>${x.p.codigo}</td><td>${esc(x.p.descripcion)}</td><td>${esc(x.p.unidad)}</td>
          <td class="num"><input class="metrado" data-id="${x.p.id}" type="number" step="0.01" value="${x.p.metrado}" style="width:90px;text-align:right"></td>
          <td class="num">${r2(x.pu).toFixed(2)}</td><td class="num">${r2(x.parcial).toFixed(2)}</td><td class="no-print"><button class="btn mini peligro quitar" data-id="${x.p.id}">✕</button></td></tr>`).join("")}</table>` : `<p class="vacio">Agrega partidas desde la biblioteca.</p>`}
      </div>
      <div class="card"><h2>Resumen</h2><div class="resumen">
        <span>Costo directo</span><span class="num">${sol(c.cd)}</span>
        <span>Gastos generales (${pres.gg}%)</span><span class="num">${sol(c.gg)}</span>
        <span>Utilidad (${pres.util}%)</span><span class="num">${sol(c.util)}</span>
        <span>Subtotal</span><span class="num">${sol(c.subtotal)}</span>
        <span>IGV (${pres.igv}%)</span><span class="num">${sol(c.igv)}</span>
        <span class="tot">Total</span><span class="tot num">${sol(c.total)}</span></div></div>
    </div>
    <div>${sel ? editorAPU(pres, sel) : ""}</div>
  </div>`;
}

function editorAPU(pres, x) {
  const p = x.p;
  return `<div class="card"><h2>Análisis de precio unitario</h2>
  <div class="campos no-print">
    <label>Descripción<input class="apuCampo" data-k="descripcion" value="${esc(p.descripcion)}"></label>
    <label>Unidad<input class="apuCampo" data-k="unidad" value="${esc(p.unidad)}"></label>
    <label>Rendimiento (${esc(p.unidad)}/día)<input class="apuCampo" data-k="rendimiento" type="number" step="0.01" value="${p.rendimiento}"></label>
    <label>Herramientas % M.O.<input class="apuCampo" data-k="herr" type="number" step="0.1" value="${p.herr}"></label>
  </div>
  <div class="fila entre" style="margin:12px 0"><span>${esc(p.codigo)} · ${esc(p.descripcion)}</span><span class="pu">${sol(x.pu)} <small style="font-size:14px;color:var(--mute)">/ ${esc(p.unidad)}</small></span></div>
  <table><tr><th>Tipo</th><th>Insumo</th><th>Und</th><th class="num">Cuadrilla</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Parcial</th><th class="no-print"></th></tr>
  ${x.filas.map((f, k) => `<tr><td>${chipTipo(f.i.tipo)}</td><td>${esc(f.i.nombre)}${f.i.precio != null ? ' <small style="color:var(--gold)">(precio fijo)</small>' : ""}</td><td>${esc(f.i.unidad)}</td>
    <td class="num">${f.i.cuadrilla != null ? `<input class="insCampo" data-k="cuadrilla" data-n="${k}" type="number" step="0.01" value="${f.i.cuadrilla}" style="width:70px;text-align:right">` : "—"}</td>
    <td class="num">${f.i.cuadrilla != null ? f.cantidad.toFixed(4) : `<input class="insCampo" data-k="cantidad" data-n="${k}" type="number" step="0.0001" value="${f.i.cantidad}" style="width:85px;text-align:right">`}</td>
    <td class="num">${f.precio.toFixed(2)}</td><td class="num">${f.parcial.toFixed(2)}</td><td class="no-print"><button class="btn mini peligro insQuitar" data-n="${k}">✕</button></td></tr>`).join("")}
  <tr><td></td><td colspan="5">Herramientas manuales (${p.herr}% de M.O.)</td><td class="num">${x.herramientas.toFixed(2)}</td><td></td></tr></table>
  <div class="fila no-print" style="margin-top:12px"><select id="insRecurso" style="flex:1"><option value="">Agregar recurso del catálogo…</option>
    ${TIPOS.map((t) => `<optgroup label="${t}">${S.recursos.filter((r) => r.tipo === t).map((r) => `<option value="${r.id}">${esc(r.nombre)} — ${esc(r.unidad)} — ${r.precio.toFixed(2)}</option>`).join("")}</optgroup>`).join("")}</select></div>
  <div class="leyenda">${TIPOS.map((t) => `<span><b style="background:${COLOR[t]}"></b>${t}: ${sol(x.por[t])}</span>`).join("")}</div>
  <p class="sub" style="margin:10px 0 0;font-size:12px">Mano de obra y equipo por cuadrilla: cantidad = cuadrilla × ${pres.jornada} h ÷ rendimiento.</p></div>`;
}

function vRecursos() {
  return `<div class="fila entre"><div><h1>Recursos</h1><p class="sub">Al cambiar un precio se recalculan todos los APU enlazados</p></div>
  <button class="btn pri" id="nuevoRec">+ Nuevo recurso</button></div>
  <div class="card"><div class="fila" style="margin-bottom:10px"><input id="buscar" placeholder="Buscar por nombre o código…" style="flex:1"><select id="filtroTipo"><option value="">Todos los tipos</option>${TIPOS.map((t) => `<option>${t}</option>`).join("")}</select>
  <button class="btn" id="csvRec">⬇ CSV</button></div>
  <table id="tablaRec"><tr><th>Código</th><th>Recurso</th><th>Tipo</th><th>Und</th><th class="num">Precio (S/)</th></tr>
  ${S.recursos.map((r) => `<tr data-busca="${esc((r.codigo + " " + r.nombre).toLowerCase())}" data-tipo="${r.tipo}"><td>${esc(r.codigo)}</td><td>${esc(r.nombre)}</td><td>${chipTipo(r.tipo)}</td><td>${esc(r.unidad)}</td>
  <td class="num"><input class="precioRec" data-id="${r.id}" type="number" step="0.01" value="${r.precio}" style="width:110px;text-align:right"></td></tr>`).join("")}</table></div>`;
}

function vBiblioteca() {
  return `<h1>Biblioteca de APU</h1><p class="sub">Plantillas reales con rendimiento y cuadrilla, listas para cargar en un presupuesto</p>
  <div class="card"><table><tr><th>Partida</th><th>Und</th><th class="num">Rendimiento</th><th class="num">Insumos</th><th class="num">P.U. actual</th></tr>
  ${S.plantillas.map((p) => { const c = calcPartida({ ...p, metrado: 1 }, 8); return `<tr><td>${esc(p.descripcion)}</td><td>${esc(p.unidad)}</td><td class="num">${p.rendimiento}</td><td class="num">${p.insumos.length}</td><td class="num">${c.pu.toFixed(2)}</td></tr>`; }).join("")}</table></div>`;
}

function vEmpresa() {
  return `<h1>Empresa y datos</h1><p class="sub">Los datos se guardan en este navegador. Descarga un respaldo con frecuencia.</p>
  <div class="card"><h2>Empresa</h2><div class="campos"><label>Razón social<input id="eNombre" value="${esc(S.empresa.nombre)}"></label><label>RUC<input id="eRuc" value="${esc(S.empresa.ruc)}"></label></div></div>
  <div class="card"><h2>Respaldo</h2><div class="fila">
    <button class="btn pri" id="respaldo">⬇ Descargar respaldo (.json)</button>
    <label class="btn">⬆ Restaurar respaldo<input type="file" id="restaurar" accept=".json" hidden></label>
    <button class="btn peligro" id="reiniciar">Reiniciar datos de demostración</button></div></div>`;
}

// ---------- Eventos ----------
function enlazar(ruta, a, b) {
  document.querySelectorAll("[data-ir]").forEach((e) => (e.onclick = () => (location.hash = e.dataset.ir)));
  const on = (sel, ev, fn) => document.querySelectorAll(sel).forEach((e) => e.addEventListener(ev, fn));
  const cambio = (fn) => (e) => { fn(e); guardar(); render(); };

  if (ruta === "presupuestos") on("#nuevoPres", "click", () => { const p = nuevoPresupuesto(S, "Nuevo presupuesto", ""); guardar(); location.hash = "#/presupuesto/" + p.id; });

  if (ruta === "presupuesto") {
    const pres = S.presupuestos.find((p) => p.id === a);
    if (!pres) return;
    const partida = () => pres.partidas.find((p) => p.id === b) || pres.partidas[0];
    const campos = { pNombre: "nombre", pCliente: "cliente", pFecha: "fecha", pJornada: "jornada", pGG: "gg", pUtil: "util", pIGV: "igv" };
    Object.entries(campos).forEach(([idc, k]) => on("#" + idc, "change", cambio((e) => (pres[k] = e.target.type === "number" ? Number(e.target.value) || 0 : e.target.value))));
    on("[data-partida]", "click", (e) => { if (!e.target.closest("input,button")) location.hash = `#/presupuesto/${pres.id}/${e.currentTarget.dataset.partida}`; });
    on(".metrado", "change", cambio((e) => (pres.partidas.find((p) => p.id === e.target.dataset.id).metrado = Number(e.target.value) || 0)));
    on(".quitar", "click", cambio((e) => { pres.partidas = pres.partidas.filter((p) => p.id !== e.target.dataset.id); numerar(pres); }));
    on("#plantillaSel", "change", (e) => { const pl = S.plantillas.find((p) => p.id === e.target.value); if (!pl) return;
      const np = partidaDesdePlantilla(pl); pres.partidas.push(np); numerar(pres); guardar(); aviso("Partida agregada"); location.hash = `#/presupuesto/${pres.id}/${np.id}`; });
    on("#partidaVacia", "click", () => { const np = { id: nid(), codigo: "", descripcion: "Nueva partida", unidad: "m2", metrado: 1, rendimiento: 10, herr: 3, insumos: [] };
      pres.partidas.push(np); numerar(pres); guardar(); location.hash = `#/presupuesto/${pres.id}/${np.id}`; });
    on(".apuCampo", "change", cambio((e) => { const k = e.target.dataset.k; partida()[k] = e.target.type === "number" ? Number(e.target.value) || 0 : e.target.value; }));
    on(".insCampo", "change", cambio((e) => (partida().insumos[e.target.dataset.n][e.target.dataset.k] = Number(e.target.value) || 0)));
    on(".insQuitar", "click", cambio((e) => partida().insumos.splice(Number(e.target.dataset.n), 1)));
    on("#insRecurso", "change", cambio((e) => { const r = recurso(Number(e.target.value)); if (!r) return;
      const porCuadrilla = r.tipo === "Mano de Obra" || (r.tipo === "Equipo" && /^h/i.test(r.unidad));
      partida().insumos.push({ recursoId: r.id, nombre: r.nombre, unidad: r.unidad, tipo: r.tipo, cuadrilla: porCuadrilla ? 1 : null, cantidad: porCuadrilla ? null : 1, precio: null }); }));
    on("#borrarPres", "click", () => { if (!confirm("¿Eliminar este presupuesto?")) return; S.presupuestos = S.presupuestos.filter((p) => p !== pres); guardar(); location.hash = "#/presupuestos"; });
    on("#csvPres", "click", () => exportarPresupuesto(pres));
  }

  if (ruta === "recursos") {
    const filtrar = () => { const q = $("#buscar").value.toLowerCase(), t = $("#filtroTipo").value;
      document.querySelectorAll("#tablaRec tr[data-busca]").forEach((tr) => (tr.style.display = tr.dataset.busca.includes(q) && (!t || tr.dataset.tipo === t) ? "" : "none")); };
    on("#buscar", "input", filtrar); on("#filtroTipo", "change", filtrar);
    on(".precioRec", "change", (e) => { recurso(Number(e.target.dataset.id)).precio = Math.max(0, Number(e.target.value) || 0); guardar(); aviso("Precio actualizado; APU recalculados"); });
    on("#nuevoRec", "click", () => { const nombre = prompt("Nombre del recurso"); if (!nombre) return;
      const unidad = prompt("Unidad (ej. hh, bol, m3, und)", "und") || "und";
      const tipo = TIPOS[Math.max(0, Number(prompt("Tipo: 1 Mano de Obra · 2 Material · 3 Equipo · 4 Subcontrato", "2")) - 1)] || "Material";
      const precio = Number(prompt("Precio (S/)", "0")) || 0; const id = S.sigRecurso++;
      S.recursos.push({ id, codigo: "R" + String(id).padStart(3, "0"), nombre, unidad, tipo, precio }); guardar(); render(); aviso("Recurso creado"); });
    on("#csvRec", "click", () => descargar("recursos.csv", csv([["Código", "Recurso", "Tipo", "Unidad", "Precio"], ...S.recursos.map((r) => [r.codigo, r.nombre, r.tipo, r.unidad, r.precio])]), "text/csv"));
  }

  if (ruta === "empresa") {
    on("#eNombre", "change", cambio((e) => (S.empresa.nombre = e.target.value)));
    on("#eRuc", "change", cambio((e) => (S.empresa.ruc = e.target.value)));
    on("#respaldo", "click", () => descargar(`bap-apu-respaldo-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(S, null, 1), "application/json"));
    on("#restaurar", "change", async (e) => { try { const d = JSON.parse(await e.target.files[0].text()); if (!d.recursos || !d.presupuestos) throw 0; S = d; guardar(); render(); aviso("Respaldo restaurado"); }
      catch { alert("El archivo no es un respaldo válido de BAP APU."); } });
    on("#reiniciar", "click", () => { if (confirm("Se borrarán tus datos de este navegador. ¿Continuar?")) { S = semillaInicial(); guardar(); render(); } });
  }
}

function exportarPresupuesto(pres) {
  const c = calcPresupuesto(pres);
  const filas = [[S.empresa.nombre], [pres.nombre], ["Cliente", pres.cliente, "Fecha", pres.fecha], [], ["Ítem", "Descripción", "Und", "Metrado", "P.U.", "Parcial"]];
  c.partidas.forEach((x) => filas.push([x.p.codigo, x.p.descripcion, x.p.unidad, x.p.metrado, x.pu.toFixed(2), x.parcial.toFixed(2)]));
  filas.push([], ["", "Costo directo", "", "", "", c.cd.toFixed(2)], ["", `Gastos generales ${pres.gg}%`, "", "", "", c.gg.toFixed(2)],
    ["", `Utilidad ${pres.util}%`, "", "", "", c.util.toFixed(2)], ["", "Subtotal", "", "", "", c.subtotal.toFixed(2)],
    ["", `IGV ${pres.igv}%`, "", "", "", c.igv.toFixed(2)], ["", "TOTAL", "", "", "", c.total.toFixed(2)]);
  c.partidas.forEach((x) => { filas.push([], [`APU ${x.p.codigo}`, x.p.descripcion, `Rend. ${x.p.rendimiento} ${x.p.unidad}/día`], ["Tipo", "Insumo", "Und", "Cuadrilla", "Cantidad", "Precio", "Parcial"]);
    x.filas.forEach((f) => filas.push([f.i.tipo, f.i.nombre, f.i.unidad, f.i.cuadrilla ?? "", f.cantidad, f.precio.toFixed(2), f.parcial.toFixed(2)]));
    filas.push(["", `Herramientas ${x.p.herr}% MO`, "", "", "", "", x.herramientas.toFixed(2)], ["", "Precio unitario", "", "", "", "", x.pu.toFixed(2)]); });
  descargar(`${pres.nombre.replace(/[^\w\- ]+/g, "")}.csv`, csv(filas), "text/csv");
}

guardar();
render();
