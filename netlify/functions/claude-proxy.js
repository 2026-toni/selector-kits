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
📋 Notas importantes: (muestra TODO el contenido de noteeng relevante para el instalador — NO omitas nada: herramientas, restricciones, opciones de fábrica, referencias de piezas adicionales, etc.)
🔧 EMBRAGUE — El kit base ya incluye embrague_std de serie. REGLA: si embrague_esp tiene valor (sea igual o distinto a embrague_std) → ofrecer versión especial. Sufijo según tipus_embrague: N=nada | N-E=[CODE]E (TM/UP/UNICLA) | N-S=[CODE]S (SANDEN) | N-E/S=ambos [CODE]E y [CODE]S. Si tipus_embrague es N o vacío → no ofrecer nada.

REGLAS:
- Solo recomiendas códigos que existan en los datos recibidos.
- No inventas datos. Una pregunta por turno.
- Excluye STANDARD BRACKET y COMPRESSOR BRACKET.
- Si el usuario pide un componente que SÍ aparece en los datos, úsalo aunque tenga formato distinto (ej: "TM15" = "TM 15 / QP 15").
- NUNCA digas que un componente no existe si aparece en la lista de componentes disponibles.

FLUJO (detente al llegar a 1 código único):

1. TIPO DE KIT — siempre primera:
   KB=compresor A/C · KC=frío industrial · KA=alternador · KH=bomba · KG=generador · KF=chasis

2. MARCA — campo brand.
   💡 Permiso circulación campo D.1

3. MODELO — muestra opciones reales de model_clean (4-8 ejemplos).
   💡 Permiso campos D.2 y D.3

4. TRACCIÓN — inmediatamente tras confirmar modelo, si hay variantes RWD/FWD en los datos:
   "¿Tracción trasera (RWD) o delantera (FWD)?"
   Si solo hay una opción de tracción, omite.

5. ¿VEHÍCULO NUEVO? — tras modelo y tracción:
   "¿Es un vehículo de matriculación reciente?"
   SÍ = usa kits con year_to_int NULO (vigentes, sin fecha fin).
   NO = pide año exacto.

6. AÑO — solo si no dijo nuevo:
   "¿Año de fabricación o primera matriculación?"
   Filtro: year_from_int <= año Y (year_to_int nulo O year_to_int >= año)
   💡 Permiso campo B

7. MOTOR — si quedan varios. Usa engine_all para matching (contiene TODOS los motores de cada fila, separados por |).
   El usuario puede mencionar un motor secundario que aparece en engine_all pero no en engine_clean — igualmente es válido.
   Muestra opciones reales de engine_all.

8. COMPONENTE — agrupa por tipo. Muestra opciones reales de nom_opcio_compressor.
   El usuario puede escribir de forma abreviada: TM15=TM 15/QP 15, TM13=TM 13/QP 13, etc.

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

