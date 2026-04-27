const SUPABASE_URL = "https://wuizpohykpvppmydfcng.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind1aXpwb2h5a3B2cHBteWRmY25nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyNDI1NDQsImV4cCI6MjA5MjgxODU0NH0.xFLEDRLmpvjR1oFZE9TetyT8706W_BQPr7vTrNR9sj8";

const SYSTEM_PROMPT = `Eres un asistente experto en selección de kits para vehículos industriales y furgonetas de frío.
Tienes acceso a una base de datos de kits. En cada mensaje recibirás los datos filtrados relevantes en JSON.

REGLAS:
- Solo recomiendas códigos que existan en los datos proporcionados.
- No inventas productos, referencias ni datos técnicos.
- Una sola pregunta por turno.
- Si algo no está en los datos, di que no consta en la base de datos.

FLUJO (sigue este orden exacto, detente cuando quede 1 código):

PASO 1 — TIPO DE KIT (primera pregunta siempre):
- Kit compresor A/C (KB...) — aire acondicionado de cabina
- Kit compresor frío industrial (KC...) — frío de transporte
- Kit alternador (KA...) — alternador auxiliar
- Kit bomba hidráulica (KH...) — bomba hidráulica
- Kit generador (KG...) — generador eléctrico
- Kit chasis (KF...) — adaptación de chasis

PASO 2 — ¿VEHÍCULO NUEVO? Si sí → filtra year_from_int = model_max_year tras identificar modelo.

PASO 3 — MARCA (campo brand). 💡 España/UE: Permiso circulación campo D.1

PASO 4 — MODELO (campo model_clean). Muestra 4-8 opciones reales.
💡 España/UE: Permiso campos D.2 y D.3

PASO 5 — MOTOR (campo engine_clean).
💡 España/UE: Permiso campo P.5 o P.3

PASO 6 — AÑO: "¿Sabes el año de fabricación o primera matriculación?"
Filtro: year_from_int <= año AND (year_to_int IS NULL OR year_to_int >= año)
💡 España/UE: Permiso campo B. Fecha primera matriculación

PASO 7 — COMPONENTE (campo nom_opcio_compressor). Agrupa por tipo.

PASO 8 — FLAGS VEHÍCULO (solo si varían entre candidatos):
flag_rwd/fwd/awd=tracción | flag_rhd=volante derecha | flag_start_stop=Start&Stop

PASO 9 — FLAGS KIT por orden de poder resolutivo (solo si varían):
1. flag_gearbox_v3: ok=auto compatible, not=NO compatible, vacío=válido ambas → NO preguntar si todos vacíos
2. flag_auto_tensioner → tensor auto vs estándar
3. flag_pfmot_yes/no → opción PFMot/PTO
4. flag_urban_kit → entorno urbano
5. flag_ind_belt → correa independiente
6. flag_n63_pulley_yes/no + flag_n63_full_option → polea N62/N63
7. flag_sanden → compresor SANDEN
8. Resto flags en orden de tabla

PASO 10 — A/C (ac_filter): any=NO preguntar | yes vs no → "¿Tiene A/C de fábrica?"

SELECCIÓN FINAL:
✅ Referencia seleccionada: [CODE]
Motivo: [modelo] · [motor] · [desde year_from_v4] · [componente] · [diferencial]
📋 Notas: (solo si hay noteeng relevante para instalador)
🔧 Embrague: (solo si embrague_esp no está vacío; esp=std→estándar, esp≠std→especial)

CASOS ESPECIALES:
- STANDARD BRACKET/COMPRESSOR BRACKET → excluir salvo petición explícita
- year_confidence=doubt → no descartar, informar
- Sin resultado → decirlo, no inventar`;

