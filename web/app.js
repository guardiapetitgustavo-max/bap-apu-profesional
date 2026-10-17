"use strict";
/* BAP APU Profesional — web con Supabase (login, empresas, roles, datos en la nube). */

const sb = window.supabase.createClient(window.BAP_CONFIG.supabaseUrl, window.BAP_CONFIG.supabaseKey);
const TIPOS = ["Mano de Obra", "Material", "Equipo", "Subcontrato"];
const ROLES = ["Administrador", "Gerente", "Ingeniero", "Presupuestador", "Consulta"];
const COLOR = { "Mano de Obra": "var(--mo)", Material: "var(--mat)", Equipo: "var(--eq)", Subcontrato: "var(--sub)" };
const $ = (s, r = document) => r.querySelector(s);
const r2 = (n) => Math.round((Number(n) + Number.EPSILON) * 100) / 100;
const r4 = (n) => Math.round((Number(n) + Number.EPSILON) * 10000) / 10000;
const sol = (n) => "S/ " + r2(n).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const f2 = (n) => r2(n).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const norm = (t) => String(t ?? "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").trim().toLowerCase();
const chipTipo = (t) => `<span class="chip t-${t === "Mano de Obra" ? "MO" : t}">${t === "Mano de Obra" ? "M. Obra" : t}</span>`;

// ---------- Estado ----------
const S = { sesion: null, perfil: null, empresa: null, recursos: [], clientes: [], proveedores: [], presupuestos: [], plantillas: [], usuarios: [], invitaciones: [], importacion: null };

function puede(accion) {
  const rol = S.perfil?.rol;
  if (rol === "Administrador") return true;
  if (rol === "Gerente") return accion !== "usuarios";
  if (rol === "Ingeniero") return ["presupuestos", "recursos"].includes(accion);
  if (rol === "Presupuestador") return accion === "presupuestos";
  return false;
}

async function q(promesa, mensajeOk) {
  const { data, error } = await promesa;
  if (error) { aviso("Error: " + error.message, true); throw error; }
  if (mensajeOk) aviso(mensajeOk);
  return data;
}

async function cargarTodo() {
  const uid = S.sesion.user.id;
  S.perfil = await q(sb.from("perfiles").select("*").eq("id", uid).maybeSingle());
  if (!S.perfil) return;
  const [empresa, recursos, clientes, proveedores, presupuestos] = await Promise.all([
    q(sb.from("empresas").select("*").eq("id", S.perfil.empresa_id).single()),
    q(sb.from("recursos").select("*").order("tipo").order("nombre")),
    q(sb.from("clientes").select("*").order("nombre")),
    q(sb.from("proveedores").select("*").order("nombre")),
    q(sb.from("presupuestos").select("*").order("created_at")),
  ]);
  Object.assign(S, { empresa, recursos: recursos.map(numRec), clientes, proveedores, presupuestos: presupuestos.map(numPres) });
  if (!S.recursos.length && puede("recursos")) await sembrarRecursos();
  S.plantillas = window.SEMILLA.plantillas.map((p, i) => ({ id: "p" + i, ...plantillaANormal(p) }));
  if (puede("usuarios")) await cargarUsuarios();
}
const numRec = (r) => ({ ...r, precio: Number(r.precio) });
const numPres = (p) => ({ ...p, jornada: Number(p.jornada), gg: Number(p.gg), util: Number(p.util), igv: Number(p.igv), partidas: p.partidas || [] });

async function sembrarRecursos() {
  const filas = window.SEMILLA.recursos.map((r) => ({ empresa_id: S.empresa.id, codigo: r.codigo, nombre: r.nombre, unidad: r.unidad, tipo: TIPOS.includes(r.tipo) ? r.tipo : "Material", precio: r.precio }));
  S.recursos = (await q(sb.from("recursos").insert(filas).select())).map(numRec);
}

async function cargarUsuarios() {
  [S.usuarios, S.invitaciones] = await Promise.all([
    q(sb.from("perfiles").select("*").order("created_at")),
    q(sb.from("invitaciones").select("*").eq("usada", false).order("created_at")),
  ]);
}

// Plantillas originales: "HERRAMIENTAS MANUALES %mo" pasa a porcentaje de mano de obra.
function plantillaANormal(p) {
  let herr = 0;
  const insumos = [];
  for (const i of p.insumos) {
    if (i.unidad.toLowerCase().includes("%")) { herr = i.cantidad; continue; }
    const rec = S.recursos.find((r) => norm(r.nombre) === norm(i.nombre) && norm(r.unidad) === norm(i.unidad));
    const porCuadrilla = i.cuadrilla > 0 && p.rendimiento > 0;
    insumos.push({ recursoId: rec ? rec.id : null, nombre: i.nombre, unidad: i.unidad, tipo: TIPOS.includes(i.tipo) ? i.tipo : "Material",
      cuadrilla: porCuadrilla ? i.cuadrilla : null, cantidad: porCuadrilla ? null : i.cantidad, precio: rec ? null : i.precio });
  }
  return { descripcion: p.nombre, unidad: p.unidad, rendimiento: p.rendimiento || 0, herr, insumos };
}

const partidaDesdePlantilla = (pl, metrado = 1) => ({ id: nid(), codigo: "", descripcion: pl.descripcion, unidad: pl.unidad, metrado, rendimiento: pl.rendimiento, herr: pl.herr, insumos: pl.insumos.map((i) => ({ ...i })) });
const numerar = (pres) => pres.partidas.forEach((p, i) => (p.codigo = "01." + String(i + 1).padStart(2, "0")));

// ---------- Cálculo ----------
const recurso = (id) => S.recursos.find((r) => r.id === id);
const precioInsumo = (i) => (i.precio != null ? Number(i.precio) : recurso(i.recursoId)?.precio ?? 0);
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

// ---------- Guardado ----------
const pendientes = new Map();
function guardarPres(pres) {
  clearTimeout(pendientes.get(pres.id));
  pendientes.set(pres.id, setTimeout(async () => {
    pendientes.delete(pres.id);
    const { nombre, fecha, cliente_id, jornada, gg, util, igv, partidas } = pres;
    await q(sb.from("presupuestos").update({ nombre, fecha, cliente_id, jornada, gg, util, igv, partidas, updated_at: new Date().toISOString() }).eq("id", pres.id), "Guardado");
  }, 500));
}

async function cambiarPrecio(rec, nuevo, origen, proveedorId = null) {
  const anterior = rec.precio;
  await q(sb.from("recursos").update({ precio: nuevo }).eq("id", rec.id));
  await q(sb.from("historial_precios").insert({ empresa_id: S.empresa.id, recurso_id: rec.id, precio_anterior: anterior, precio_nuevo: nuevo, origen, usuario_id: S.sesion.user.id }));
  rec.precio = nuevo;
}

// ---------- Utilidades UI ----------
function aviso(t, error) { const e = $("#toast"); e.textContent = t; e.className = "ver" + (error ? " error" : ""); clearTimeout(aviso.t); aviso.t = setTimeout(() => (e.className = ""), error ? 5000 : 1800); }
function descargar(nombre, contenido, tipo) {
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([contenido], { type: tipo })); a.download = nombre; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const csv = (filas) => "\ufeff" + filas.map((f) => f.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(";")).join("\r\n");
const sololectura = (accion) => (puede(accion) ? "" : "disabled");