// Map user input to exact DB component names
function normalizeComponent(text) {
  const compMap = [
    [/TM\s*43/i, 'TM 43'],
    [/TM\s*31/i, 'TM 31 / QP 31'],
    [/TM\s*21/i, 'TM 21 / QP 21'],
    [/TM\s*16/i, 'TM 16 / QP 16'],
    [/TM\s*15/i, 'TM 15 / QP 15'],
    [/TM\s*13/i, 'TM 13 / QP 13'],
    [/TM\s*08|TM\s*8\b/i, 'TM 08 / QP 08'],
    [/QP\s*25/i, 'QP 25'],
    [/UP\s*170|UPF\s*170/i, 'UP 170 / UPF 170'],
    [/UP\s*150|UPF\s*150/i, 'UP 150 / UPF 150'],
    [/UP\s*120|UPF\s*120/i, 'UP 120 / UPF 120'],
    [/UPF\s*200/i, 'UPF 200'],
    [/UP\s*90/i, 'UP 90'],
    [/SD7H15/i, 'SD7H15'],
    [/SD7L15/i, 'SD7L15'],
    [/SD5H14/i, 'SD5H14'],
    [/SD5L14/i, 'SD5L14'],
    [/SD5H09/i, 'SD5H09'],
    [/CS\s*150/i, 'CS150'],
    [/CS\s*90/i, 'CS90'],
    [/CS\s*55/i, 'CS55'],
    [/CR\s*150/i, 'CR150'],
    [/CR\s*90/i, 'CR90'],
    [/SALAMI/i, 'SALAMI'],
    [/SALAMI\s*16|16\s*cc/i, '16 cc SALAMI'],
    [/SALAMI\s*12|12\s*cc/i, '12 cc SALAMI'],
    [/SALAMI\s*8|8\s*cc/i, '8 cc SALAMI'],
    [/MG\s*29|Mahle.*200A|200A.*14V/i, 'Mahle MG 29 (200A 14V)'],
    [/MG\s*142|Mahle.*100A|100A.*28V/i, 'Mahle MG 142 (100A 28V)'],
    [/Valeo|140A\s*14V/i, 'Valeo 140A 14V'],
    [/SEG|150A\s*28V/i, 'SEG 150A 28V'],
    [/G4.*400|400V.*G4/i, 'Generator "G4-400V"'],
    [/G4.*230|230V.*G4/i, 'Generator "G4-230V"'],
    [/G3.*400|400V.*G3/i, 'Generator "G3-400V"'],
    [/G3.*230|230V.*G3/i, 'Generator "G3-230V"'],
    [/HPI\s*15/i, 'HPI 15cc'],
    [/HPI\s*12/i, 'HPI 12cc'],
    [/HPI\s*8/i, 'HPI 8cc'],
    [/TK.?315/i, 'TK-315'],
    [/TK.?312/i, 'TK-312'],
    [/BITZER/i, 'BITZER 4UFC'],
    [/BOCK/i, 'BOCK FK40'],
    [/Xarios/i, 'Xarios Integrated'],
  ];
  for (const [re, name] of compMap) {
    if (re.test(text)) return name;
  }
  return null;
}

