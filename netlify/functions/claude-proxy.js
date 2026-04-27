const SUPABASE_URL = "https://wuizpohykpvppmydfcng.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind1aXpwb2h5a3B2cHBteWRmY25nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyNDI1NDQsImV4cCI6MjA5MjgxODU0NH0.xFLEDRLmpvjR1oFZE9TetyT8706W_BQPr7vTrNR9sj8";

const SYSTEM_PROMPT = `Eres un asistente comercial experto en selección de kits para vehículos.

ESTILO:
- Texto natural y conversacional. NUNCA uses ## o ### ni "PASO X".
- Conciso: máximo 3-4 líneas por respuesta salvo cuando muestres opciones.
- Confirma datos con "✓ [dato]" y pasa a la siguiente pregunta.
- Una sola pregunta por turno.

SELECCIÓN FINAL:
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor] · [vigente desde year_from_v4] · [componente] · [diferencial]
📋 Notas: (solo info relevante de noteeng para el instalador)
🔧 Embrague [estándar/especial]: (solo si embrague_esp no vacío)

REGLAS:
- Solo recomiendas códigos que existan en los datos recibidos.
- No inventas datos. Una pregunta por turno.
- Excluye STANDARD BRACKET y COMPRESSOR BRACKET.

FLUJO (detente al llegar a 1 código único):

1. TIPO DE KIT — siempre primera:
   KB=compresor A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis

2. MARCA — campo brand.
   💡 Permiso circulación campo D.1

3. MODELO — muestra opciones reales de model_clean (4-8 ejemplos).
   💡 Permiso campos D.2 y D.3

4. TRACCIÓN — inmediatamente tras confirmar modelo, si hay variantes RWD/FWD en los datos:
   "¿Tracción trasera (RWD) o delantera (FWD)?"
   Si solo hay una opción, omite.

5. ¿VEHÍCULO NUEVO? — tras modelo y tracción:
   "¿Es un vehículo de matriculación reciente?"
   SÍ = usa kits con year_to_int NULO (vigentes, sin fecha fin).
   NO = pide año exacto.

6. AÑO — solo si no dijo nuevo:
   "¿Año de fabricación o primera matriculación?"
   Filtro: year_from_int <= año Y (year_to_int nulo O year_to_int >= año)
   💡 Permiso campo B

7. MOTOR — si quedan varios. Muestra opciones reales de engine_clean.

8. COMPONENTE — agrupa por tipo. Muestra opciones reales de nom_opcio_compressor.

9. FLAGS KIT (solo si varían entre candidatos, en orden):
   flag_gearbox_v3: ok=auto OK, not=NO auto, vacío=ambas → NO preguntar si todos vacíos
   flag_auto_tensioner → tensor auto vs estándar
   flag_pfmot_yes/no → PTO/PFMot
   flag_urban_kit → entorno urbano
   flag_ind_belt → correa independiente
   flag_n63_pulley_yes/no + flag_n63_full_option → polea N62/N63
   flag_sanden → compresor SANDEN

10. A/C — solo si ac_filter mezcla yes/no: "¿Tiene A/C de fábrica?"
    ac_filter=any → NO preguntar.`;