// ---------- Acceso (login / registro) ----------
function vAcceso(modo = "entrar") {
  $("#sidebar").hidden = true;
  const reg = modo === "registro";
  $("#app").innerHTML = `<div class="acceso"><div class="acceso-card">
    <img src="assets/bap_logo_principal.png" alt="BAP" class="acceso-logo">
    <h1>${reg ? "Crea la cuenta de tu empresa" : modo === "olvido" ? "Recuperar contraseña" : "Ingresa a BAP APU"}</h1>
    <p class="sub">${reg ? "Serás el administrador. Luego podrás invitar a tu equipo." : "Análisis de precios unitarios y presupuestos de obra"}</p>
    <form id="formAcceso" class="campos-col">
      ${reg ? `<label>Razón social<input name="empresa" required placeholder="Constructora ABC S.A.C."></label>
      <label>RUC<input name="ruc" pattern="\\d{11}" placeholder="20123456789"></label>
      <label>Tu nombre<input name="nombre" required></label>` : ""}
      <label>Correo<input name="email" type="email" required autocomplete="email"></label>
      ${modo !== "olvido" ? `<label>Contraseña<input name="password" type="password" required minlength="8" autocomplete="${reg ? "new-password" : "current-password"}"></label>` : ""}
      <button class="btn pri" type="submit">${reg ? "Crear cuenta" : modo === "olvido" ? "Enviar enlace" : "Ingresar"}</button>
    </form>
    <div class="acceso-links">
      ${modo !== "entrar" ? `<a href="#" data-modo="entrar">Ya tengo cuenta</a>` : `<a href="#" data-modo="registro">Crear cuenta de empresa</a><a href="#" data-modo="olvido">Olvidé mi contraseña</a>`}
    </div>
    <p class="nota">¿Te invitaron? Usa "Crear cuenta" con el mismo correo de la invitación y entrarás a la empresa que te invitó.</p>
  </div></div>`;
  document.querySelectorAll("[data-modo]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); vAcceso(a.dataset.modo); }));
  $("#formAcceso").onsubmit = async (e) => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.target));
    const boton = e.target.querySelector("button"); boton.disabled = true;
    try {
      if (reg) {
        const { data, error } = await sb.auth.signUp({ email: d.email, password: d.password, options: { data: { empresa: d.empresa, ruc: d.ruc, nombre: d.nombre }, emailRedirectTo: location.origin + "/app" } });
        if (error) throw error;
        if (!data.session) { $("#app").querySelector(".acceso-card").innerHTML = `<h1>Revisa tu correo</h1><p class="sub">Te enviamos un enlace a <strong>${esc(d.email)}</strong> para confirmar la cuenta. Luego vuelve aquí e ingresa.</p><button class="btn pri" onclick="location.reload()">Volver</button>`; return; }
      } else if (modo === "olvido") {
        const { error } = await sb.auth.resetPasswordForEmail(d.email, { redirectTo: location.origin + "/app" });
        if (error) throw error;
        aviso("Te enviamos un enlace para cambiar la contraseña"); vAcceso("entrar"); return;
      } else {
        const { error } = await sb.auth.signInWithPassword({ email: d.email, password: d.password });
        if (error) throw error;
      }
    } catch (err) {
      aviso(err.message === "Invalid login credentials" ? "Correo o contraseña incorrectos" : err.message, true);
      boton.disabled = false;
    }
  };
}

function vNuevaClave() {
  $("#sidebar").hidden = true;
  $("#app").innerHTML = `<div class="acceso"><div class="acceso-card"><h1>Nueva contraseña</h1>
  <form id="formClave" class="campos-col"><label>Contraseña nueva<input name="p" type="password" minlength="8" required autocomplete="new-password"></label><button class="btn pri">Guardar</button></form></div></div>`;
  $("#formClave").onsubmit = async (e) => { e.preventDefault();
    const { error } = await sb.auth.updateUser({ password: new FormData(e.target).get("p") });
    if (error) return aviso(error.message, true);
    aviso("Contraseña actualizada"); location.hash = "#/inicio"; arrancar(); };
}

// ---------- Rutas ----------
const MENU = [
  ["inicio", "▦ Panel", null], ["presupuestos", "◧ Presupuestos", null], ["recursos", "◈ Recursos", null],
  ["importar", "⇪ Importar precios", "recursos"], ["terceros", "☰ Clientes y proveedores", null],
  ["biblioteca", "❖ Biblioteca APU", null], ["usuarios", "◉ Usuarios", "usuarios"], ["empresa", "⚙ Empresa", null],
];
const RUTAS = { inicio: vInicio, presupuestos: vPresupuestos, presupuesto: vPresupuesto, recursos: vRecursos, recurso: vRecurso, importar: vImportar,
  terceros: vTerceros, biblioteca: vBiblioteca, usuarios: vUsuarios, empresa: vEmpresa, imprimir: vImprimir };

