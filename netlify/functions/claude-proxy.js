const SUPABASE_URL = "https://wuizpohykpvppmydfcng.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind1aXpwb2h5a3B2cHBteWRmY25nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyNDI1NDQsImV4cCI6MjA5MjgxODU0NH0.xFLEDRLmpvjR1oFZE9TetyT8706W_BQPr7vTrNR9sj8";

const SYSTEM_PROMPT = `Eres un asistente comercial experto en selección de kits para vehículos de frío industrial y furgonetas.

ESTILO DE RESPUESTA — MUY IMPORTANTE:
- Responde en texto natural y conversacional. NUNCA uses títulos con ## o ###.
- No muestres "PASO X" ni estructuras de pasos. Habla como un experto comercial.
- Sé conciso y directo. Máximo 3-4 líneas por respuesta salvo cuando muestres opciones.
- Usa formato de lista solo para mostrar opciones de selección.
- Cuando confirmes un dato del usuario, di "✓ [dato]" brevemente y pasa a la siguiente pregunta.
- Para la selección final usa exactamente este formato:
  ✅ **Referencia seleccionada: [CODE]**
  Motivo: [modelo] · [motor] · [desde año] · [componente] · [diferencial si aplica]

REGLAS DE DATOS:
- Solo recomiendas códigos que existan en los datos proporcionados en cada mensaje.
- No inventas productos, referencias ni datos técnicos.
- Una sola pregunta por turno, nunca dos preguntas seguidas.
- Si algo no está en los datos disponibles, dilo claramente.
- Excluye siempre STANDARD BRACKET y COMPRESSOR BRACKET salvo petición explícita.

DEFINICIÓN DE "VEHÍCULO NUEVO":
- Un vehículo nuevo = usar SOLO los kits que tienen year_to_int NULO (sin fecha de fin).
- Estos kits están vigentes y son aplicables a cualquier vehículo actual, independientemente del año de inicio (year_from_int).
- NO filtres por year_from_int cuando el usuario dice "vehículo nuevo". Filtra SOLO por year_to_int nulo.
- Los datos ya llegan pre-filtrados con esta lógica desde el servidor.

FLUJO DE SELECCIÓN (sigue este orden, detente cuando quede 1 código único):

1. TIPO DE KIT — Primera pregunta siempre. Opciones:
   · Kit compresor A/C (KB) — aire acondicionado de cabina
   · Kit compresor frío industrial (KC) — frío de transporte
   · Kit alternador (KA) — alternador auxiliar
   · Kit bomba hidráulica (KH) — bomba hidráulica
   · Kit generador (KG) — generador eléctrico
   · Kit chasis (KF) — adaptación de chasis

2. MARCA — Pide la marca del vehículo.
   💡 España/UE: Permiso de circulación, campo D.1 Marca

3. MODELO — Muestra 4-8 opciones reales del campo model_clean de los datos.
   💡 España/UE: Permiso, campos D.2 Tipo y D.3 Denominación comercial

4. TRACCIÓN — Pregunta inmediatamente después de confirmar el modelo si los datos tienen variantes RWD/FWD:
   "¿El vehículo es de tracción trasera (RWD) o delantera (FWD)?"
   Usa flag_rwd y flag_fwd para filtrar. Si solo hay una opción de tracción en los datos, omite esta pregunta.
   💡 Inspección física bajo el vehículo, o campo Variante del permiso de circulación

5. ¿VEHÍCULO NUEVO? — Después de confirmar modelo y tracción:
   "¿Es un vehículo de matriculación reciente (nuevo)?"
   Si SÍ: usa SOLO los kits con year_to_int NULO de los datos (vigentes sin fecha de fin).
   Si NO: pide el año exacto.

6. AÑO — Solo si el usuario NO dijo "nuevo". Pregunta: "¿Sabes el año de fabricación o primera matriculación?"
   Filtra: year_from_int <= año Y (year_to_int nulo O year_to_int >= año)
   💡 España/UE: Permiso, campo B. Fecha de primera matriculación

7. MOTOR — Si todavía quedan varios candidatos, pregunta por el motor.
   Muestra opciones reales del campo engine_clean.
   💡 España/UE: Permiso campo P.5 o etiqueta en tapa de válvulas

8. COMPONENTE — Pregunta qué compresor/componente necesita.
   Agrupa por tipo con ejemplos reales de nom_opcio_compressor.

9. FLAGS DE KIT — Solo si varían entre candidatos. Orden de prioridad:
   a. flag_gearbox_v3: ok=compatible automática, not=NO compatible, vacío=válido para ambas → NO preguntar si todos vacíos
   b. flag_auto_tensioner → "¿Tensor automático o estándar?"
   c. flag_pfmot_yes/no → "¿Tiene opción PTO/PFMot de fábrica?"
   d. flag_urban_kit → "¿Opera en entorno urbano o alta temperatura?"
   e. flag_ind_belt → "¿Kit con correa independiente?"
   f. flag_n63_pulley_yes/no + flag_n63_full_option → "¿Lleva polea cigüeñal N62/N63?"
   g. flag_sanden → "¿El compresor original es SANDEN?"
   h. Resto de flags si siguen quedando candidatos

10. A/C — Solo si ac_filter varía y hay mix de yes/no:
    "¿Tiene aire acondicionado de fábrica?"
    (ac_filter=any → NO preguntar, siempre válido)

SELECCIÓN FINAL cuando queda 1 código:
✅ **Referencia seleccionada: [CODE]**
Motivo: [modelo] · [motor] · [desde year_from_v4] · [componente] · [diferencial]

📋 Notas importantes: (solo si hay datos relevantes en noteeng para el instalador)
· [nota 1]

🔧 Opción con embrague [estándar/especial]: (solo si embrague_esp no está vacío)
[contenido de embrague_esp]
¿Quieres la versión con embrague?

Si hay 1 código pero varios componentes disponibles:
✅ **Código seleccionado: [CODE]**
Componentes disponibles:
· [nom_opcio_compressor 1]
· [nom_opcio_compressor 2]
¿Cuál necesitas?`;