// Extract structured state from conversation
function extractState(messages) {
  const text = messages.map(m => typeof m.content === 'string' ? m.content : '').join(' ');
  const s = {};

  // Kit type
  if (/compresor\s*a\/c|kb\b/i.test(text)) s.kit_type = 'Kit compresor A/C';
  else if (/fr[ií]o\s*industrial|kc\b/i.test(text)) s.kit_type = 'Kit compresor frío industrial';
  else if (/alternador|ka\b/i.test(text)) s.kit_type = 'Kit alternador';
  else if (/bomba|kh\b/i.test(text)) s.kit_type = 'Kit bomba hidráulica';
  else if (/generador|kg\b/i.test(text)) s.kit_type = 'Kit generador';
  else if (/chasis|kf\b/i.test(text)) s.kit_type = 'Kit chasis';

  // Brand
  const brandMap = [
    [/sprinter|vito|actros|atego|arocs|antos|axor|econic/i, 'MERCEDES'],
    [/ducato|scudo|talento|doblo/i, 'FIAT'],
    [/transit|tourneo/i, 'FORD'],
    [/\bmaster\b|trafic|kangoo/i, 'RENAULT'],
    [/\bdaily\b|eurocargo|stralis|trakker/i, 'IVECO'],
    [/\bbox[e]?r\b|expert|partner/i, 'PEUGEOT'],
    [/jumper|jumpy|berlingo/i, 'CITROEN'],
    [/crafter|transporter|\btge\b/i, 'VW'],
    [/movano|vivaro|\bcombo\b/i, 'OPEL'],
    [/nv400|nv300|interstar|primastar/i, 'NISSAN'],
    [/\btgl\b|\btgm\b|\btgs\b|\btgx\b/i, 'MAN'],
    [/canter|fuso/i, 'MITSUBISHI'],
    [/\bvolvo\b/i, 'VOLVO'],
    [/\bdaf\b/i, 'DAF'],
  ];
  for (const [re, brand] of brandMap) {
    if (re.test(text)) { s.brand = brand; break; }
  }
  for (const b of ['RENAULT','FIAT','IVECO','FORD','MERCEDES','VW','OPEL','NISSAN','PEUGEOT','CITROEN','MAN','DAF','VOLVO','TOYOTA','MITSUBISHI']) {
    if (new RegExp('\\b'+b+'\\b','i').test(text)) { s.brand = b; break; }
  }

  // Traction
  if (/\brwd\b|tracci[oó]n\s*trasera|rear\s*wheel/i.test(text)) s.flag_rwd = true;
  if (/\bfwd\b|tracci[oó]n\s*delantera|front\s*wheel/i.test(text)) s.flag_fwd = true;

  // New vehicle
  if (/nuevo|reciente|nueva\s*matriculaci/i.test(text)) s.new_vehicle = true;

  // Year
  const ym = text.match(/\b(19[89]\d|20[012]\d)\b/);
  if (ym && !s.new_vehicle) s.year = parseInt(ym[1]);

  // Component
  const cm = text.match(/\b(TM\s*\d+|UP\s*\d+|SD[57][HL]\d+|CS\s*\d+|G[34]-[24]\d+V)/i);
  if (cm) s.component = cm[1].replace(/\s+/,'');

  return s;
}

async function queryDB(s) {
  const parts = [
    'brand=neq.ACCESSORY',
    'kit_type=neq.Otro',
    'model_clean=neq.STANDARD%20BRACKET',
    'model_clean=neq.COMPRESSOR%20BRACKET',
  ];

  if (s.kit_type) parts.push(`kit_type=eq.${encodeURIComponent(s.kit_type)}`);
  if (s.brand) parts.push(`brand=eq.${encodeURIComponent(s.brand)}`);
  if (s.model_clean) parts.push(`model_clean=eq.${encodeURIComponent(s.model_clean)}`);
  if (s.engine_clean) parts.push(`engine_clean=eq.${encodeURIComponent(s.engine_clean)}`);
  if (s.flag_rwd) parts.push('flag_rwd=eq.Yes');
  if (s.flag_fwd) parts.push('flag_fwd=eq.Yes');
  if (s.new_vehicle) {
    parts.push('year_to_int=is.null');
  } else if (s.year) {
    parts.push(`year_from_int=lte.${s.year}`);
    parts.push(`or=(year_to_int.is.null,year_to_int.gte.${s.year})`);
  }
  if (s.component) parts.push(`nom_opcio_compressor=ilike.*${encodeURIComponent(s.component)}*`);

  // Limit aggressively - we only need enough to show options
  parts.push('limit=100');

  const url = `${SUPABASE_URL}/rest/v1/kits?${parts.join('&')}`;
  const r = await fetch(url, {
    headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
  });
  if (!r.ok) throw new Error(`DB error ${r.status}`);
  return r.json();
}