function render() {
  if (!S.perfil) return;
  const [ruta, a, b] = location.hash.replace(/^#\//, "").split("/");
  const r = RUTAS[ruta] ? ruta : "inicio";
  const impresion = r === "imprimir";
  document.body.classList.toggle("modo-impresion", impresion);
  $("#sidebar").hidden = impresion;
  $("#menu").innerHTML = MENU.filter(([, , p]) => !p || puede(p)).map(([k, t]) => `<a href="#/${k}" class="${k === ({ presupuesto: "presupuestos", recurso: "recursos" }[r] || r) ? "on" : ""}">${t}</a>`).join("");
  $("#empresaTag").innerHTML = `<strong>${esc(S.empresa.razon_social)}</strong><br>RUC ${esc(S.empresa.ruc || "—")}<br>${esc(S.perfil.nombre)} · ${S.perfil.rol}<br><a href="#" id="salir">Cerrar sesión</a>`;
  $("#salir").onclick = async (e) => { e.preventDefault(); await sb.auth.signOut(); };
  $("#app").innerHTML = RUTAS[r](a, b);
  enlazar(r, a, b);
}
window.addEventListener("hashchange", render);

// ---------- Vistas ----------
function vInicio() {
  const tot = S.presupuestos.map((p) => ({ p, c: calcPresupuesto(p) }));
  const monto = tot.reduce((s, x) => s + x.c.total, 0);
  const por = Object.fromEntries(TIPOS.map((t) => [t, 0]));
  tot.forEach(({ c }) => c.partidas.forEach((x) => TIPOS.forEach((t) => (por[t] += x.por[t] * (Number(x.p.metrado) || 0)))));
  const suma = TIPOS.reduce((s, t) => s + por[t], 0) || 1;
  return `<h1>Hola, ${esc(S.perfil.nombre)}</h1><p class="sub">${esc(S.empresa.razon_social)} · ${S.perfil.rol}</p>
  <div class="kpis">
    <div class="kpi" style="--c:var(--teal)"><span>Presupuestos</span><b>${S.presupuestos.length}</b></div>
    <div class="kpi" style="--c:var(--gold)"><span>Monto total con IGV</span><b>${sol(monto)}</b></div>
    <div class="kpi" style="--c:var(--violet)"><span>Recursos</span><b>${S.recursos.length}</b></div>
    <div class="kpi" style="--c:var(--coral)"><span>Clientes</span><b>${S.clientes.length}</b></div>
  </div>
  <div class="card"><h2>Composición del costo directo</h2>
    <div class="barra">${TIPOS.map((t) => `<i style="width:${(por[t] / suma) * 100}%;background:${COLOR[t]}"></i>`).join("")}</div>
    <div class="leyenda">${TIPOS.map((t) => `<span><b style="background:${COLOR[t]}"></b>${t}: ${sol(por[t])}</span>`).join("")}</div></div>
  <div class="card"><div class="fila entre"><h2>Presupuestos recientes</h2><a class="btn pri" href="#/presupuestos">Ver todos</a></div>${tablaPresupuestos(tot.slice(-5).reverse())}</div>`;
}

const nombreCliente = (id) => S.clientes.find((c) => c.id === id)?.nombre || "—";
function tablaPresupuestos(lista) {
  if (!lista.length) return `<p class="vacio">Aún no hay presupuestos.</p>`;
  return `<table><tr><th>Presupuesto</th><th>Cliente</th><th>Fecha</th><th class="num">Partidas</th><th class="num">Total</th></tr>
  ${lista.map(({ p, c }) => `<tr class="clic" data-ir="#/presupuesto/${p.id}"><td><strong>${esc(p.nombre)}</strong></td><td>${esc(nombreCliente(p.cliente_id))}</td><td>${p.fecha}</td><td class="num">${p.partidas.length}</td><td class="num">${sol(c.total)}</td></tr>`).join("")}</table>`;
}

function vPresupuestos() {
  return `<div class="fila entre"><div><h1>Presupuestos</h1><p class="sub">Cada partida tiene su análisis de precio unitario</p></div>
  ${puede("presupuestos") ? `<button class="btn pri" id="nuevoPres">+ Nuevo presupuesto</button>` : ""}</div>
  <div class="card">${tablaPresupuestos(S.presupuestos.map((p) => ({ p, c: calcPresupuesto(p) })))}</div>`;
}

function vPresupuesto(id, partidaId) {
  const pres = S.presupuestos.find((p) => p.id === id);
  if (!pres) return `<p class="vacio">Presupuesto no encontrado.</p>`;
  const c = calcPresupuesto(pres);
  const sel = c.partidas.find((x) => x.p.id === partidaId) || c.partidas[0];
  const ro = sololectura("presupuestos");
  return `<div class="fila entre"><a href="#/presupuestos" class="btn mini">← Presupuestos</a>
    <div class="fila"><button class="btn" id="csvPres">⬇ Excel (CSV)</button><a class="btn oro" href="#/imprimir/${pres.id}">🖨 PDF profesional</a>
    ${puede("presupuestos") ? `<button class="btn peligro" id="borrarPres">Eliminar</button>` : ""}</div></div>
  <h1 style="margin-top:14px"><input id="pNombre" value="${esc(pres.nombre)}" ${ro} class="titulo-input"></h1>
  <div class="card"><div class="campos">
    <label>Cliente<select id="pCliente" ${ro}><option value="">— Sin cliente —</option>${S.clientes.map((cl) => `<option value="${cl.id}" ${cl.id === pres.cliente_id ? "selected" : ""}>${esc(cl.nombre)}</option>`).join("")}</select></label>
    <label>Fecha<input type="date" id="pFecha" value="${pres.fecha}" ${ro}></label>
    <label>Jornada (h)<input type="number" step="0.5" id="pJornada" value="${pres.jornada}" ${ro}></label>
    <label>Gastos generales %<input type="number" step="0.1" id="pGG" value="${pres.gg}" ${ro}></label>
    <label>Utilidad %<input type="number" step="0.1" id="pUtil" value="${pres.util}" ${ro}></label>
    <label>IGV %<input type="number" step="0.1" id="pIGV" value="${pres.igv}" ${ro}></label></div></div>
  <div class="grid2"><div>
    <div class="card"><div class="fila entre"><h2>Partidas</h2>
      ${puede("presupuestos") ? `<div class="fila"><select id="plantillaSel"><option value="">Agregar desde biblioteca…</option>${S.plantillas.map((p) => `<option value="${p.id}">${esc(p.descripcion)}</option>`).join("")}</select>
      <button class="btn mini" id="partidaVacia">+ Vacía</button></div>` : ""}</div>
      ${c.partidas.length ? `<table><tr><th>Ítem</th><th>Descripción</th><th>Und</th><th class="num">Metrado</th><th class="num">P.U.</th><th class="num">Parcial</th><th></th></tr>
      ${c.partidas.map((x) => `<tr class="clic ${sel && x.p.id === sel.p.id ? "sel" : ""}" data-partida="${x.p.id}"><td>${x.p.codigo}</td><td>${esc(x.p.descripcion)}</td><td>${esc(x.p.unidad)}</td>
        <td class="num"><input class="metrado" data-id="${x.p.id}" type="number" step="0.01" value="${x.p.metrado}" ${ro} style="width:90px;text-align:right"></td>
        <td class="num">${f2(x.pu)}</td><td class="num">${f2(x.parcial)}</td><td>${puede("presupuestos") ? `<button class="btn mini peligro quitar" data-id="${x.p.id}">✕</button>` : ""}</td></tr>`).join("")}</table>` : `<p class="vacio">Agrega partidas desde la biblioteca.</p>`}</div>
    <div class="card"><h2>Resumen</h2><div class="resumen">
      <span>Costo directo</span><span class="num">${sol(c.cd)}</span><span>Gastos generales (${pres.gg}%)</span><span class="num">${sol(c.gg)}</span>
      <span>Utilidad (${pres.util}%)</span><span class="num">${sol(c.util)}</span><span>Subtotal</span><span class="num">${sol(c.subtotal)}</span>
      <span>IGV (${pres.igv}%)</span><span class="num">${sol(c.igv)}</span><span class="tot">Total</span><span class="tot num">${sol(c.total)}</span></div></div>
  </div><div>${sel ? editorAPU(pres, sel, ro) : ""}</div></div>`;
}

function editorAPU(pres, x, ro) {
  const p = x.p;
  return `<div class="card"><h2>Análisis de precio unitario</h2>
  <div class="campos">
    <label>Descripción<input class="apuCampo" data-k="descripcion" value="${esc(p.descripcion)}" ${ro}></label>
    <label>Unidad<input class="apuCampo" data-k="unidad" value="${esc(p.unidad)}" ${ro}></label>
    <label>Rendimiento (${esc(p.unidad)}/día)<input class="apuCampo" data-k="rendimiento" type="number" step="0.01" value="${p.rendimiento}" ${ro}></label>
    <label>Herramientas % M.O.<input class="apuCampo" data-k="herr" type="number" step="0.1" value="${p.herr}" ${ro}></label></div>
  <div class="fila entre" style="margin:12px 0"><span>${esc(p.codigo)} · ${esc(p.descripcion)}</span><span class="pu">${sol(x.pu)} <small>/ ${esc(p.unidad)}</small></span></div>
  <table><tr><th>Tipo</th><th>Insumo</th><th>Und</th><th class="num">Cuadrilla</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Parcial</th><th></th></tr>
  ${x.filas.map((f, k) => `<tr><td>${chipTipo(f.i.tipo)}</td><td>${esc(f.i.nombre)}${f.i.precio != null ? ' <small class="oro">(precio fijo)</small>' : ""}</td><td>${esc(f.i.unidad)}</td>
    <td class="num">${f.i.cuadrilla != null ? `<input class="insCampo" data-k="cuadrilla" data-n="${k}" type="number" step="0.01" value="${f.i.cuadrilla}" ${ro} style="width:70px;text-align:right">` : "—"}</td>
    <td class="num">${f.i.cuadrilla != null ? f.cantidad.toFixed(4) : `<input class="insCampo" data-k="cantidad" data-n="${k}" type="number" step="0.0001" value="${f.i.cantidad}" ${ro} style="width:85px;text-align:right">`}</td>
    <td class="num">${f2(f.precio)}</td><td class="num">${f2(f.parcial)}</td><td>${puede("presupuestos") ? `<button class="btn mini peligro insQuitar" data-n="${k}">✕</button>` : ""}</td></tr>`).join("")}
  <tr><td></td><td colspan="5">Herramientas manuales (${p.herr}% de M.O.)</td><td class="num">${f2(x.herramientas)}</td><td></td></tr></table>
  ${puede("presupuestos") ? `<div class="fila" style="margin-top:12px"><select id="insRecurso" style="flex:1"><option value="">Agregar recurso del catálogo…</option>
    ${TIPOS.map((t) => `<optgroup label="${t}">${S.recursos.filter((r) => r.tipo === t).map((r) => `<option value="${r.id}">${esc(r.nombre)} — ${esc(r.unidad)} — ${f2(r.precio)}</option>`).join("")}</optgroup>`).join("")}</select></div>` : ""}
  <div class="leyenda">${TIPOS.map((t) => `<span><b style="background:${COLOR[t]}"></b>${t}: ${sol(x.por[t])}</span>`).join("")}</div>
  <p class="sub nota-calc">Mano de obra y equipo por cuadrilla: cantidad = cuadrilla × ${pres.jornada} h ÷ rendimiento.</p></div>`;
}

function vRecursos() {
  return `<div class="fila entre"><div><h1>Recursos</h1><p class="sub">Al cambiar un precio se recalculan todos los APU enlazados y queda en el historial</p></div>
  <div class="fila">${puede("recursos") ? `<a class="btn" href="#/importar">⇪ Importar Excel</a><button class="btn pri" id="nuevoRec">+ Nuevo recurso</button>` : ""}</div></div>
  <div class="card"><div class="fila" style="margin-bottom:10px"><input id="buscar" placeholder="Buscar por nombre o código…" style="flex:1"><select id="filtroTipo"><option value="">Todos los tipos</option>${TIPOS.map((t) => `<option>${t}</option>`).join("")}</select>
  <button class="btn" id="csvRec">⬇ CSV</button></div>
  <table id="tablaRec"><tr><th>Código</th><th>Recurso</th><th>Tipo</th><th>Und</th><th class="num">Precio (S/)</th><th></th></tr>
  ${S.recursos.map((r) => `<tr data-busca="${esc(norm(r.codigo + " " + r.nombre))}" data-tipo="${r.tipo}"><td>${esc(r.codigo)}</td><td>${esc(r.nombre)}</td><td>${chipTipo(r.tipo)}</td><td>${esc(r.unidad)}</td>
  <td class="num"><input class="precioRec" data-id="${r.id}" type="number" step="0.01" value="${r.precio}" ${sololectura("recursos")} style="width:110px;text-align:right"></td>
  <td><a class="btn mini" href="#/recurso/${r.id}">Ofertas</a></td></tr>`).join("")}</table></div>`;
}

function vRecurso(id) {
  const r = recurso(Number(id));
  if (!r) return `<p class="vacio">Recurso no encontrado.</p>`;
  setTimeout(async () => {
    const [ofertas, historial] = await Promise.all([
      q(sb.from("ofertas").select("*, proveedores(nombre)").eq("recurso_id", r.id).order("precio")),
      q(sb.from("historial_precios").select("*").eq("recurso_id", r.id).order("created_at", { ascending: false }).limit(30)),
    ]);
    $("#ofertas").innerHTML = ofertas.length ? `<table><tr><th>Proveedor</th><th>Marca</th><th>Fecha</th><th class="num">Precio</th><th></th></tr>
      ${ofertas.map((o, k) => `<tr class="${k === 0 ? "sel" : ""}"><td>${esc(o.proveedores?.nombre || "—")}${k === 0 ? ' <span class="chip t-MO">Mejor precio</span>' : ""}</td><td>${esc(o.marca || "")}</td><td>${o.fecha}</td><td class="num">${f2(o.precio)}</td>
      <td>${puede("recursos") ? `<button class="btn mini aplicarOferta" data-precio="${o.precio}" data-prov="${o.proveedor_id ?? ""}">Usar este precio</button>` : ""}</td></tr>`).join("")}</table>` : `<p class="vacio">Sin ofertas. Impórtalas desde Excel.</p>`;
    $("#historial").innerHTML = historial.length ? `<table><tr><th>Fecha</th><th>Origen</th><th class="num">Anterior</th><th class="num">Nuevo</th></tr>
      ${historial.map((h) => `<tr><td>${new Date(h.created_at).toLocaleString("es-PE")}</td><td>${esc(h.origen)}</td><td class="num">${h.precio_anterior == null ? "—" : f2(h.precio_anterior)}</td><td class="num">${f2(h.precio_nuevo)}</td></tr>`).join("")}</table>` : `<p class="vacio">Sin cambios de precio.</p>`;
    document.querySelectorAll(".aplicarOferta").forEach((b) => (b.onclick = async () => { await cambiarPrecio(r, Number(b.dataset.precio), "OFERTA PROVEEDOR"); aviso("Precio actualizado"); render(); }));
  });
  return `<a href="#/recursos" class="btn mini">← Recursos</a><h1 style="margin-top:14px">${esc(r.nombre)}</h1>
  <p class="sub">${chipTipo(r.tipo)} · ${esc(r.unidad)} · Precio vigente <strong>${sol(r.precio)}</strong></p>
  <div class="grid2"><div class="card"><h2>Comparación de ofertas</h2><div id="ofertas"><p class="vacio">Cargando…</p></div></div>
  <div class="card"><h2>Historial de precios</h2><div id="historial"><p class="vacio">Cargando…</p></div></div></div>`;
}

function vImportar() {
  const imp = S.importacion;
  return `<h1>Importar precios desde Excel</h1><p class="sub">Crea recursos, registra ofertas de proveedores y actualiza precios con historial</p>
  <div class="card"><h2>1. Prepara tu archivo</h2>
    <p>Columnas: <code>Codigo</code>, <code>Nombre</code>, <code>Unidad</code>, <code>Tipo</code> (Mano de Obra / Material / Equipo / Subcontrato), <code>Precio</code>, <code>Proveedor</code>, <code>RUC_Proveedor</code>, <code>Marca</code>, <code>Actualizar_Precio</code> (SI/NO).</p>
    <div class="fila"><button class="btn" id="plantillaXlsx">⬇ Descargar plantilla Excel</button>
    <label class="btn pri">⬆ Elegir archivo Excel o CSV<input type="file" id="archivoImp" accept=".xlsx,.xls,.csv" hidden></label></div></div>
  ${imp ? `<div class="card"><h2>2. Revisa antes de confirmar</h2>
    <p>${imp.filas.filter((f) => f.ok).length} filas válidas · ${imp.filas.filter((f) => !f.ok).length} con errores (se omiten)</p>
    <table><tr><th>Fila</th><th>Acción</th><th>Recurso</th><th>Und</th><th>Tipo</th><th class="num">Precio</th><th>Proveedor</th><th>Observación</th></tr>
    ${imp.filas.map((f) => `<tr class="${f.ok ? "" : "error-fila"}"><td>${f.n}</td><td>${f.ok ? `<span class="chip t-${f.accion === "CREAR" ? "Material" : f.accion === "ACTUALIZAR" ? "MO" : "Equipo"}">${f.accion}</span>` : "—"}</td><td>${esc(f.nombre)}</td><td>${esc(f.unidad)}</td><td>${esc(f.tipo || "")}</td><td class="num">${f.precio != null ? f2(f.precio) : ""}</td><td>${esc(f.proveedor)}</td><td>${esc(f.error || "")}</td></tr>`).join("")}</table>
    <div class="fila" style="margin-top:12px"><button class="btn pri" id="confirmarImp">Confirmar importación</button><button class="btn" id="cancelarImp">Cancelar</button></div></div>` : ""}`;
}

const TIPO_ALIAS = { "mano de obra": "Mano de Obra", "mano obra": "Mano de Obra", mo: "Mano de Obra", material: "Material", materiales: "Material", equipo: "Equipo", equipos: "Equipo", herramienta: "Equipo", subcontrato: "Subcontrato" };
function analizarImportacion(filasCrudas) {
  const col = (o, ...nombres) => { for (const k of Object.keys(o)) if (nombres.includes(norm(k).replace(/[^a-z0-9]/g, ""))) return o[k]; return ""; };
  const nuevos = new Set();
  return filasCrudas.map((o, idx) => {
    const f = { n: idx + 2, codigo: String(col(o, "codigo", "codigorecurso", "sku")).trim().toUpperCase(), nombre: String(col(o, "nombre", "nombrerecurso", "recurso")).trim(),
      unidad: String(col(o, "unidad", "und")).trim(), tipo: TIPO_ALIAS[norm(col(o, "tipo"))], proveedor: String(col(o, "proveedor", "nombreproveedor")).trim(),
      ruc: String(col(o, "rucproveedor", "proveedorruc", "ruc")).trim(), marca: String(col(o, "marca")).trim(),
      actualizar: ["si", "s", "1", "true", "yes"].includes(norm(col(o, "actualizarprecio", "actualizar"))) };
    const p = String(col(o, "precio")).replace("S/", "").replace(/\s/g, "");
    f.precio = p === "" ? null : Number(p.includes(",") && p.includes(".") ? p.replace(/\./g, "").replace(",", ".") : p.replace(",", "."));
    const errores = [];
    if (!f.nombre) errores.push("falta nombre"); if (!f.unidad) errores.push("falta unidad"); if (!f.tipo) errores.push("tipo no reconocido");
    if (f.precio == null || !(f.precio > 0)) errores.push("precio inválido"); if (f.ruc && !/^\d{11}$/.test(f.ruc)) errores.push("RUC inválido");
    f.rec = S.recursos.find((r) => (f.codigo && norm(r.codigo) === norm(f.codigo)) || (norm(r.nombre) === norm(f.nombre) && norm(r.unidad) === norm(f.unidad)));
    const clave = f.codigo || norm(f.nombre) + "|" + norm(f.unidad);
    f.accion = f.rec ? (f.actualizar ? "ACTUALIZAR" : f.proveedor || f.ruc ? "OFERTA" : "SIN CAMBIO") : nuevos.has(clave) ? "OFERTA" : (nuevos.add(clave), "CREAR");
    f.ok = !errores.length; f.error = errores.join("; ");
    return f;
  });
}

async function ejecutarImportacion() {
  const validas = S.importacion.filas.filter((f) => f.ok);
  let creados = 0, actualizados = 0, ofertas = 0;
  for (const f of validas) {
    let rec = f.rec || S.recursos.find((r) => (f.codigo && norm(r.codigo) === norm(f.codigo)) || (norm(r.nombre) === norm(f.nombre) && norm(r.unidad) === norm(f.unidad)));
    if (!rec) {
      rec = numRec(await q(sb.from("recursos").insert({ empresa_id: S.empresa.id, codigo: f.codigo || null, nombre: f.nombre, unidad: f.unidad, tipo: f.tipo, precio: f.precio }).select().single()));
      S.recursos.push(rec); creados++;
      await q(sb.from("historial_precios").insert({ empresa_id: S.empresa.id, recurso_id: rec.id, precio_anterior: null, precio_nuevo: f.precio, origen: "IMPORTACIÓN", usuario_id: S.sesion.user.id }));
    } else if (f.actualizar && rec.precio !== f.precio) { await cambiarPrecio(rec, f.precio, "IMPORTACIÓN"); actualizados++; }
    if (f.proveedor || f.ruc) {
      let prov = S.proveedores.find((p) => (f.ruc && p.ruc === f.ruc) || (!f.ruc && norm(p.nombre) === norm(f.proveedor)));
      if (!prov) { prov = await q(sb.from("proveedores").insert({ empresa_id: S.empresa.id, ruc: f.ruc || null, nombre: f.proveedor || "Proveedor " + f.ruc }).select().single()); S.proveedores.push(prov); }
      await q(sb.from("ofertas").insert({ empresa_id: S.empresa.id, recurso_id: rec.id, proveedor_id: prov.id, precio: f.precio, marca: f.marca || null }));
      ofertas++;
    }
  }
  S.importacion = null;
  aviso(`Importación lista: ${creados} nuevos, ${actualizados} precios actualizados, ${ofertas} ofertas`);
  location.hash = "#/recursos"; render();
}

function vTerceros() {
  const edit = puede("terceros");
  const form = (tipo) => edit ? `<form class="campos form-tercero" data-tipo="${tipo}" style="margin-bottom:12px">
    ${tipo === "clientes" ? `<label>Documento<select name="tipo_documento"><option>RUC</option><option>DNI</option><option>CE</option></select></label><label>Número<input name="numero_documento"></label>` : `<label>RUC<input name="ruc" pattern="\\d{11}"></label><label>Contacto<input name="contacto"></label>`}
    <label>Nombre<input name="nombre" required></label><label>Teléfono<input name="telefono"></label><label>Correo<input name="email" type="email"></label>
    <label>&nbsp;<button class="btn pri">Agregar</button></label></form>` : "";
  const fila = (t, x) => `<tr><td><strong>${esc(x.nombre)}</strong></td><td>${esc(t === "clientes" ? `${x.tipo_documento} ${x.numero_documento || ""}` : x.ruc || "")}</td><td>${esc(t === "proveedores" ? x.contacto || "" : "")}</td><td>${esc(x.telefono || "")}</td><td>${esc(x.email || "")}</td>
    <td>${edit ? `<button class="btn mini peligro borrarTercero" data-tipo="${t}" data-id="${x.id}">✕</button>` : ""}</td></tr>`;
  const tabla = (t, lista) => lista.length ? `<table><tr><th>Nombre</th><th>Documento</th><th>${t === "proveedores" ? "Contacto" : ""}</th><th>Teléfono</th><th>Correo</th><th></th></tr>${lista.map((x) => fila(t, x)).join("")}</table>` : `<p class="vacio">Sin registros.</p>`;
  return `<h1>Clientes y proveedores</h1><p class="sub">Asocia clientes a tus presupuestos; los proveedores alimentan la comparación de precios</p>
  <div class="card"><h2>Clientes</h2>${form("clientes")}${tabla("clientes", S.clientes)}</div>
  <div class="card"><h2>Proveedores</h2>${form("proveedores")}${tabla("proveedores", S.proveedores)}</div>`;
}

function vBiblioteca() {
  return `<h1>Biblioteca de APU</h1><p class="sub">Plantillas reales con rendimiento y cuadrilla, listas para cargar en un presupuesto</p>
  <div class="card"><table><tr><th>Partida</th><th>Und</th><th class="num">Rendimiento</th><th class="num">Insumos</th><th class="num">P.U. actual</th></tr>
  ${S.plantillas.map((p) => `<tr><td>${esc(p.descripcion)}</td><td>${esc(p.unidad)}</td><td class="num">${p.rendimiento}</td><td class="num">${p.insumos.length}</td><td class="num">${f2(calcPartida({ ...p, metrado: 1 }, 8).pu)}</td></tr>`).join("")}</table></div>`;
}

function vUsuarios() {
  if (!puede("usuarios")) return `<p class="vacio">Tu rol no permite administrar usuarios.</p>`;
  return `<h1>Usuarios</h1><p class="sub">Invita a tu equipo: la persona crea su cuenta con el correo invitado y entra a tu empresa con el rol elegido</p>
  <div class="card"><h2>Equipo</h2><table><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th></tr>
  ${S.usuarios.map((u) => { const yo = u.id === S.perfil.id; return `<tr><td>${esc(u.nombre)}${yo ? " (tú)" : ""}</td><td>${esc(u.email)}</td>
    <td><select class="rolUsuario" data-id="${u.id}" ${yo ? "disabled" : ""}>${ROLES.map((r) => `<option ${r === u.rol ? "selected" : ""}>${r}</option>`).join("")}</select></td>
    <td>${yo ? "Activo" : `<button class="btn mini ${u.activo ? "" : "pri"} activoUsuario" data-id="${u.id}" data-activo="${u.activo}">${u.activo ? "Desactivar" : "Activar"}</button>`}</td></tr>`; }).join("")}</table></div>
  <div class="card"><h2>Invitar</h2><form id="formInv" class="campos"><label>Correo<input name="email" type="email" required></label>
    <label>Rol<select name="rol">${ROLES.filter((r) => r !== "Administrador").map((r) => `<option>${r}</option>`).join("")}<option>Administrador</option></select></label><label>&nbsp;<button class="btn pri">Invitar</button></label></form>
  ${S.invitaciones.length ? `<table style="margin-top:12px"><tr><th>Correo invitado</th><th>Rol</th><th></th></tr>${S.invitaciones.map((i) => `<tr><td>${esc(i.email)}</td><td>${i.rol}</td><td><button class="btn mini peligro borrarInv" data-id="${i.id}">Anular</button></td></tr>`).join("")}</table>` : ""}
  <p class="sub nota-calc">Roles: Administrador (todo) · Gerente (todo menos usuarios) · Ingeniero (presupuestos y recursos) · Presupuestador (presupuestos) · Consulta (solo ver).</p></div>`;
}

function vEmpresa() {
  const ed = sololectura("empresa");
  return `<h1>Empresa</h1><p class="sub">Datos que aparecen en tus PDF</p>
  <div class="card"><div class="campos"><label>Razón social<input id="eNombre" value="${esc(S.empresa.razon_social)}" ${ed}></label><label>RUC<input id="eRuc" value="${esc(S.empresa.ruc || "")}" ${ed}></label></div></div>
  <div class="card"><h2>Mi cuenta</h2><p>${esc(S.perfil.nombre)} · ${esc(S.perfil.email)} · ${S.perfil.rol}</p><button class="btn" id="cambiarClave">Cambiar contraseña</button></div>
  <div class="card"><h2>Exportar datos</h2><div class="fila"><button class="btn" id="exportarTodo">⬇ Descargar todos mis datos (.json)</button></div></div>`;
}

// ---------- PDF profesional (vista de impresión) ----------
function vImprimir(id) {
  const pres = S.presupuestos.find((p) => p.id === id);
  if (!pres) return `<p class="vacio">Presupuesto no encontrado.</p>`;
  const c = calcPresupuesto(pres);
  const cli = S.clientes.find((x) => x.id === pres.cliente_id);
  const cab = `<header class="doc-cab"><img src="assets/bap_logo_principal.png" alt=""><div><strong>${esc(S.empresa.razon_social)}</strong><br>RUC ${esc(S.empresa.ruc || "—")}</div></header>`;
  setTimeout(() => window.print(), 600);
  return `<div class="no-print fila" style="margin-bottom:14px"><a class="btn" href="#/presupuesto/${pres.id}">← Volver</a><button class="btn oro" onclick="print()">🖨 Imprimir / Guardar PDF</button>
    <span class="sub" style="margin:0">En el diálogo elige "Guardar como PDF".</span></div>
  <article class="doc">${cab}
    <h1 class="doc-titulo">PRESUPUESTO</h1>
    <table class="doc-datos"><tr><td><b>Obra:</b> ${esc(pres.nombre)}</td><td><b>Fecha:</b> ${pres.fecha}</td></tr>
      <tr><td><b>Cliente:</b> ${esc(cli?.nombre || "—")}</td><td><b>${esc(cli?.tipo_documento || "Doc.")}:</b> ${esc(cli?.numero_documento || "—")}</td></tr></table>
    <table class="doc-tabla"><thead><tr><th>Ítem</th><th>Descripción</th><th>Und.</th><th class="num">Metrado</th><th class="num">P.U. (S/)</th><th class="num">Parcial (S/)</th></tr></thead>
      <tbody>${c.partidas.map((x) => `<tr><td>${x.p.codigo}</td><td>${esc(x.p.descripcion)}</td><td>${esc(x.p.unidad)}</td><td class="num">${f2(x.p.metrado)}</td><td class="num">${f2(x.pu)}</td><td class="num">${f2(x.parcial)}</td></tr>`).join("")}</tbody></table>
    <table class="doc-resumen"><tr><td>Costo directo</td><td class="num">${sol(c.cd)}</td></tr><tr><td>Gastos generales (${pres.gg}%)</td><td class="num">${sol(c.gg)}</td></tr>
      <tr><td>Utilidad (${pres.util}%)</td><td class="num">${sol(c.util)}</td></tr><tr><td>Subtotal</td><td class="num">${sol(c.subtotal)}</td></tr>
      <tr><td>IGV (${pres.igv}%)</td><td class="num">${sol(c.igv)}</td></tr><tr class="doc-total"><td>TOTAL</td><td class="num">${sol(c.total)}</td></tr></table>
    <div class="doc-firma"><span>${esc(S.perfil.nombre)}</span><small>${esc(S.empresa.razon_social)}</small></div>
  </article>
  ${c.partidas.map((x) => `<article class="doc salto">${cab}<h2 class="doc-titulo">ANÁLISIS DE PRECIOS UNITARIOS</h2>
    <table class="doc-datos"><tr><td><b>Partida:</b> ${x.p.codigo} ${esc(x.p.descripcion)}</td><td><b>Und.:</b> ${esc(x.p.unidad)}</td></tr>
    <tr><td><b>Rendimiento:</b> ${x.p.rendimiento} ${esc(x.p.unidad)}/día · Jornada ${pres.jornada} h</td><td><b>Costo unitario:</b> ${sol(x.pu)}</td></tr></table>
    ${TIPOS.filter((t) => x.filas.some((f) => f.i.tipo === t)).map((t) => `<h3 class="doc-grupo">${t.toUpperCase()}</h3><table class="doc-tabla"><thead><tr><th>Descripción</th><th>Und.</th><th class="num">Cuadrilla</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Parcial</th></tr></thead><tbody>
      ${x.filas.filter((f) => f.i.tipo === t).map((f) => `<tr><td>${esc(f.i.nombre)}</td><td>${esc(f.i.unidad)}</td><td class="num">${f.i.cuadrilla ?? ""}</td><td class="num">${f.cantidad.toFixed(4)}</td><td class="num">${f2(f.precio)}</td><td class="num">${f2(f.parcial)}</td></tr>`).join("")}
      ${t === "Mano de Obra" && x.herramientas ? `<tr><td>Herramientas manuales</td><td>%MO</td><td></td><td class="num">${x.p.herr}</td><td class="num">${f2(x.por["Mano de Obra"])}</td><td class="num">${f2(x.herramientas)}</td></tr>` : ""}
      <tr class="doc-sub"><td colspan="5">Subtotal ${t}</td><td class="num">${f2(x.por[t] + (t === "Mano de Obra" ? x.herramientas : 0))}</td></tr></tbody></table>`).join("")}
  </article>`).join("")}`;
}

// ---------- Eventos ----------
function enlazar(ruta, a, b) {
  document.querySelectorAll("[data-ir]").forEach((e) => (e.onclick = () => (location.hash = e.dataset.ir)));
  const on = (sel, ev, fn) => document.querySelectorAll(sel).forEach((e) => e.addEventListener(ev, fn));

  if (ruta === "presupuestos") on("#nuevoPres", "click", async () => {
    const p = numPres(await q(sb.from("presupuestos").insert({ empresa_id: S.empresa.id, nombre: "Nuevo presupuesto" }).select().single()));
    S.presupuestos.push(p); location.hash = "#/presupuesto/" + p.id;
  });

  if (ruta === "presupuesto") {
    const pres = S.presupuestos.find((p) => p.id === a);
    if (!pres) return;
    const partida = () => pres.partidas.find((p) => p.id === b) || pres.partidas[0];
    const cambio = (fn) => (e) => { fn(e); guardarPres(pres); render(); };
    const campos = { pNombre: "nombre", pFecha: "fecha", pJornada: "jornada", pGG: "gg", pUtil: "util", pIGV: "igv" };
    Object.entries(campos).forEach(([idc, k]) => on("#" + idc, "change", cambio((e) => (pres[k] = e.target.type === "number" ? Number(e.target.value) || 0 : e.target.value))));
    on("#pCliente", "change", cambio((e) => (pres.cliente_id = e.target.value ? Number(e.target.value) : null)));
    on("[data-partida]", "click", (e) => { if (!e.target.closest("input,button")) location.hash = `#/presupuesto/${pres.id}/${e.currentTarget.dataset.partida}`; });
    on(".metrado", "change", cambio((e) => (pres.partidas.find((p) => p.id === e.target.dataset.id).metrado = Number(e.target.value) || 0)));
    on(".quitar", "click", cambio((e) => { pres.partidas = pres.partidas.filter((p) => p.id !== e.target.dataset.id); numerar(pres); }));
    on("#plantillaSel", "change", (e) => { const pl = S.plantillas.find((p) => p.id === e.target.value); if (!pl) return;
      const np = partidaDesdePlantilla(pl); pres.partidas.push(np); numerar(pres); guardarPres(pres); location.hash = `#/presupuesto/${pres.id}/${np.id}`; });
    on("#partidaVacia", "click", () => { const np = { id: nid(), codigo: "", descripcion: "Nueva partida", unidad: "m2", metrado: 1, rendimiento: 10, herr: 3, insumos: [] };
      pres.partidas.push(np); numerar(pres); guardarPres(pres); location.hash = `#/presupuesto/${pres.id}/${np.id}`; });
    on(".apuCampo", "change", cambio((e) => { partida()[e.target.dataset.k] = e.target.type === "number" ? Number(e.target.value) || 0 : e.target.value; }));
    on(".insCampo", "change", cambio((e) => (partida().insumos[e.target.dataset.n][e.target.dataset.k] = Number(e.target.value) || 0)));
    on(".insQuitar", "click", cambio((e) => partida().insumos.splice(Number(e.target.dataset.n), 1)));
    on("#insRecurso", "change", cambio((e) => { const r = recurso(Number(e.target.value)); if (!r) return;
      const porCuadrilla = r.tipo === "Mano de Obra" || (r.tipo === "Equipo" && /^h/i.test(r.unidad));
      partida().insumos.push({ recursoId: r.id, nombre: r.nombre, unidad: r.unidad, tipo: r.tipo, cuadrilla: porCuadrilla ? 1 : null, cantidad: porCuadrilla ? null : 1, precio: null }); }));
    on("#borrarPres", "click", async () => { if (!confirm("¿Eliminar este presupuesto?")) return;
      await q(sb.from("presupuestos").delete().eq("id", pres.id), "Presupuesto eliminado"); S.presupuestos = S.presupuestos.filter((p) => p !== pres); location.hash = "#/presupuestos"; });
    on("#csvPres", "click", () => exportarPresupuesto(pres));
  }

  if (ruta === "recursos") {
    const filtrar = () => { const t = $("#filtroTipo").value, qq = norm($("#buscar").value);
      document.querySelectorAll("#tablaRec tr[data-busca]").forEach((tr) => (tr.style.display = tr.dataset.busca.includes(qq) && (!t || tr.dataset.tipo === t) ? "" : "none")); };
    on("#buscar", "input", filtrar); on("#filtroTipo", "change", filtrar);
    on(".precioRec", "change", async (e) => { await cambiarPrecio(recurso(Number(e.target.dataset.id)), Math.max(0, Number(e.target.value) || 0), "EDICIÓN MANUAL"); aviso("Precio actualizado; APU recalculados"); });
    on("#nuevoRec", "click", async () => { const nombre = prompt("Nombre del recurso"); if (!nombre) return;
      const unidad = prompt("Unidad (ej. hh, bol, m3, und)", "und") || "und";
      const tipo = TIPOS[Math.max(0, Number(prompt("Tipo: 1 Mano de Obra · 2 Material · 3 Equipo · 4 Subcontrato", "2")) - 1)] || "Material";
      const precio = Number(prompt("Precio (S/)", "0")) || 0;
      S.recursos.push(numRec(await q(sb.from("recursos").insert({ empresa_id: S.empresa.id, codigo: "R" + String(S.recursos.length + 1).padStart(3, "0"), nombre, unidad, tipo, precio }).select().single(), "Recurso creado"))); render(); });
    on("#csvRec", "click", () => descargar("recursos.csv", csv([["Código", "Recurso", "Tipo", "Unidad", "Precio"], ...S.recursos.map((r) => [r.codigo, r.nombre, r.tipo, r.unidad, r.precio])]), "text/csv"));
  }

  if (ruta === "importar") {
    on("#plantillaXlsx", "click", () => { const ws = XLSX.utils.aoa_to_sheet([["Codigo", "Nombre", "Unidad", "Tipo", "Precio", "Proveedor", "RUC_Proveedor", "Marca", "Actualizar_Precio"],
      ["MAT-001", "Cemento Portland Tipo I", "bol", "Material", 30.9, "Proveedor Uno", "20111111111", "Sol", "NO"]]);
      const wb = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(wb, ws, "Importacion"); XLSX.writeFile(wb, "Plantilla_Importacion_BAP.xlsx"); });
    on("#archivoImp", "change", async (e) => { try { const file = e.target.files[0];
      const wb = XLSX.read(await file.arrayBuffer(), { type: "array" }); const ws = wb.Sheets["Importacion"] || wb.Sheets[wb.SheetNames[0]];
      const filas = XLSX.utils.sheet_to_json(ws, { defval: "" }); if (!filas.length) throw new Error("El archivo está vacío");
      S.importacion = { archivo: file.name, filas: analizarImportacion(filas) }; render(); } catch (err) { aviso("No se pudo leer el archivo: " + err.message, true); } });
    on("#confirmarImp", "click", async (e) => { e.target.disabled = true; e.target.textContent = "Importando…"; try { await ejecutarImportacion(); } catch { e.target.disabled = false; } });
    on("#cancelarImp", "click", () => { S.importacion = null; render(); });
  }

  if (ruta === "terceros") {
    on(".form-tercero", "submit", async (e) => { e.preventDefault(); const t = e.target.dataset.tipo;
      const d = Object.fromEntries([...new FormData(e.target)].map(([k, v]) => [k, String(v).trim() || null]));
      S[t].push(await q(sb.from(t).insert({ ...d, empresa_id: S.empresa.id }).select().single(), "Registro agregado")); render(); });
    on(".borrarTercero", "click", async (e) => { if (!confirm("¿Eliminar este registro?")) return; const { tipo, id } = e.target.dataset;
      await q(sb.from(tipo).delete().eq("id", id), "Eliminado"); S[tipo] = S[tipo].filter((x) => x.id !== Number(id)); render(); });
  }

  if (ruta === "usuarios") {
    on(".rolUsuario", "change", async (e) => { await q(sb.from("perfiles").update({ rol: e.target.value }).eq("id", e.target.dataset.id), "Rol actualizado"); await cargarUsuarios(); });
    on(".activoUsuario", "click", async (e) => { const activo = e.target.dataset.activo !== "true";
      await q(sb.from("perfiles").update({ activo }).eq("id", e.target.dataset.id), activo ? "Usuario activado" : "Usuario desactivado"); await cargarUsuarios(); render(); });
    on("#formInv", "submit", async (e) => { e.preventDefault(); const d = Object.fromEntries(new FormData(e.target));
      await q(sb.from("invitaciones").insert({ empresa_id: S.empresa.id, email: d.email.trim().toLowerCase(), rol: d.rol }), "Invitación creada: pídele que cree su cuenta con ese correo");
      await cargarUsuarios(); render(); });
    on(".borrarInv", "click", async (e) => { await q(sb.from("invitaciones").delete().eq("id", e.target.dataset.id), "Invitación anulada"); await cargarUsuarios(); render(); });
  }

  if (ruta === "empresa") {
    const guardarEmp = async () => { const razon_social = $("#eNombre").value.trim(); if (!razon_social) return aviso("La razón social es obligatoria", true);
      Object.assign(S.empresa, await q(sb.from("empresas").update({ razon_social, ruc: $("#eRuc").value.trim() || null }).eq("id", S.empresa.id).select().single(), "Empresa actualizada")); render(); };
    on("#eNombre", "change", guardarEmp); on("#eRuc", "change", guardarEmp);
    on("#cambiarClave", "click", vNuevaClave);
    on("#exportarTodo", "click", () => { const { sesion, importacion, plantillas, ...datos } = S; descargar(`bap-apu-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(datos, null, 1), "application/json"); });
  }
}

function exportarPresupuesto(pres) {
  const c = calcPresupuesto(pres);
  const filas = [[S.empresa.razon_social, "RUC " + (S.empresa.ruc || "")], [pres.nombre], ["Cliente", nombreCliente(pres.cliente_id), "Fecha", pres.fecha], [], ["Ítem", "Descripción", "Und", "Metrado", "P.U.", "Parcial"]];
  c.partidas.forEach((x) => filas.push([x.p.codigo, x.p.descripcion, x.p.unidad, x.p.metrado, x.pu.toFixed(2), x.parcial.toFixed(2)]));
  filas.push([], ["", "Costo directo", "", "", "", c.cd.toFixed(2)], ["", `Gastos generales ${pres.gg}%`, "", "", "", c.gg.toFixed(2)], ["", `Utilidad ${pres.util}%`, "", "", "", c.util.toFixed(2)],
    ["", "Subtotal", "", "", "", c.subtotal.toFixed(2)], ["", `IGV ${pres.igv}%`, "", "", "", c.igv.toFixed(2)], ["", "TOTAL", "", "", "", c.total.toFixed(2)]);
  c.partidas.forEach((x) => { filas.push([], [`APU ${x.p.codigo}`, x.p.descripcion, `Rend. ${x.p.rendimiento} ${x.p.unidad}/día`], ["Tipo", "Insumo", "Und", "Cuadrilla", "Cantidad", "Precio", "Parcial"]);
    x.filas.forEach((f) => filas.push([f.i.tipo, f.i.nombre, f.i.unidad, f.i.cuadrilla ?? "", f.cantidad, f.precio.toFixed(2), f.parcial.toFixed(2)]));
    filas.push(["", `Herramientas ${x.p.herr}% MO`, "", "", "", "", x.herramientas.toFixed(2)], ["", "Precio unitario", "", "", "", "", x.pu.toFixed(2)]); });
  descargar(`${pres.nombre.replace(/[^\w\- ]+/g, "")}.csv`, csv(filas), "text/csv");
}

// ---------- Arranque ----------
async function arrancar() {
  const { data } = await sb.auth.getSession();
  S.sesion = data.session;
  if (!S.sesion) { S.perfil = null; return vAcceso(location.hash === "#registro" ? "registro" : "entrar"); }
  try {
    await cargarTodo();
    if (!S.perfil || !S.perfil.activo) { $("#app").innerHTML = `<div class="acceso"><div class="acceso-card"><h1>Cuenta sin acceso</h1><p class="sub">Tu usuario está desactivado o no pertenece a ninguna empresa. Habla con el administrador.</p><button class="btn" id="salir2">Cerrar sesión</button></div></div>`; $("#salir2").onclick = () => sb.auth.signOut(); return; }
    $("#sidebar").hidden = false;
    render();
  } catch (err) { $("#app").innerHTML = `<p class="vacio">No se pudieron cargar los datos: ${esc(err.message)}</p>`; }
}

sb.auth.onAuthStateChange((evento) => {
  if (evento === "PASSWORD_RECOVERY") return vNuevaClave();
  if (evento === "SIGNED_IN" && !S.perfil) arrancar();
  if (evento === "SIGNED_OUT") { Object.assign(S, { sesion: null, perfil: null }); vAcceso(); }
});
arrancar();
