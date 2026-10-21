// Edge Function: sugiere el APU de una partida con Claude, usando los recursos de la empresa.
import Anthropic from "npm:@anthropic-ai/sdk";
import { createClient } from "npm:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const TIPOS = ["Mano de Obra", "Material", "Equipo", "Subcontrato"];
const responder = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { ...CORS, "Content-Type": "application/json" } });

type Recurso = { id: number; nombre: string; unidad: string; tipo: string; precio?: number };

const ESQUEMA = {
  type: "object",
  additionalProperties: false,
  required: ["descripcion", "unidad", "rendimiento", "herr", "insumos", "nota"],
  properties: {
    descripcion: { type: "string" },
    unidad: { type: "string" },
    rendimiento: { type: "number" },
    herr: { type: "number" },
    nota: { type: "string" },
    insumos: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["recursoId", "nombre", "unidad", "tipo", "cuadrilla", "cantidad", "precio"],
        properties: {
          recursoId: { type: ["integer", "null"] },
          nombre: { type: "string" },
          unidad: { type: "string" },
          tipo: { type: "string", enum: TIPOS },
          cuadrilla: { type: ["number", "null"] },
          cantidad: { type: ["number", "null"] },
          precio: { type: ["number", "null"] },
        },
      },
    },
  },
};

const SISTEMA = `Eres un ingeniero de costos de construcción en el Perú. Armas análisis de precios unitarios (APU) con criterios usuales del mercado peruano (rendimientos tipo CAPECO, jornada de 8 h, cuadrillas de operario, oficial y peón).
Reglas:
- "rendimiento" es la producción por día en la unidad de la partida.
- "herr" es el porcentaje de herramientas manuales sobre la mano de obra (normalmente 3 a 5).
- Mano de obra y equipos por hora (hh, hm): usa "cuadrilla" (número de personas o equipos) y deja "cantidad" en null.
- Materiales, subcontratos y equipos que no son por hora: usa "cantidad" por unidad de partida y deja "cuadrilla" en null.
- Si un insumo coincide con un recurso del catálogo de la empresa, usa su "recursoId", su nombre y su unidad exactos, y deja "precio" en null.
- Si no hay coincidencia, pon "recursoId" en null y estima un "precio" referencial en soles.
- No incluyas las herramientas manuales como insumo; van en "herr".
- En "nota" explica en una o dos frases los supuestos principales.`;

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return responder({ error: "Método no permitido" }, 405);

  const clave = Deno.env.get("ANTHROPIC_API_KEY");
  if (!clave) {
    return responder({ error: "El asistente IA no está configurado: falta el secreto ANTHROPIC_API_KEY en Supabase (Edge Functions → Secrets).", codigo: "SIN_CLAVE" }, 503);
  }

  // Solo usuarios con permiso de presupuestos y suscripción vigente (la función puede() lo verifica).
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: req.headers.get("Authorization") ?? "" } },
  });
  const { data: permitido, error: errPermiso } = await sb.rpc("puede", { accion: "presupuestos" });
  if (errPermiso || !permitido) return responder({ error: "Tu usuario no puede crear partidas (rol sin permiso o plan vencido)." }, 403);

  let cuerpo: { descripcion?: string; recursos?: Recurso[]; jornada?: number };
  try { cuerpo = await req.json(); } catch { return responder({ error: "Cuerpo JSON inválido" }, 400); }
  const descripcion = String(cuerpo.descripcion ?? "").trim().slice(0, 300);
  if (!descripcion) return responder({ error: "Escribe la descripción de la partida" }, 400);
  const recursos = (Array.isArray(cuerpo.recursos) ? cuerpo.recursos : []).slice(0, 800)
    .filter((r) => r && Number.isInteger(r.id))
    .map((r) => ({ id: r.id, nombre: String(r.nombre).slice(0, 120), unidad: String(r.unidad).slice(0, 20), tipo: String(r.tipo), precio: Number(r.precio) || 0 }));
  const jornada = Number(cuerpo.jornada) > 0 ? Number(cuerpo.jornada) : 8;

  const catalogo = recursos.map((r) => `${r.id}\t${r.tipo}\t${r.nombre}\t${r.unidad}\t${r.precio.toFixed(2)}`).join("\n");
  const client = new Anthropic({ apiKey: clave });
  try {
    const respuesta = await client.beta.messages.create({
      model: "claude-sonnet-5-5",
      max_tokens: 8000,
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      output_config: { effort: "medium", format: { type: "json_schema", schema: ESQUEMA } },
      system: SISTEMA,
      messages: [{
        role: "user",
        content: `Catálogo de recursos de la empresa (id, tipo, nombre, unidad, precio S/):\n${catalogo || "(vacío)"}\n\nJornada: ${jornada} h.\nArma el APU de esta partida: ${descripcion}`,
      }],
    } as never) as unknown as { stop_reason: string; content: { type: string; text?: string }[] };

    if (respuesta.stop_reason === "refusal") return responder({ error: "El asistente no pudo generar esta partida. Reformula la descripción." }, 422);
    const texto = respuesta.content.find((b) => b.type === "text")?.text;
    if (!texto) return responder({ error: "El asistente no devolvió una respuesta." }, 502);
    const apu = JSON.parse(texto);

    // Valida los recursos sugeridos contra el catálogo enviado.
    const porId = new Map(recursos.map((r) => [r.id, r]));
    apu.insumos = (apu.insumos ?? []).map((i: Record<string, unknown>) => {
      const rec = i.recursoId != null ? porId.get(Number(i.recursoId)) : undefined;
      const tipo = TIPOS.includes(String(rec?.tipo ?? i.tipo)) ? String(rec?.tipo ?? i.tipo) : "Material";
      const porCuadrilla = i.cuadrilla != null && Number(i.cuadrilla) > 0;
      return {
        recursoId: rec ? rec.id : null,
        nombre: rec ? rec.nombre : String(i.nombre),
        unidad: rec ? rec.unidad : String(i.unidad),
        tipo,
        cuadrilla: porCuadrilla ? Number(i.cuadrilla) : null,
        cantidad: porCuadrilla ? null : Number(i.cantidad) || 0,
        precio: rec ? null : Number(i.precio) || 0,
      };
    });
    apu.rendimiento = Math.max(0, Number(apu.rendimiento) || 0);
    apu.herr = Math.max(0, Number(apu.herr) || 0);
    return responder({ apu });
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) return responder({ error: "La clave ANTHROPIC_API_KEY no es válida. Revísala en Supabase (Edge Functions → Secrets).", codigo: "CLAVE_INVALIDA" }, 503);
    if (err instanceof Anthropic.RateLimitError) return responder({ error: "El asistente está ocupado. Intenta en un minuto." }, 429);
    if (err instanceof Anthropic.APIError) return responder({ error: "Error del servicio de IA: " + err.message }, 502);
    return responder({ error: "No se pudo procesar la sugerencia: " + (err as Error).message }, 500);
  }
});