function extractState(messages) {
  const text = messages.map(m => typeof m.content === 'string' ? m.content : '').join(' ');
  const s = {};

  // Kit type
  if (/compresor\s*a\/c|\bkb\b/i.test(text)) s.kit_type = 'Kit compresor A/C';
  else if (/fr[ií]o\s*industrial|\bkc\b/i.test(text)) s.kit_type = 'Kit compresor frío industrial';
  else if (/alternador|\bka\b/i.test(text)) s.kit_type = 'Kit alternador';
  else if (/bomba\s*hidráulica|\bkh\b/i.test(text)) s.kit_type = 'Kit bomba hidráulica';
  else if (/generador|\bkg\b/i.test(text)) s.kit_type = 'Kit generador';
  else if (/chasis|\bkf\b/i.test(text)) s.kit_type = 'Kit chasis';

  // Brand
  const brandMap = [
    [/sprinter|vito|actros|atego|arocs|antos|axor|econic/i, 'MERCEDES'],
    [/ducato|scudo|talento|doblò|doblo/i, 'FIAT'],
    [/transit|tourneo/i, 'FORD'],
    [/\bmaster\b|trafic|kangoo/i, 'RENAULT'],
    [/\bdaily\b|eurocargo|stralis|trakker/i, 'IVECO'],
    [/\bboxer\b|expert|partner/i, 'PEUGEOT'],
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
  if (/nuevo|reciente|nueva\s*matriculaci|es\s*nuevo|si.*nuevo/i.test(text)) s.new_vehicle = true;

  // Year - only if not new vehicle
  if (!s.new_vehicle) {
    const ym = text.match(/\b(19[89]\d|20[012]\d)\b/);
    if (ym) s.year = parseInt(ym[1]);
  }

  // Component - use normalized name
  s.component = normalizeComponent(text);

  return s;
}

async function queryDB(s) {
  const parts = [
    'brand=neq.ACCESSORY',
    'kit_type=neq.Otro',
    'model_clean=neq.STANDARD%20BRACKET',
    'model_clean=neq.COMPRESSOR%20BRACKET',
    'limit=150',
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

  // Use exact normalized component name
  if (s.component) {
    parts.push(`nom_opcio_compressor=eq.${encodeURIComponent(s.component)}`);
  }

  const url = `${SUPABASE_URL}/rest/v1/kits?${parts.join('&')}`;
  const r = await fetch(url, {
    headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
  });
  if (!r.ok) throw new Error(`DB ${r.status}`);
  return r.json();
}

function buildContext(data, state) {
  if (!data || data.length === 0) return '[BD: Sin resultados para los filtros actuales]';

  const byCode = {};
  for (const row of data) {
    if (!byCode[row.code]) byCode[row.code] = row;
  }
  const codes = Object.values(byCode);
  const uniq = arr => [...new Set(arr.filter(Boolean))];

  // Always send summary
  const summary = {
    total_codes: codes.length,
    models: uniq(codes.map(r => r.model_clean)),
    engines: uniq(codes.map(r => r.engine_clean)),
    components: uniq(data.map(r => r.nom_opcio_compressor)),
    tractions: { rwd: codes.filter(r=>r.flag_rwd==='Yes').length, fwd: codes.filter(r=>r.flag_fwd==='Yes').length },
    new_vehicle_filter: state.new_vehicle || false,
    active_filters: state,
  };

  // Send full detail only when ≤8 codes
  if (codes.length <= 8) {
    const detail = codes.map(r => ({
      code: r.code,
      model: r.model_clean,
      engine: r.engine_clean,
      engine_all: r.engine_all||null,
      year_from_v4: r.year_from_v4,
      year_to_v4: r.year_to_v4 || null,
      components: uniq(data.filter(d=>d.code===r.code).map(d=>d.nom_opcio_compressor)),
      flag_rwd: r.flag_rwd||null, flag_fwd: r.flag_fwd||null, flag_awd: r.flag_awd||null,
      flag_auto_tensioner: r.flag_auto_tensioner||null,
      flag_n63_pulley_yes: r.flag_n63_pulley_yes||null,
      flag_n63_pulley_no: r.flag_n63_pulley_no||null,
      flag_n63_full_option: r.flag_n63_full_option||null,
      flag_pfmot_yes: r.flag_pfmot_yes||null, flag_pfmot_no: r.flag_pfmot_no||null,
      flag_urban_kit: r.flag_urban_kit||null, flag_ind_belt: r.flag_ind_belt||null,
      flag_sanden: r.flag_sanden||null, flag_gearbox_v3: r.flag_gearbox_v3||null,
      flag_himatic: r.flag_himatic||null, flag_not_18t: r.flag_not_18t||null,
      ac_filter: r.ac_filter||null,
      noteeng: r.noteeng_clean||null,
      embrague_esp: r.embrague_esp||null,
      embrague_std: r.embrague_std||null,
      tipus_embrague: r.tipus_embrague||null,
    }));
    return `[BD Resumen: ${JSON.stringify(summary)}]\n[BD Detalle ${codes.length} códigos: ${JSON.stringify(detail)}]`;
  }

  return `[BD Resumen: ${JSON.stringify(summary)}]`;
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };
  const API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!API_KEY) return { statusCode: 500, body: JSON.stringify({ error: 'API key no configurada' }) };

  try {
    const body = JSON.parse(event.body);
    const messages = body.messages || [];
    const state = extractState(messages);

    let ctx = '[BD: Sin datos aún]';
    try {
      const data = await queryDB(state);
      ctx = buildContext(data, state);
    } catch(e) {
      console.error('DB:', e.message);
      ctx = `[BD Error: ${e.message}]`;
    }

    const msgsWithCtx = [...messages];
    const last = msgsWithCtx[msgsWithCtx.length - 1];
    msgsWithCtx[msgsWithCtx.length - 1] = {
      ...last,
      content: (typeof last.content === 'string' ? last.content : '') + '\n\n' + ctx
    };

    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': API_KEY, 'anthropic-version': '2023-06-01' },
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