function summarizeDB(data, state) {
  if (!data || data.length === 0) return { summary: 'Sin datos', data: [] };

  // Deduplicate by code for counting
  const byCode = {};
  for (const row of data) {
    if (!byCode[row.code]) byCode[row.code] = row;
  }
  const codes = Object.values(byCode);

  // Build compact summary - only unique values per field
  const uniq = (arr) => [...new Set(arr.filter(Boolean))];

  const summary = {
    total_codes: codes.length,
    kit_types: uniq(codes.map(r => r.kit_type)),
    brands: uniq(codes.map(r => r.brand)),
    models: uniq(codes.map(r => r.model_clean)),
    engines: uniq(codes.map(r => r.engine_clean)),
    year_ranges: uniq(codes.map(r => r.year_from_v4 ? `desde ${r.year_from_v4}${r.year_to_v4 ? ` hasta ${r.year_to_v4}` : ''}` : null)),
    components: uniq(data.map(r => r.nom_opcio_compressor)),
    tractions: {
      rwd: codes.filter(r => r.flag_rwd === 'Yes').length,
      fwd: codes.filter(r => r.flag_fwd === 'Yes').length,
    },
    flags_present: {
      auto_tensioner: codes.some(r => r.flag_auto_tensioner === 'Yes'),
      n63_pulley_yes: codes.some(r => r.flag_n63_pulley_yes === 'Yes'),
      n63_pulley_no: codes.some(r => r.flag_n63_pulley_no === 'Yes'),
      n63_full: codes.some(r => r.flag_n63_full_option === 'Yes'),
      pfmot_yes: codes.some(r => r.flag_pfmot_yes === 'Yes'),
      pfmot_no: codes.some(r => r.flag_pfmot_no === 'Yes'),
      urban: codes.some(r => r.flag_urban_kit === 'Yes'),
      sanden: codes.some(r => r.flag_sanden === 'Yes'),
      gearbox_v3_mixed: uniq(codes.map(r => r.flag_gearbox_v3)).length > 1,
      awd: codes.some(r => r.flag_awd === 'Yes'),
    },
    ac_values: uniq(codes.map(r => r.ac_filter)),
  };

  // If few codes left, include full detail
  let detail = [];
  if (codes.length <= 10) {
    detail = codes.map(r => ({
      code: r.code,
      model: r.model_clean,
      engine: r.engine_clean,
      year_from: r.year_from_v4,
      year_to: r.year_to_v4,
      component: data.filter(d => d.code === r.code).map(d => d.nom_opcio_compressor),
      flag_rwd: r.flag_rwd,
      flag_fwd: r.flag_fwd,
      flag_awd: r.flag_awd,
      flag_auto_tensioner: r.flag_auto_tensioner,
      flag_n63_pulley_yes: r.flag_n63_pulley_yes,
      flag_n63_pulley_no: r.flag_n63_pulley_no,
      flag_n63_full_option: r.flag_n63_full_option,
      flag_pfmot_yes: r.flag_pfmot_yes,
      flag_pfmot_no: r.flag_pfmot_no,
      flag_urban_kit: r.flag_urban_kit,
      flag_sanden: r.flag_sanden,
      flag_gearbox_v3: r.flag_gearbox_v3,
      flag_himatic: r.flag_himatic,
      flag_ind_belt: r.flag_ind_belt,
      ac_filter: r.ac_filter,
      noteeng: r.noteeng,
      embrague_esp: r.embrague_esp,
      embrague_std: r.embrague_std,
    }));
  }

  return { summary, detail };
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };
  const API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!API_KEY) return { statusCode: 500, body: JSON.stringify({ error: 'API key no configurada' }) };

  try {
    const body = JSON.parse(event.body);
    const messages = body.messages || [];

    const state = extractState(messages);
    let dbResult = { summary: 'Sin datos aún', detail: [] };

    try {
      const data = await queryDB(state);
      dbResult = summarizeDB(data, state);
    } catch(e) {
      console.error('DB error:', e.message);
    }

    const ctx = `\n\n[BD - Filtros activos: ${JSON.stringify(state)}]\n[Resumen: ${JSON.stringify(dbResult.summary)}]\n${dbResult.detail.length > 0 ? '[Detalle códigos: ' + JSON.stringify(dbResult.detail) + ']' : ''}`;

    const msgsWithCtx = [...messages];
    const last = msgsWithCtx[msgsWithCtx.length - 1];
    msgsWithCtx[msgsWithCtx.length - 1] = {
      ...last,
      content: (typeof last.content === 'string' ? last.content : '') + ctx
    };

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 800,
        system: SYSTEM_PROMPT,
        messages: msgsWithCtx
      })
    });

    const data = await resp.json();
    if (!resp.ok) return { statusCode: resp.status, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: data.error?.message }) };
    return { statusCode: 200, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) };

  } catch(err) {
    return { statusCode: 500, headers: {'Content-Type':'application/json'}, body: JSON.stringify({ error: err.message }) };
  }
};