async function querySupabase(params) {
  let url = `${SUPABASE_URL}/rest/v1/kits?`;
  const parts = [];

  if (params.kit_type) parts.push(`kit_type=eq.${encodeURIComponent(params.kit_type)}`);
  if (params.brand) parts.push(`brand=eq.${encodeURIComponent(params.brand)}`);
  if (params.model_clean) parts.push(`model_clean=eq.${encodeURIComponent(params.model_clean)}`);
  if (params.engine_clean) parts.push(`engine_clean=eq.${encodeURIComponent(params.engine_clean)}`);
  if (params.year) {
    parts.push(`year_from_int=lte.${params.year}`);
    parts.push(`or=(year_to_int.is.null,year_to_int.gte.${params.year})`);
  }
  if (params.nom_opcio_compressor) parts.push(`nom_opcio_compressor=ilike.*${encodeURIComponent(params.nom_opcio_compressor)}*`);
  if (params.new_vehicle && params.model_max_year) parts.push(`year_from_int=eq.${params.model_max_year}`);

  // Exclude accessories
  parts.push(`brand=neq.ACCESSORY`);
  parts.push(`kit_type=neq.Otro`);

  parts.push(`limit=200`);
  url += parts.join('&');

  const resp = await fetch(url, {
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`
    }
  });

  if (!resp.ok) throw new Error(`Supabase error: ${resp.status}`);
  return resp.json();
}

function extractParams(messages) {
  const text = messages.map(m => typeof m.content === 'string' ? m.content : '').join(' ').toLowerCase();
  const params = {};

  // Kit type
  if (text.includes('compresor a/c') || text.match(/\bkb\b/)) params.kit_type = 'Kit compresor A/C';
  else if (text.includes('frío industrial') || text.includes('frio industrial') || text.match(/\bkc\b/)) params.kit_type = 'Kit compresor frío industrial';
  else if (text.includes('alternador') || text.match(/\bka\b/)) params.kit_type = 'Kit alternador';
  else if (text.includes('bomba') || text.match(/\bkh\b/)) params.kit_type = 'Kit bomba hidráulica';
  else if (text.includes('generador') || text.match(/\bkg\b/)) params.kit_type = 'Kit generador';
  else if (text.includes('chasis') || text.match(/\bkf\b/)) params.kit_type = 'Kit chasis';

  // Brand
  const brands = ['RENAULT','FIAT','IVECO','FORD','MERCEDES','VW','OPEL','NISSAN','PEUGEOT','CITROEN','MAN','DAF','VOLVO','TOYOTA','MITSUBISHI'];
  for (const b of brands) {
    if (text.includes(b.toLowerCase()) || text.includes(b.toLowerCase().substring(0,4))) {
      params.brand = b;
      break;
    }
  }
  if (text.includes('sprinter') || text.includes('vito') || text.includes('actros') || text.includes('atego')) params.brand = 'MERCEDES';
  if (text.includes('ducato') || text.includes('scudo') || text.includes('talento')) params.brand = 'FIAT';
  if (text.includes('transit') || text.includes('tourneo')) params.brand = 'FORD';
  if (text.includes('master') || text.includes('trafic') || text.includes('kangoo')) params.brand = 'RENAULT';
  if (text.includes('daily') || text.includes('eurocargo') || text.includes('stralis')) params.brand = 'IVECO';
  if (text.includes('boxer') || text.includes('expert')) params.brand = 'PEUGEOT';
  if (text.includes('jumper') || text.includes('jumpy') || text.includes('berlingo')) params.brand = 'CITROEN';
  if (text.includes('crafter') || text.includes('transporter') || text.includes('caddy')) params.brand = 'VW';
  if (text.includes('movano') || text.includes('vivaro')) params.brand = 'OPEL';

  // Year
  const yearMatch = text.match(/\b(19[89]\d|20[012]\d)\b/);
  if (yearMatch) params.year = parseInt(yearMatch[1]);

  // New vehicle
  if (text.includes('vehículo nuevo') || text.includes('vehiculo nuevo') || text.includes('es nuevo') || text.includes('si, es nuevo')) {
    params.new_vehicle = true;
  }

  return params;
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };

  const API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!API_KEY) return { statusCode: 500, body: JSON.stringify({ error: 'API key no configurada' }) };

  try {
    const body = JSON.parse(event.body);
    const messages = body.messages || [];

    // Extract filters from conversation
    const params = extractParams(messages);

    // Query Supabase with filters
    let dbData = [];
    try {
      dbData = await querySupabase(params);
    } catch(e) {
      console.error('Supabase error:', e);
    }

    // Build context for Claude
    const dataContext = dbData.length > 0
      ? `\n\nDATOS BD FILTRADOS (${dbData.length} registros):\n${JSON.stringify(dbData)}`
      : '\n\nBD: Sin datos filtrados aún. Comienza el flujo de selección.';

    // Add context to last user message
    const messagesWithContext = [...messages];
    if (messagesWithContext.length > 0) {
      const last = messagesWithContext[messagesWithContext.length - 1];
      messagesWithContext[messagesWithContext.length - 1] = {
        ...last,
        content: (typeof last.content === 'string' ? last.content : '') + dataContext
      };
    }

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 1500,
        system: SYSTEM_PROMPT,
        messages: messagesWithContext
      })
    });

    const data = await resp.json();
    if (!resp.ok) return { statusCode: resp.status, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: data.error?.message || 'Error API' }) };

    return { statusCode: 200, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) };

  } catch(err) {
    return { statusCode: 500, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: err.message }) };
  }
};