async function querySupabase(params) {
  const parts = [
    `brand=neq.ACCESSORY`,
    `kit_type=neq.Otro`,
    `model_clean=neq.STANDARD%20BRACKET`,
    `model_clean=neq.COMPRESSOR%20BRACKET`,
    `limit=200`
  ];

  if (params.kit_type) parts.push(`kit_type=eq.${encodeURIComponent(params.kit_type)}`);
  if (params.brand) parts.push(`brand=eq.${encodeURIComponent(params.brand)}`);
  if (params.model_clean) parts.push(`model_clean=eq.${encodeURIComponent(params.model_clean)}`);
  if (params.engine_clean) parts.push(`engine_clean=eq.${encodeURIComponent(params.engine_clean)}`);

  // NEW VEHICLE LOGIC: filter year_to_int IS NULL (open-ended, vigent kits)
  if (params.new_vehicle) {
    parts.push(`year_to_int=is.null`);
  } else if (params.year) {
    // Normal year filter
    parts.push(`year_from_int=lte.${params.year}`);
    parts.push(`or=(year_to_int.is.null,year_to_int.gte.${params.year})`);
  }

  if (params.nom_opcio_compressor) {
    parts.push(`nom_opcio_compressor=ilike.*${encodeURIComponent(params.nom_opcio_compressor)}*`);
  }
  if (params.flag_rwd) parts.push(`flag_rwd=eq.Yes`);
  if (params.flag_fwd) parts.push(`flag_fwd=eq.Yes`);

  const url = `${SUPABASE_URL}/rest/v1/kits?${parts.join('&')}`;
  const resp = await fetch(url, {
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`
    }
  });
  if (!resp.ok) throw new Error(`Supabase ${resp.status}`);
  return resp.json();
}

function extractParams(messages) {
  const text = messages.map(m => typeof m.content === 'string' ? m.content : '').join(' ');
  const lower = text.toLowerCase();
  const params = {};

  // Kit type
  if (/compresor a\/c|kb\b/i.test(text)) params.kit_type = 'Kit compresor A/C';
  else if (/fr[ií]o industrial|kc\b/i.test(text)) params.kit_type = 'Kit compresor frío industrial';
  else if (/alternador|ka\b/i.test(text)) params.kit_type = 'Kit alternador';
  else if (/bomba|kh\b/i.test(text)) params.kit_type = 'Kit bomba hidráulica';
  else if (/generador|kg\b/i.test(text)) params.kit_type = 'Kit generador';
  else if (/chasis|kf\b/i.test(text)) params.kit_type = 'Kit chasis';

  // Brand detection
  const brandMap = {
    'sprinter|vito|actros|atego|arocs|antos|axor|econic': 'MERCEDES',
    'ducato|scudo|talento|doblo': 'FIAT',
    'transit|tourneo': 'FORD',
    'master|trafic|kangoo': 'RENAULT',
    'daily|eurocargo|stralis|trakker': 'IVECO',
    'boxer|expert|partner': 'PEUGEOT',
    'jumper|jumpy|berlingo': 'CITROEN',
    'crafter|transporter|caddy': 'VW',
    'movano|vivaro|combo': 'OPEL',
    'nv400|nv300|interstar|primastar': 'NISSAN',
    'tgl|tgm|tgs|tgx': 'MAN',
    'canter|fuso': 'MITSUBISHI',
    'promaster': 'FIAT',
  };
  for (const [pattern, brand] of Object.entries(brandMap)) {
    if (new RegExp(pattern, 'i').test(text)) { params.brand = brand; break; }
  }
  for (const b of ['RENAULT','FIAT','IVECO','FORD','MERCEDES','VW','OPEL','NISSAN','PEUGEOT','CITROEN','MAN','DAF','VOLVO','TOYOTA','MITSUBISHI']) {
    if (lower.includes(b.toLowerCase())) { params.brand = b; break; }
  }

  // Year
  const yearMatch = text.match(/\b(19[89]\d|20[012]\d)\b/);
  if (yearMatch) params.year = parseInt(yearMatch[1]);

  // Traction
  if (/\brwd\b|tracci[oó]n trasera|rear wheel/i.test(text)) params.flag_rwd = true;
  if (/\bfwd\b|tracci[oó]n delantera|front wheel/i.test(text)) params.flag_fwd = true;

  // New vehicle — key logic change: just flag it, query will use year_to_int IS NULL
  if (/veh[ií]culo nuevo|es nuevo|si.*nuevo|nuevo.*si|matriculaci[oó]n reciente|nuevo.*matricul|reciente/i.test(text)) {
    params.new_vehicle = true;
    params.year = null; // clear year filter when new vehicle
  }

  // Component
  const compMatch = text.match(/\b(TM\s*\d+|UP\s*\d+|SD[57][HL]\d+|CS\s*\d+|QP\s*\d+|MG\s*\d+|Mahle|Valeo|SEG|SALAMI|G[34]-[24])/i);
  if (compMatch) params.nom_opcio_compressor = compMatch[1];

  return params;
}

exports.handler = async function(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'Method Not Allowed' };

  const API_KEY = process.env.ANTHROPIC_API_KEY;
  if (!API_KEY) return { statusCode: 500, body: JSON.stringify({ error: 'API key no configurada en Netlify' }) };

  try {
    const body = JSON.parse(event.body);
    const messages = body.messages || [];

    const params = extractParams(messages);
    let dbData = [];
    try {
      dbData = await querySupabase(params);
    } catch(e) {
      console.error('Supabase error:', e.message);
    }

    const dataContext = dbData.length > 0
      ? `\n\n[DATOS BD: ${dbData.length} registros filtrados. Filtros activos: ${JSON.stringify(params)}]\n${JSON.stringify(dbData)}`
      : `\n\n[DATOS BD: Sin filtros suficientes aún — inicia el flujo de selección]`;

    const msgsWithCtx = [...messages];
    if (msgsWithCtx.length > 0) {
      const last = msgsWithCtx[msgsWithCtx.length - 1];
      msgsWithCtx[msgsWithCtx.length - 1] = {
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
        max_tokens: 1000,
        system: SYSTEM_PROMPT,
        messages: msgsWithCtx
      })
    });

    const data = await resp.json();
    if (!resp.ok) return {
      statusCode: resp.status,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: data.error?.message || 'Error API' })
    };

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    };

  } catch(err) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: err.message })
    };
  }
};
