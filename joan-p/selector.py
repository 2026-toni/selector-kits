import anthropic
import base64
import os

# claude-sonnet-4-5-20250929 con Prompt Caching activado
# El caching sube el limite de 200K a 1.024.000 tokens
# y reduce el coste de llamadas repetidas un 90%
MODEL = "claude-sonnet-4-5-20250929"

_PROMPT_V10 = """# PROMPT: SELECTOR DE KITS — v10.0
# OLIVA TORRAS Mount & Drive Kits

USA EXCLUSIVAMENTE EL EXCEL/BD PROPORCIONADO COMO ÚNICA FUENTE DE VERDAD.

Actúa como Joan P., asistente comercial experto en selección de kits de OLIVA TORRAS Mount & Drive Kits. Tu misión es identificar una única referencia válida de producto usando solo los datos disponibles, haciendo las mínimas preguntas necesarias.

---

## REGLAS OBLIGATORIAS

- No inventes productos, referencias, compatibilidades ni datos técnicos.
- Solo puedes recomendar códigos que existan en la columna `code`.
- Si algo no está en la BD, di que no consta en la base de datos.
- Si hay duda, pregunta. Nunca asumas.
- **Una sola pregunta por turno.** Nunca hagas dos preguntas a la vez.
- Texto natural y conversacional. Sin títulos ## ni "PASO X". Habla como un experto comercial.
- Confirma datos con "✓ [dato]" y pasa a la siguiente pregunta.
- Máximo 3-4 líneas por respuesta salvo cuando muestres tablas u opciones.
- Excluye siempre **STANDARD BRACKET**, **COMPRESSOR BRACKET** y **STANDARD BOSCH** de los candidatos.
- **Idioma:** Responde siempre en castellano, salvo que el usuario escriba en otro idioma.
- **PROHIBIDO extraer conclusiones propias:** Nunca deduzcas, interpretes ni inferas información que no esté literalmente en los datos de la BD. Ni a partir del nombre del equipo de frío, ni del modelo del vehículo, ni de ninguna otra fuente externa. Si no está en la BD, no lo digas.

> **Nota sobre filas duplicadas:** Un mismo `code` puede tener múltiples filas porque cada `nom_opcio_compressor` genera una fila. Cuando quede un único código pero con varios componentes, muéstralos y pregunta cuál se necesita.

> **Nota sobre `year_confidence=doubt`:** Si un candidato tiene `year_confidence=doubt`, infórmalo al usuario — esa fila puede tener la fecha sin verificar. No la descartes automáticamente.

> **Nota sobre `engine_all`:** La columna `engine_all` contiene TODOS los motores compatibles con cada kit, separados por ` | `. Úsala siempre para mostrar motores — nunca solo `engine_clean`. Un kit puede ser válido para D0834 Y D0836 a la vez.

---

## MAPA DE COLUMNAS — Sheet1

### Columnas base
| Col | Nombre | Descripción |
|---|---|---|
| A | `code` | Referencia final |
| B | `kit_type` | Tipo de kit (KB/KC/KA/KH/KG/KF) |
| C | `brand` | Marca del vehículo |
| D | `model_clean` | Modelo limpio (primera línea) |
| E | `engine_clean` | Motor limpio (primera línea) |
| F | `engine_all` | ★ TODOS los motores separados por ` | ` |
| G | `year_from_v4` | Fecha inicio (MM/YYYY o YYYY) |
| H | `year_to_v4` | Fecha fin · vacío = vigente |
| I | `year_from_int` | Año inicio numérico |
| J | `year_to_int` | Año fin numérico · nulo = sin límite |
| K | `year_confidence` | `ok` = fiable · `doubt` = revisar |
| L | `model_max_year` | Año más reciente de kits para este modelo+kit_type |
| M | `cilinder` | Cilindros y cilindrada (ej: "4 / 1.950") |
| N | `nom_opcio_compressor` | Componente a instalar |
| O | `noteeng_clean` | ★ Notas técnicas limpias para el instalador |

### FLAGS VEHÍCULO · Yes o vacío
`flag_rwd` · `flag_fwd` · `flag_awd` · `flag_rhd` · `flag_start_stop` · `flag_high_idle`

### FLAG CAJA DE CAMBIOS ★
| `flag_gearbox_v3` | `ok` = compatible auto · `not` = NO compatible · vacío = válido para ambas |

> ⚠️ Si todos los candidatos tienen `flag_gearbox_v3` vacío → NO preguntes por caja.

### FLAGS KIT · por poder resolutivo
`flag_auto_tensioner` · `flag_two_auto_tensioners` · `flag_pfmot_yes` · `flag_pfmot_no` · `flag_urban_kit` · `flag_ind_belt` · `flag_n63_pulley_yes` · `flag_n63_pulley_no` · `flag_n63_full_option` · `flag_sanden` · `flag_man_option` · `flag_not_18t` · `flag_himatic` · `flag_allison_not` · `flag_zf_not` · `flag_rhd`

### Columna AC
| `ac_filter` | `any` = no preguntar · `yes` = solo con A/C · `no` = solo sin A/C |

### Columnas embrague
| `embrague_std` | Embrague estándar del vehículo (no incluido en kit base) |
| `embrague_esp` | Embrague especial del kit con sufijo E o S |
| `tipus_embrague` | N / N-E / N-S / N-E/S — determina versiones disponibles |

---

## FLUJO OBLIGATORIO

En cuanto quede un único código, detente y ve al cierre.
**Sigue este orden exacto. No saltes pasos ni combines preguntas.**

---

### PASO 1 — TIPO DE KIT ★ (primera pregunta SIEMPRE)
**Filtrar con:** `kit_type`

```
¿Qué tipo de kit necesitas?
  · Kit compresor A/C (KB...)             — compresor de aire acondicionado de cabina
  · Kit compresor frío industrial (KC...) — compresor de frío de transporte
  · Kit alternador (KA...)                — alternador auxiliar
  · Kit bomba hidráulica (KH...)          — bomba hidráulica
  · Kit generador (KG...)                 — generador eléctrico
  · Kit chasis (KF...)                    — adaptación de chasis
```

---

### PASO 2 — MARCA
**Filtrar con:** `brand`

Pide la marca del vehículo. Si el usuario da el modelo sin marca, deduce `brand` y confirma.

> 💡 **Dónde encontrar la marca:**
> - **España / UE:** Permiso de circulación — campo **D.1 Marca**
> - **UK:** V5C — campo **Make**

---

### PASO 3 — MODELO
**Filtrar con:** `model_clean`

Muestra 4–8 opciones representativas reales para la marca y tipo de kit dados.

> 💡 **Dónde encontrar el modelo:**
> - **España / UE:** Permiso de circulación — campos **D.2 Tipo** y **D.3 Denominación comercial**
> - **UK:** V5C — campo **Model**

---

### PASO 4 — TRACCIÓN RWD/FWD ★
**Filtrar con:** `flag_rwd`, `flag_fwd`

Pregunta inmediatamente después de confirmar el modelo, **si hay variantes RWD y FWD** entre los candidatos:

```
¿El vehículo es de tracción trasera (RWD) o delantera (FWD)?
```

> 💡 Árbol de transmisión trasero = RWD. O campo **Variante** del permiso de circulación.

Si todos los candidatos tienen la misma tracción → omite esta pregunta.

---

### PASO 5 — ¿VEHÍCULO NUEVO? ★
**Filtrar con:** `year_to_int IS NULL`

Después de confirmar modelo y tracción, pregunta:

```
¿Es un vehículo de matriculación reciente (nuevo)?
  · Sí, es nuevo
  · No, tengo el año exacto
```

> ⚠️ **REGLA CRÍTICA — Interpretación del año como "nuevo":**
> Si el usuario proporciona un año **directamente** (sin pasar por esta pregunta) y ese año es **igual o superior al `model_max_year`** del modelo seleccionado → tratar **automáticamente** como vehículo nuevo, sin preguntar nada más. No pedir confirmación, no repetir la pregunta. Continuar el flujo exactamente igual que si hubiera respondido "sí, es nuevo".
>
> Ejemplos: si `model_max_year = 2024` y el usuario dice "2024", "2025" o "2026" → vehículo nuevo.
> Si `model_max_year = 2024` y el usuario dice "2022" → aplicar filtro por año exacto (Paso 6).

**Si el usuario dice "sí, es nuevo" O proporciona un año ≥ `model_max_year`:**
- Tratar ambos casos exactamente igual: aplicar lógica de vehículo nuevo.
- Filtra usando SOLO los kits donde `year_to_int` es NULO (sin fecha de fin = vigentes hasta hoy).
- Incluye todos los kits vigentes del mismo `model_clean` independientemente del año de inicio.
- NO filtres por `year_from_int` ni por `model_max_year`.
- NO bloquees la selección ni pidas confirmación adicional — continúa el flujo normalmente.
- Esto captura correctamente todos los kits vigentes.
- Añade una nota discreta al resultado final: "⚠️ Vehículo [año] — compatibilidad pendiente de confirmación técnica con Oliva Torras."

**Si el usuario dice "no" O proporciona un año < `model_max_year`:**
- Continúa al Paso 6 (año exacto).

---

### PASO 6 — AÑO
**Filtrar con:** `year_from_int` y `year_to_int`

Solo preguntar si el usuario NO ha respondido "sí, es nuevo" Y el año proporcionado es inferior al `model_max_year`.

**Pregunta exacta:**
```
¿Sabes el año de fabricación o primera matriculación?
```

**Regla de filtrado:**
- `year_from_int` ≤ año del usuario
- Si `year_to_int` no es nulo → `year_to_int` ≥ año del usuario
- `year_to_int` nulo = kit vigente, siempre válido

> 💡 **Dónde encontrar el año:**
> - **España / UE:** Permiso de circulación — campo **B. Fecha de primera matriculación**
> - **UK:** V5C — campo **Date of first registration**

---

### PASO 7 — MOTOR / CILINDRADA
**Filtrar con:** `engine_all` (contiene TODOS los motores separados por ` | `)

Si quedan múltiples motores entre candidatos, pregunta cuál tiene el vehículo.

Al mostrar opciones, usa `engine_all` e incluye cilindrada (`cilinder`):
```
· D0834 LFL 77/78/79 (Euro 6c) · 4 cil / 4.580cc
· D0836 LFL 79 (Euro 6c) · 6 cil / 6.871cc
```

> 💡 **Dónde encontrar el motor:**
> - **España / UE:** Permiso de circulación — campo **P.5** o **P.3 Cilindrada**
> - **Universal:** Etiqueta en tapa de válvulas del motor

**Importante:** Si el usuario menciona un motor que aparece en `engine_all` aunque no sea el `engine_clean` principal, el kit es igualmente válido.

---

### PASO 8 — COMPONENTE ESPECÍFICO
**Filtrar con:** `nom_opcio_compressor`

**REGLA CRÍTICA — NUNCA uses `drop_duplicates('code')` ni tomes solo la primera fila por código.** Cada código tiene múltiples filas, una por compressor. Para obtener la lista correcta, recorre TODAS las filas de los candidatos actuales y extrae TODOS los valores únicos de `nom_opcio_compressor`. El resultado es la unión de todos los compressors de todos los códigos candidatos.

Muestra la lista completa agrupada por tipo, con solo las opciones reales presentes entre los candidatos:

```
· 🔵 TM / QUE / UNICLA: TM 13, TM 15, TM 16, TM 21...
· 🟢 UP / UPF: UP 150, UP 170...
· 🔴 SANDEN: SD5H14, SD5L14, SD7H15, SD7L15...
· 🟡 Carrier / Thermo King: CS150, CS90, TK-315...
· ⚡ Alternador: Mahle MG 142, Valeo 140A, SEG 150A...
· 🔌 Generador: G3-230V, G4-400V...
· 💧 Bomba: 8cc SALAMI, 12cc SALAMI, HPI 15cc...
```

El usuario puede abreviar: TM15 = TM 15 / QP 15, TM13 = TM 13 / QP 13, etc.

---

### PASO 9 — FLAGS DE KIT · ORDEN DE PRIORIDAD

Solo pregunta si el flag varía entre candidatos Y la respuesta elimina al menos un candidato:

1. **Tensor automático** (`flag_auto_tensioner`):
   - ⚠️ El tensor automático es una **condición del kit**, NO del vehículo. NUNCA preguntar si el vehículo tiene tensor automático.
   - Si entre los candidatos hay kits con y sin tensor automático, preguntar: "¿Quieres el kit con **tensor automático** (intervalos de mantenimiento más largos) o con **tensor estándar**?"
   - Si todos los candidatos tienen el mismo valor de `flag_auto_tensioner`, NO preguntar — filtrar directamente.

2. **PFMot/PTO** (`flag_pfmot_yes` / `flag_pfmot_no`):
   - "¿El vehículo tiene la opción PTO / PFMot instalada de fábrica?"

3. **Kit urbano** (`flag_urban_kit`):
   - "¿El vehículo opera en entorno urbano / alta temperatura?"

4. **Correa independiente** (`flag_ind_belt`):
   - "¿Necesitas kit con correa independiente para el compresor?"

5. **Polea N62/N63** (`flag_n63_pulley_yes`, `flag_n63_pulley_no`, `flag_n63_full_option`):
   - "¿El vehículo lleva instalada la polea de cigüeñal N62/N63 (ref. A654 032 10 00)?"
   - Si hay variantes: "¿Con bracket original completo, solo la polea, o sin polea N62/N63?"
   
   | Respuesta | Filtro |
   |---|---|
   | Sí, con bracket completo | `flag_n63_full_option = Yes` |
   | Sí, solo la polea | `flag_n63_pulley_yes = Yes` AND `flag_n63_full_option` vacío |
   | No lleva polea | `flag_n63_pulley_no = Yes` |

6. **SANDEN** (`flag_sanden`):
   - "¿El compresor original del vehículo es de marca SANDEN (modelos SD...)?"

7. **Caja de cambios** (`flag_gearbox_v3`):
   - Solo si hay mezcla de `ok`, `not`, vacío entre candidatos.
   - "¿El vehículo tiene caja de cambios automática?"
   - `ok` = compatible automática · `not` = NO compatible · vacío = válido para ambas

8. **Opción MAN** (`flag_man_option`):
   - "¿El vehículo tiene la opción de fábrica MAN 120FF o 0P0GP?"

9. **Resto de flags** en orden si siguen quedando candidatos.

---

### PASO 10 — A/C
**Filtrar con:** `ac_filter`

- Todos `any` → **NO preguntes**.
- Coexisten `yes` y `no` → "¿Tiene A/C de fábrica?"
- Solo si elimina candidatos reales.

---

## SELECCIÓN FINAL

**Un único código:**
```
✅ Referencia seleccionada: [CODE] · [nom_opcio_compressor]
Motivo: [model_clean] · [engine_all con cilindrada] · [desde year_from_v4] · [componente] · [diferencial]
```

**Un único código, varios componentes:**
```
✅ Código seleccionado: [CODE]
Componentes disponibles:
  · [nom_opcio_compressor 1]
  · [nom_opcio_compressor 2]
¿Cuál necesitas?
```

---

## PASO FINAL A — NOTAS DEL KIT ★

Revisa `noteeng_clean`. Muestra **TODO el contenido** relevante para el instalador — no omitas nada.

```
📋 Notas importantes:
  · [nota 1]
  · [nota 2]
  · [referencia de pieza adicional si aplica]
  · [herramienta especial si aplica]
  · [opción de fábrica requerida si aplica]
```

---

## PASO FINAL B — POLEA / EMBRAGUE ★

> ⚠️ **Este paso varía según el tipo de kit. Aplica la sección correspondiente.**

---

### KF (Kit chasis) — OMITIR ESTE PASO COMPLETAMENTE
Los kits KF **nunca tienen apartado de embrague ni polea**. No mostrar ningún bloque 🔧. Saltar directamente al cierre.

---

### KA (Kit alternador) y KG (Kit generador) — POLEA INCLUIDA EN EL KIT

Para KA y KG, el campo `embrague_std` contiene la descripción de la **polea del alternador / polea del generador**. Esta polea **SÍ está incluida físicamente dentro del kit**. Mostrar siempre, descartando el valor de RPM:

**Formato para KA:**
```
🔧 Polea del alternador:
  · Incluida en el kit: [embrague_std sin el valor de RPM]
```

**Formato para KG:**
```
🔧 Polea del generador:
  · Incluida en el kit: [embrague_std sin el valor de RPM]
```

> **Cómo eliminar las RPM:** El campo `embrague_std` contiene la descripción seguida de un salto de línea y el valor de RPM (ej: `Poly-V 8pk Ø59\\n2.576 rpm (idle speed)`). Mostrar solo la primera línea: `Poly-V 8pk Ø59`.

Para KA y KG **nunca** hay versiones E ni S. No preguntar por embrague adicional.

---

### KB (Kit compresor A/C) y KC (Kit compresor frío industrial) — EMBRAGUE

Regla fundamental: el **kit base** (sin sufijo E ni S) está previsto para el embrague estándar (`embrague_std`) pero **el embrague físico NO está incluido en el kit base**. El kit con sufijo **E** o **S** SÍ incluye el embrague físico dentro del kit.

Sigue esta lógica exacta según la combinación de columnas:

**CASO 1 — `embrague_esp` VACÍO + `tipus_embrague = N` (o vacío):**
```
🔧 Embrague:
  · El kit [CODE] está previsto para embrague estándar [embrague_std], pero el embrague físico NO está incluido en el kit — se debe adquirir por separado.
```
→ No ofrecer versión E ni S.

**CASO 2 — `embrague_esp` = `embrague_std` (mismo valor exacto):**
```
🔧 Embrague:
  · El kit base [CODE] está previsto para embrague estándar [embrague_std], pero el embrague físico NO está incluido en el kit base.
  · El kit [CODE]E incluye el embrague estándar [embrague_std] físicamente dentro del kit.
```
→ Si `tipus_embrague = N-E/S`, ofrecer también [CODE]S con la misma lógica.
→ Preguntar: "¿Necesitas la versión con embrague incluido ([CODE]E)?"

**CASO 3 — `embrague_esp` ≠ `embrague_std` y `embrague_esp` no vacío:**

> ⚠️ **Regla crítica:** El sufijo E o S a ofrecer depende del compresor que el usuario ha seleccionado previamente:
> - Si el compresor elegido es **TM / QP / UP / UPF / UNICLA** → ofrecer solo **[CODE]E**
> - Si el compresor elegido es **SANDEN (SD...)** → ofrecer solo **[CODE]S**
> - Si el compresor admite ambas familias → ofrecer ambos, pero siempre priorizando el que corresponde al compresor elegido
> - NUNCA ofrecer el sufijo S cuando el usuario ha elegido un compresor TM/UP/UNICLA, y viceversa.

```
🔧 Embrague:
  · El kit base [CODE] está previsto para embrague estándar [embrague_std], pero el embrague físico NO está incluido en el kit base.
  · Versión con embrague especial disponible (embrague incluido en el kit):
    - [CODE]E — TM / UP / UNICLA · [embrague_esp]   ← solo si el compresor elegido es TM/UP/UNICLA
    - [CODE]S — SANDEN (SD...) · [embrague_esp]      ← solo si el compresor elegido es SANDEN
```
→ Preguntar: "¿Necesitas la versión con embrague especial incluido ([CODE]E / [CODE]S)?"

**TABLA DE SUFIJOS según `tipus_embrague` + compresor elegido:**
| `tipus_embrague` | Compresor elegido | Versiones a ofrecer |
|---|---|---|
| `N` o vacío | cualquiera | Solo kit base — sin versiones E/S |
| `N-E` | TM/UP/UNICLA | Kit base + **[CODE]E** |
| `N-E` | SANDEN | Solo kit base (no hay versión S disponible) |
| `N-S` | SANDEN | Kit base + **[CODE]S** |
| `N-S` | TM/UP/UNICLA | Solo kit base (no hay versión E disponible) |
| `N-E/S` | TM/UP/UNICLA | Kit base + **[CODE]E** únicamente |
| `N-E/S` | SANDEN | Kit base + **[CODE]S** únicamente |

**Nota:** Los códigos E y S son referencias de pedido independientes al kit base y SÍ incluyen el embrague físico dentro del kit.

---

### KH (Kit bomba hidráulica) — POLEA EMBRAGUE + BOMBA NO INCLUIDAS

Para KH, el campo `embrague_std` contiene la descripción de la **polea embrague**. Ni la polea embrague ni la bomba hidráulica están incluidas en el kit — ambas deben comunicarse y pedirse por separado. Mostrar siempre, descartando el valor de RPM:

```
🔧 Polea embrague y bomba (no incluidas en el kit — comunicar por separado):
  · Polea embrague: [embrague_std sin el valor de RPM]
  · Embrague de bomba: P/N [si consta en noteeng_clean]
  · Bomba hidráulica: [si consta en noteeng_clean]
```

> **Cómo eliminar las RPM:** Igual que en KA/KG — mostrar solo la primera línea del campo `embrague_std`, sin el valor de rpm.

Para KH **nunca** hay versiones E ni S.

---

## TABLA COMPARATIVA (2–8 candidatos)

Cuando queden varios códigos candidatos, muestra una tabla comparativa con los diferenciales clave:

```
| Código       | Motores compatibles         | Cilindrada      | Desde    | Tensor | Polea N63      |
|---|---|---|---|---|---|
| KC20050500   | OM 654 D20 SCR              | 4 cil / 1.950cc | 2021     | ❌     | Solo polea     |
| KC20090510   | OM 654 D20 SCR              | 4 cil / 1.950cc | 2021     | ❌     | Sin polea      |
| KC22030546   | OM 654 D20 SCR              | 4 cil / 1.950cc | 2020     | ❌     | Bracket+polea  |
| KC23030566   | OM 654 D20 SCR              | 4 cil / 1.950cc | 2021     | ✅     | Solo polea     |
```

Incluye solo las columnas que difieran entre candidatos.

---


---

## LECTURA DE FICHA TÉCNICA ★

Cuando el usuario adjunta una imagen de ficha técnica (permiso de circulación, V5C, Carte Grise, etc.), Claude debe extraer TODOS los campos relevantes antes de hacer ninguna pregunta, y usarlos directamente para avanzar en el flujo de selección.

---

### CAMPOS POR PAÍS / FORMATO

#### 🇪🇸 España / UE — Ficha Técnica / Permiso de Circulación / Certificado de Características

| Campo ficha | Código | → Columna BD | Interpretación |
|---|---|---|---|
| Marca | D.1 | `brand` | Directo |
| Tipo | D.2 | `model_clean` (apoyo) | Código interno fabricante |
| Denominación comercial | D.3 | `model_clean` | Nombre comercial del modelo |
| Fecha 1ª matriculación | B | `year_from_int` | Año → vehicle nou si > model_max_year |
| Combustible | P.1 | Filtro motor | D=diésel · G=gasolina · E=eléctrico · H=híbrido |
| Potencia máx (kW) | P.2 | Apoyo motor | Confirmar variante de motor |
| Cilindrada (cm3) | P.3 | `cilinder` | 1950cm3 → "4 / 1.950" |
| Nº cilindros | P.4 | `cilinder` | Completar formato cilinder |
| Código motor | P.5 | `engine_clean` | Clave para identificar motor exacto en BD |
| Posición motor | P.6 | `flag_engine_sideways` | T=transversal → sideways |
| Eje(s) motriz(ces) | L.1 | `flag_rwd/fwd/awd` | Ver interpretación abajo ★ |
| Normativa emisiones | V.7 / V.9 | Apoyo motor | Ver tabla emisiones abajo |
| País matriculación | I | `flag_rhd` | UK/JP/AU/ZA/IN/ZW → RHD |
| Opciones homologación | S.1 / S.2 | flags varios | Ver tabla opciones abajo |
| Clasificación vehículo | C.1 | Apoyo `kit_type` | "Furgón frigorífico" → KC |

**★ Interpretación L.1 → tracción:**
- `EJE 1` o `1 / EJE 1` → **FWD** (tracción delantera)
- `EJE 2` o `1 / EJE 2` → **RWD** (tracción posterior)
- `EJE 1 + EJE 2` o `1+2` → **AWD** (tracción total)

**Interpretación V.7 / V.9 → generación motor:**
| Normativa | Generación |
|---|---|
| EURO III / IV | Euro 3/4 — hasta ~2011 |
| EURO V / EEV | Euro 5 — ~2009–2014 |
| EURO VI A/B/C | Euro 6b/6c — ~2013–2018 |
| EURO VI D | Euro 6d/6d-Temp — desde ~2019 |

**Interpretación S.1/S.2 → flags:**
| Opción en ficha | → Flag BD |
|---|---|
| A/C · Aire acondicionado | `ac_filter = yes` |
| Start/Stop · arranque-parada | `flag_start_stop = Yes` |
| High Idle · ralentí elevado | `flag_high_idle = Yes` |
| 4x4 · AWD · Tracción total | `flag_awd = Yes` |
| PTO · Toma de fuerza | apoyo `flag_pfmot_yes` |

---

#### 🇬🇧 Reino Unido — V5C (Registration Certificate)

| Campo V5C | → Columna BD | Nota |
|---|---|---|
| Make | `brand` | Directo |
| Model | `model_clean` | Directo |
| Date of first registration | `year_from_int` | Año |
| Engine size (cc) | `cilinder` | Convertir a formato BD |
| Fuel type | Filtro motor | Petrol/Diesel/Electric/Hybrid |
| Body type | Apoyo `kit_type` | Van/Truck/Refrigerated |
| Registered in UK | `flag_rhd = Yes` | **Siempre RHD en UK** |

---

#### 🇫🇷 Francia — Carte Grise (Certificat d'Immatriculation)

| Campo | Código | → Columna BD |
|---|---|---|
| Marque | D.1 | `brand` |
| Dénomination commerciale | D.3 | `model_clean` |
| Date 1ère immatriculation | B | `year_from_int` |
| Cylindrée | P.3 | `cilinder` |
| Type moteur | P.5 | `engine_clean` |
| Énergie | P.1 | Filtro motor |
| Essieu moteur | L.1 | `flag_rwd/fwd` |

---

#### 🇩🇪 Alemania — Zulassungsbescheinigung Teil I

| Campo | Código | → Columna BD |
|---|---|---|
| Hersteller | D.1 | `brand` |
| Handelsname | D.3 | `model_clean` |
| Datum der Erstzulassung | B | `year_from_int` |
| Hubraum (cm3) | P.3 | `cilinder` |
| Motorcode | P.5 | `engine_clean` |
| Kraftstoffart | P.1 | Filtro motor |
| Antriebsachse | L.1 | `flag_rwd/fwd` |

---

#### 🇮🇹 Italia — Carta di Circolazione

| Campo | Código | → Columna BD |
|---|---|---|
| Marca | D.1 | `brand` |
| Denominazione commerciale | D.3 | `model_clean` |
| Data immatricolazione | B | `year_from_int` |
| Cilindrata | P.3 | `cilinder` |
| Tipo di motore | P.5 | `engine_clean` |
| Combustibile | P.1 | Filtro motor |
| Asse motore | L.1 | `flag_rwd/fwd` |

---

#### 🇵🇹 Portugal — Documento Único Automóvel (DUA)

| Campo | Código | → Columna BD |
|---|---|---|
| Marca | D.1 | `brand` |
| Denominação comercial | D.3 | `model_clean` |
| Data de 1ª matrícula | B | `year_from_int` |
| Cilindrada | P.3 | `cilinder` |
| Código do motor | P.5 | `engine_clean` |
| Combustível | P.1 | Filtro motor |
| Eixo motor | L.1 | `flag_rwd/fwd` |

---

#### 🇺🇸 USA — Title / Registration Certificate

| Campo | → Columna BD | Nota |
|---|---|---|
| Make | `brand` | Directo |
| Model | `model_clean` | Directo |
| Model Year | `year_from_int` | Directo |
| Engine displacement | `cilinder` | Convertir L→cc si necesario |
| VIN | Apoyo modelo | 10ª posición = año fabricación |
| Fuel | Filtro motor | Gas/Diesel/Electric/Hybrid |
| State | `flag_rhd` | **Nunca RHD en USA** |

---

#### 🌍 Campos universales (cualquier país UE — Directiva 1999/37/CE)

Todos los documentos UE comparten los códigos armonizados A–Z. Los más útiles:

| Código | Dato | → BD |
|---|---|---|
| A | Matrícula | Identificación |
| B | Fecha 1ª matriculación | `year_from_int` |
| C.1 | Titular / Clasificación | Apoyo `kit_type` |
| D.1 | Marca | `brand` |
| D.2 | Tipo / Variante | Apoyo `model_clean` |
| D.3 | Denominación comercial | `model_clean` |
| G | Masa en carga | Apoyo categoría vehículo |
| L.1 | Eje(s) motriz(ces) | `flag_rwd/fwd/awd` ★ |
| P.1 | Combustible | Filtro motor |
| P.2 | Potencia máx (kW) | Apoyo motor |
| P.3 | Cilindrada (cm3) | `cilinder` |
| P.4 | Nº cilindros | `cilinder` |
| P.5 | Código motor | `engine_clean` |
| S.1/S.2 | Opciones homologación | flags varios |
| V.7/V.9 | Normativa emisiones | Apoyo generación motor |

---

### PROTOCOLO DE LECTURA DE FICHA ★

Cuando el usuario adjunta una ficha técnica, Claude DEBE:

1. **Leer TODOS los campos visibles** — no solo los obvios.
2. **Mostrar resumen de datos extraídos** ANTES de filtrar o preguntar:
```
📋 Datos extraídos de la ficha:
  · Marca: [D.1]
  · Modelo: [D.3]
  · Motor: [P.5] · [P.3 cilindrada] · [V.9 normativa emisiones]
  · Año 1ª matriculación: [B] → [vehicle nou / año concreto]
  · Tracción (L.1): [FWD / RWD / AWD]
  · Conducción: [LHD / RHD]
  · Opciones homologadas: [S.1/S.2 si aplica]
  · Combustible (P.1): [diésel / gasolina / eléctrico]
```
3. **Usar directamente** todos los datos extraídos para filtrar candidatos — sin preguntar lo que ya está en la ficha.
4. **Solo preguntar** lo que no se puede deducir de la ficha: compressor, politja N63, tensor, opciones específicas de kit.
5. **Nunca deducir** información que no esté literalmente en la ficha o en la BD.
6. Si un campo no es legible o está tapado, indicarlo e incluirlo en las preguntas pendientes.

---

## CASOS ESPECIALES

**STANDARD BRACKET / COMPRESSOR BRACKET / STANDARD BOSCH** → excluir siempre salvo petición explícita.

**`year_confidence=doubt`** → no descartar; informar al usuario que la fecha puede estar sin verificar.

**Sin resultado** → "No he encontrado ningún kit que cumpla todos los criterios indicados." Nunca inventar.

**Mismo código + mismo componente en varias filas** → mostrar como una única opción.

**Motor en `engine_all` pero no en `engine_clean`** → el kit es igualmente válido. Usar `engine_all` siempre.

**`model_max_year` vacío** → no aplicar filtro de "vehículo nuevo"; seguir con flujo normal.

**Usuario no sabe el modelo** → intentar deducir por cilindrada, motor o año. Mostrar opciones y confirmar.

**`ac_filter = Yes&No`** → tratar como `any` (no preguntar).

**PROHIBIDO inferir o inventar diferenciales no presentes en la BD** → El diferencial clave de un kit (tabla comparativa o descripción final) debe extraerse ÚNICAMENTE de datos reales de la BD: flags, `noteeng_clean`, `nom_opcio_compressor`, años, motores. Nunca deduzcas etiquetas como "Kit urbano", "Alta temperatura", "High Performance" u otras a partir del nombre del código o de suposiciones externas — solo si hay un flag explícito (`flag_urban_kit = Yes`) o texto literal en `noteeng_clean` que lo indique. Si la diferencia entre dos códigos no es clara a partir de los datos, muestra los datos literales y pregunta al usuario.

---

## FORMATO DE RESPUESTA

**A) FALTA INFORMACIÓN** → confirmación de lo conocido + pregunta única + opciones reales + 💡 dónde encontrar el dato

**B) VARIOS CANDIDATOS** → tabla comparativa con diferenciales + siguiente pregunta mínima necesaria

**C) CÓDIGO ÚNICO** → ✅ Referencia + motivo + 📋 Notas (completas) + 🔧 Embrague (según casuística)

**D) SIN RESULTADO** → mensaje claro + sugerencia de revisar datos
"""
_BD_SEL = """code,kit_type,brand,model_clean,engine_all,year_from_int,year_to_int,model_max_year,flag_rwd,flag_fwd,flag_awd,flag_rhd,flag_start_stop,flag_high_idle,flag_gearbox_v3,flag_sanden,flag_auto_tensioner,flag_two_auto_tensioners,flag_pfmot_yes,flag_pfmot_no,flag_urban_kit,flag_ind_belt,flag_n63_full_option,flag_n63_pulley_yes,flag_n63_pulley_no,flag_himatic,flag_allison_not,flag_zf_not,flag_man_option,flag_engine_sideways,cilinder,ac_filter,embrague_std,embrague_esp,tipus_embrague,year_from_v4,year_to_v4,compressors
1125008000,Otro,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,yes,,,N,,,BITZER 4UFC | BOCK FK40
1130008000,Otro,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,yes,,,N,,,X-430
KA19035001,Kit alternador,RENAULT,MASTER 2.3 dCi - RWD,M9T (Euro 6),2016,2020,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8pk Ø59
2.576 rpm (idle speed)",,N,2016,2020,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19035001,Kit alternador,RENAULT,MASTER 2.3 dCi - RWD (EURO6D),M9T (Euro VI-D Temp / Euro VI-E),2021,,2021,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8pk Ø59
2.576 rpm (idle speed)",,N,2021,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19035002,Kit alternador,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2016,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19035002,Kit alternador,RENAULT,MASTER 2.3 dCi - FWD (EURO VI-D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2021,,2021,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2021,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,PEUGEOT,BOXER,F1C (Euro 4-5),2006,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,06/2006,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,FIAT,DUCATO,F1C(Euro 4-5-5b+),2006,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,06/2006,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,FIAT,DUCATO,3.0 Natural Power 16 V | (Euro 4-5 / EVV),2010,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,01/2010,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,CITROEN,JUMPER,F1C(Euro 4-5),2006,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,06/2006,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,PEUGEOT,BOXER,F1C (Euro 5b+),2014,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,CITROEN,JUMPER,F1C (Euro 5b+),2014,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,RAM/FIAT,ProMaster 3.0,Eco Diesel 3.0 - Euro 4,2014,,2014,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19045003,Kit alternador,FIAT,DUCATO 3.0,3.0 Natural Power (Euro 6 ) | Dual-fuel CNG/petrol,2015,,2015,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8pk Ø59
3.1116 rpm (high idle speed)",,N,2015,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19055004,Kit alternador,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2021,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19055004,Kit alternador,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2021,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19055004,Kit alternador,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2021,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,11/2011,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19055004,Kit alternador,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2021,Yes,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2021,09/2024,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19095005,Kit alternador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2021,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2019,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19095005,Kit alternador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2019,,2021,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2019,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA19095005,Kit alternador,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2021,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2021,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA20045006,Kit alternador,FIAT,DUCATO,F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V 6pk Ø53
2.500 rpm (idle speed)",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA20045006,Kit alternador,FIAT,DUCATO,F1AE0481 (Euro 3-4-5) | F1AE3481 (Euro 5+),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V 6pk Ø53
2.500 rpm (idle speed)",,N,2002,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA20045006,Kit alternador,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V 6pk Ø53
2.500 rpm (idle speed)",,N,09/2019,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA20085007,Kit alternador,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"6K A Ø53
4.830 rpm",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA20085007,Kit alternador,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"6K A Ø53
4.8300 rpm",,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21055008,Kit alternador,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"Poly-V 6pk Ø53
10.889 rpm",,N,11/2017,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21055008,Kit alternador,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,yes,"Poly-V 6pk Ø53
10.889 rpm",,N,11/2017,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21075009,Kit alternador,ISUZU,- D Wide CAB 2.3 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6) | DTi8 320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,yes,,,N,09/2013,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21075009,Kit alternador,ISUZU,- CAB 2.1 m -,DTi8 280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.698,yes,"Poly-V 7pk Ø53
4.962 rpm (idle speed)",,N,09/2013,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21105010,Kit alternador,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
3.441 rpm","Poly-V 8K A Ø119
3.441 rpm",N-E,09/2021,04/2024,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA21125011,Kit alternador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2021,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 7pk Ø53
2.363 rpm (idle speed)",,N,2021,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA22065012,Kit alternador,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2021,Yes,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2021,09/2024,SEG 150A 28V 
KA22065012-B,Kit alternador,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2021,Yes,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 6pk Ø53
2.322 rpm (idle speed)",,N,09/2021,09/2024,SEG 150A 28V 
KA22105013,Kit alternador,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2021,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 6pk Ø54
2.295 rpm (idle speed)",,N,09/2021,,Valeo 140A 14V
KA23015014,Kit alternador,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 7K A Ø53
3.014 rpm",,N,09/2019,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA23025015,Kit alternador,CITROEN,JUMPY,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2016,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 5PK Ø54
10.667 rpm",,N,09/2016,,Valeo 140A 14V
KA23025015,Kit alternador,PEUGEOT,EXPERT,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2016,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 5K A Ø54
10667 rpm",,N,09/2016,,Valeo 140A 14V
KA23025015,Kit alternador,TOYOTA,PROACE,1.6D-4D 95 (Euro 6) | 1.6D-4D 115 (Euro 6),2016,,2016,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 5PK Ø54
10.667 rpm",,N,09/2016,,Valeo 140A 14V
KA23035017,Kit alternador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2019,,SEG 150A 28V 
KA23035017,Kit alternador,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2021,,SEG 150A 28V 
KA23035017,Kit alternador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2019,,SEG 150A 28V 
KA23055018,Kit alternador,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,,,N,09/2021,04/2024,SEG 150A 28V 
KA23055019,Kit alternador,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1-E6N (Euro 6N),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,,,N,2021,,Valeo 140A 14V
KA23055020,Kit alternador,PEUGEOT,BOXER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø54
11.083 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23055020,Kit alternador,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø54
11.083 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23055020,Kit alternador,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø54
11.083 r.p.m.",,N,09/2016,09/2019,Valeo 140A 14V
KA23055020,Kit alternador,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø54
11.083 r.p.m.",,N,09/2016,09/2019,Valeo 140A 14V
KA23055020,Kit alternador,CITROEN,JUMPER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø54
11.083 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23055021,Kit alternador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 5pk Ø54
2.415 rpm (idle speed)",,N,09/2019,,Valeo 140A 14V
KA23055021,Kit alternador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 5pk Ø54
2.415 rpm (idle speed)",,N,09/2019,,Valeo 140A 14V
KA23055021,Kit alternador,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Poly-V 5pk Ø54
2.415 rpm (idle speed)",,N,09/2021,,Valeo 140A 14V
KA23055022,Kit alternador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2021,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 5pk Ø53
2.363 rpm (idle speed)",,N,2021,,Valeo 140A 14V
KA23065023,Kit alternador,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2016,,Valeo 140A 14V
KA23065023,Kit alternador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23065023,Kit alternador,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23065023,Kit alternador,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23065023,Kit alternador,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Full) | M9T (Euro VI-D Full),2022,,2022,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,03/2022,,Valeo 140A 14V
KA23065023,Kit alternador,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,09/2019,,Valeo 140A 14V
KA23065023,Kit alternador,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2016,,Valeo 140A 14V
KA23065023,Kit alternador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2016,,Valeo 140A 14V
KA23065023,Kit alternador,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2014,,Valeo 140A 14V
KA23065023,Kit alternador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2014,,Valeo 140A 14V
KA23065023,Kit alternador,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2014,,Valeo 140A 14V
KA23065023,Kit alternador,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø54
3.460 r.p.m.",,N,2016,,Valeo 140A 14V
KA23105027,Kit alternador,RENAULT,MASTER 2.3 dCi - RWD,M9T (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7k Ø54
2815 rpm",,N,2016,,Mahle MG 29 (200A 14V)
KA23115029,Kit alternador,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 7K A Ø54
2188 rpm",,N,09/2019,,Valeo 140A 14V
KA23115030,Kit alternador,RENAULT,MASTER 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V K Ø55
2818 r.p.m.",,N-E,09/2024,,Valeo 140A 14V
KA23115030,Kit alternador,NISSAN,INTERSTAR 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V K Ø55
2818 r.p.m.",,N-E,09/2024,,Valeo 140A 14V
KA23125031,Kit alternador,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro 6D Temp) | F4AFE611E*N (Euro 6D Temp) | F4AFE611C*N (Euro 6D Temp) | F4AFE611D*N (Euro 6D Temp),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"2B Ø190 @ 2500 rpm
Ø70 @ 6785 rpm",,N,2014,09/2019,Valeo 140A 14V
KA23125031,Kit alternador,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro 6D Temp) | F4AFE611E*N (Euro 6D Temp) | F4AFE611C*N (Euro 6D Temp) | F4AFE611D*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"2B Ø190 @ 2500 rpm
Ø70 @ 6785 rpm",,N,09/2019,,Valeo 140A 14V
KA24015032,Kit alternador,IVECO,EuroCargo Tector 5,F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,,,N,2014,09/2019,Valeo 140A 14V
KA24015032,Kit alternador,IVECO,EuroCargo Tector,F4AE3481A (Euro 4-5),2006,,2006,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 3.920,any,,,N,06/2006,,Valeo 140A 14V
KA24015033,Kit alternador,ISUZU,NPR 75,4HK1-TCS | (Euro 4-5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,,,N,2009,,Valeo 140A 14V
KA24015033,Kit alternador,RENAULT TRUCKS,SERIE - N Euro6,4HK1-E6C | (Euro6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,,,N,2014,,Valeo 140A 14V
KA24045035,Kit alternador,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"6K A Ø53
4.8300 rpm",,N,2014,,SEG 150A 28V 
KA24045035,Kit alternador,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"6K A Ø53
4.830 rpm",,N,2014,,SEG 150A 28V 
KA24055038,Kit alternador,MITSUBISHI FUSO,"eCanter 4,25 T / 6,0 T / 7,49 T / 8,55 T",,2023,,2023,,,,Yes,,,,,,,,,,,,,,,,,,,,any,Poly-V 8K A Ø119,,N,2023,,Bosch 150A 28V
KA24075040,Kit alternador,RENAULT TRUCKS,SERIE - N Euro6,4HK1-E6C | (Euro6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,,,N,2014,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA24075040,Kit alternador,ISUZU,NPR 75,4HK1-TCS | (Euro 4-5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,,,N,2009,,Mahle MG 142 (100A 28V) | Mahle MG 29 (200A 14V)
KA24095041,Kit alternador,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø56
2.822 r.p.m.",,N,09/2024,,SEG 150A 28V 
KA24095041,Kit alternador,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø56
2.822 r.p.m.",,N,09/2024,,SEG 150A 28V 
KA24095041-A,Kit alternador,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø56
2.822 r.p.m.",,N,09/2024,,SEG 150A 28V 
KA24125042,Kit alternador,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,SEG 150A 28V 
KA24125042,Kit alternador,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,SEG 150A 28V 
KA24125042,Kit alternador,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,SEG 150A 28V 
KA24125042,Kit alternador,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,SEG 150A 28V 
KA25035043,Kit alternador,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,no,Poly-V,,N,05/2024,,SEG 150A 28V 
KA25035043,Kit alternador,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,no,Poly-V,,N,05/2024,,SEG 150A 28V 
KA25035043,Kit alternador,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,no,Poly-V,,N,05/2024,,SEG 150A 28V 
KA25035043,Kit alternador,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,no,Poly-V,,N,05/2024,,SEG 150A 28V 
KA25035043,Kit alternador,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,no,Poly-V,,N,05/2024,,SEG 150A 28V 
KA25035044,Kit alternador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2021,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 5PK Ø53
2.363 rpm (idle speed)",,N,2021,,SEG 150A 28V 
KA25105046,Kit alternador,FORD,TRANSIT 2.0 Euro 6AR / 6EA,BKFB Euro 6EA,2024,,2024,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V Ø54
2429 r.p.m.",,N,09/2024,,SEG 150A 28V 
KB00008000,Kit compresor A/C,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,BITZER 4UFC | BOCK FK40
KB00008000X,Kit compresor A/C,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,BITZER 4UFC | BOCK FK40 | X-430
KB00008001,Kit compresor A/C,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,BITZER 4UFC | BOCK FK40
KB00008001X,Kit compresor A/C,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,X-430
KB00008002X,Kit compresor A/C,ACCESSORY,SEPARADOR COLECTOR,,,,,,,,,,,,,,,,,,,,,,,,,,,,any,,,N,,,X-430
KB07118001,Kit compresor A/C,NEOPLAN,12240,D0836 LFL40-50 (Euro 3-4),2005,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,any,"2B Ø158
4.253 rpm",,N,2005,,TM 31 / QP 31
KB07118002X,Kit compresor A/C,VOLVO,B12B,DH12E,,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.100,no,"2B Ø204
2.797 rpm",,N,,,X-430
KB08108003,Kit compresor A/C,OPTARE,Double Deck,Cummins ISC,,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.300,any,"2B Ø158
3.425 rpm",,N,,,TM 31 / QP 31
KB08118004X,Kit compresor A/C,IRISBUS,AvanCity+,DEUTZ TCD 2013 L06 4V | EURO 5/EEV,2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.146,no,"2B Ø204
2.635 rpm",,N,2008,,X-430
KB09048005,Kit compresor A/C,IVECO,DAILY 3.0,F1C 3.0 (Euro 3-4),2004,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
4.573 rpm",#¿NOMBRE?,2004,,SD7H15 | TM 16 / QP 16 | UP 170 / UPF 170
KB09108008,Kit compresor A/C,VOLVO,B9TL,D9B (Euro 4-5),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,yes,"Poly-V 8K A Ø150
3.167 rpm",,N,2006,,TM 31 / QP 31
KB09118009,Kit compresor A/C,RENAULT,MASTER - FWD,G9U 650 (Euro 4) | G9U 632 (Euro 4),2006,,2010,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.464,any,"Poly-V 6K A Ø119
4.823 rpm","Poly-V 8K A Ø119
4.823 rpm",N-E,06/2006,,SD7H15 | TM 16 / QP 16 | UP 170 / UPF 170
KB09128010,Kit compresor A/C,IRISBUS,AGORA LINE D.D.,CURSOR 8 F2B | CURSOR 8 F2G,,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,yes,"Poly-V 8K A Ø150
3.640 rpm",,N,,,TM 31 / QP 31
KB10018011X,Kit compresor A/C,IRISBUS,EURORIDER 397E.12,CURSOR 10,2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.308,no,"2B Ø204
2.750 rpm",,N,2008,,X-430
KB10018012,Kit compresor A/C,IVECO,DAILY 3.0,F1C 3.0 (Euro 3-4),2004,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,"Poly-V 8K A Ø137
4.087 rpm",,N,2004,,TM 21 / QP 21
KB10018013,Kit compresor A/C,CITROEN,BERLINGO,F1C 3.0 (Euro 3-4),2004,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
4.087 rpm",,N,2004,,TM 21 / QP 21
KB10028014,Kit compresor A/C,MERCEDES,VARIO,OM 904 LA (Euro 4-5),1997,,1997,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.249,no,"Poly-V 8K A Ø137
3.206 rpm",,N,1997,,TM 21 / QP 21
KB10038015X,Kit compresor A/C,IRISBUS,CITELIS12 / CITELIS 18,CURSOR 8,2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,"2B Ø204
2.779 rpm",,N,2009,,X-430
KB10038016,Kit compresor A/C,VOLVO,K230 / 280 / 320 / 360,DC9 (Euro 5) | DC13 (Euro 5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.290_x000D_
6 / 12.740",no,"2B Ø166 (LA16.200Y)
2.625 rpm",,N,2009,,BITZER 4UFC | BOCK FK40
KB10038016X,Kit compresor A/C,VOLVO,K230 / 280 / 320 / 360,DC9 (Euro 5) | DC13 (Euro 5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.290_x000D_
6 / 12.740",no,"2B Ø204
2.142 rpm",,N,2009,,X-430
KB10038017,Kit compresor A/C,VOLVO,B13R,D13C (Euro 5),,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.800,no,"2B Ø220 (LA16.0148Y)
2.356 rpm",,N,,,BITZER 4UFC | BOCK FK40
KB10038017X,Kit compresor A/C,VOLVO,B13R,D13C (Euro 5),,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.800,no,"2B Ø204
2.541 rpm",,N,,,X-430
KB10038018,Kit compresor A/C,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5) | OM 906 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800_x000D_
6 / 6.374",no,"2B Ø158
3.899 rpm",,N,1998,,TM 31 / QP 31
KB10038019,Kit compresor A/C,VOLVO,B9TL,D9B (Euro 4-5),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,yes,"Poly-V 6K A Ø119
4.961 rpm",,N,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KB10038020,Kit compresor A/C,IRISBUS,CITELIS12 / CITELIS 18,CURSOR 8,2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,no,"2B Ø210 (LA16.158Y)
2.700 rpm",,N,2009,,BITZER 4UFC | BOCK FK40
KB10078021,Kit compresor A/C,NEOPLAN,12.250 FOCL,D0836 LOH (Euro 5-6),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,any,"2B Ø158
3.610 rpm",,N,2010,,TM 31 / QP 31
KB10098022X,Kit compresor A/C,VOLVO,B9L,D9B (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,no,"2B Ø204
2.952 rpm",,N,2006,,X-430
KB10098023,Kit compresor A/C,VOLVO,B7RLE,D7E (Euro 4-5),,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.140,no,"2B Ø200
2.887 rpm",,N,,,BOCK FK40
KB10098023X,Kit compresor A/C,VOLVO,B7RLE,D7E (Euro 4-5),,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.140,no,"2B Ø204
2.831 rpm",,N,,,X-430
KB11018024,Kit compresor A/C,IRISBUS,EuroMidi,F4AE3681D (Euro 4-5) | F4AFE611E*C (Euro 6),2010,,2020,,,,,,,,,,,,,,,,,,,,,,,"6 / 5.880_x000D_
6 / 6.728",any,"2B Ø158
3.400 rpm",,N,2010,,TM 31 / QP 31
KB11028025,Kit compresor A/C,RENAULT,MASTER - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2010,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",any,"2A Ø135
4.796 rpm",,N,06/2010,,SD7H15 | TM 16 / QP 16 | UP 170 / UPF 170
KB11038026X,Kit compresor A/C,IRISBUS,CITELIS12 / CITELIS 18,CURSOR 8 - GNC,2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,no,"2B Ø204
2.779 rpm",,N,2009,,X-430
KB11038027,Kit compresor A/C,IRISBUS,CITELIS12 / CITELIS 18,CURSOR 8 - GNC,2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,no,"2B Ø210 (LA16.158Y)
2.700 rpm",,N,2009,,BITZER 4UFC | BOCK FK40
KB11068028,Kit compresor A/C,IVECO,DAILY 3.0,F1C 3.0 (Euro 3-4),2004,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
4.573 rpm",#¿NOMBRE?,2004,,TM 21 / QP 21
KB11068029,Kit compresor A/C,,B9R,D9B (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,no,"2B Ø257 (LA16.0222Y)
2.344 rpm",,N,2006,,BITZER 4UFC | BOCK FK40
KB11068029X,Kit compresor A/C,,B9R,D9B (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,no,"2B Ø204
2.952 rpm",,N,2006,,X-430
KB11068030X,Kit compresor A/C,VOLVO,K230 / 280 / 320 / 360,DC9 (Euro 5) | DC13 (Euro 5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.290_x000D_
6 / 12.740",any,"2B Ø204
2.608 rpm",,N,2009,,X-430
KB11078031,Kit compresor A/C,ACCESSORY,STANDARD BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,any,,,N,,,ELH7 | HG34P | HGX34P
KB11078032,Kit compresor A/C,MERCEDES,SPRINTER,M 272 E 35 | (Euro 4-5-6),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 3.498,any,"Poly-V 8K A Ø137
5.512 rpm",,N,09/2008,,TM 21 / QP 21
KB11088033,Kit compresor A/C,VOLVO,B11R 4x2,D11C330 (Euro 5) | D11C370 (Euro 5) | D11C410 (Euro 5 - EEV) | DC11C450 (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.837,no,"2B Ø220 (LA16.0148Y)
2.505rpm",,N,11/2011,,BITZER 4UFC | BOCK FK40
KB11088033X,Kit compresor A/C,VOLVO,B11R 4x2,D11C330 (Euro 5) | D11C370 (Euro 5) | D11C410 (Euro 5 - EEV) | DC11C450 (Euro 5),,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.837,no,"2B Ø204
2.701 rpm",,N,,,X-430
KB11098034,Kit compresor A/C,VOLVO,B9TL,D9B260 Euro 4 | D9B260 Euro 5 EEV,2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,yes,"Poly-V 8K A Ø144
3.361 rpm",,N,2011,,TM 31 / QP 31 (x2)
KB11118035X,Kit compresor A/C,MERCEDES,INTOURO,OM 926 LA 210,,,,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.200,no,"2B Ø204
2.426 rpm",,N,,,X-430
KB11128036,Kit compresor A/C,IVECO,DAILY 3.0 MY2012,F1CE3481K (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.730 rpm",#¿NOMBRE?,01/2012,,TM 21 / QP 21
KB11128036,Kit compresor A/C,CITROEN,BERLINGO,F1CFL411F*A (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.730 rpm",#¿NOMBRE?,08/2014,,TM 21 / QP 21
KB12018037,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481K (Euro 5),2012,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,"Poly-V 8K A Ø137
4.090 rpm",,N,01/2012,,TM 21 / QP 21
KB12018037,Kit compresor A/C,CITROEN,BERLINGO,F1CFL411F*A (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,"Poly-V 8K A Ø137
4.090 rpm",,N,08/2014,,TM 21 / QP 21
KB12028038,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL411F*A (Euro 6),2014,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø145
3.860 rpm",#¿NOMBRE?,08/2014,,TM 16 / QP 16 | UP 170 / UPF 170
KB12048040,Kit compresor A/C,,ALEXANDER DENNIS,ISBe4 (EEV),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4/3.920,yes,"2B Ø158
2.590 rpm",,N,2012,,TM 31 / QP 31 (x2)
KB12048041,Kit compresor A/C,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5) | OM 906 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800_x000D_
6 / 6.374",any,"2B Ø158
4.000 rpm",,N,1998,,TM 31 / QP 31
KB12068042,Kit compresor A/C,VOLVO,B9L,D9B (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.400,no,"2B Ø20 (LA16.0146Y)
3.011 rpm",,N,2006,,BOCK FK40
KB12078043,Kit compresor A/C,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
4.511 rpm",,N,06/2011,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KB12118045,Kit compresor A/C,IVECO,DAILY 3.0 MY2012,F1CE3481K (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,,"1A Ø150
4.150 rpm",#¿NOMBRE?,01/2012,,TM 16 (x2)
KB12118046,Kit compresor A/C,IVECO,DAILY 3.0,F1C 3.0 (Euro 3-4),2004,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,,"1A Ø150, 4.573 rpm
4K A Ø159, 4.676 rpm",#¿NOMBRE?,2004,,TM 16 (x2) | UP 170 / UPF 170 (x2)
KB13028047,Kit compresor A/C,IRISBUS,EURORIDER 397E.12,CURSOR 10,2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.308,no,"2B Ø204
2.750 rpm",,N,2008,,BOCK FK40
KB13038048,Kit compresor A/C,IVECO,EuroCargo,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,,2014,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 6.700,any,"2B Ø158
2.975 rpm",,N,2014,,TM 31 / QP 31
KB13058049,Kit compresor A/C,NEOPLAN,12.250 FOCL,D0836 LOH (Euro 5-6),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,any,"2B Ø158
3.610 rpm",,N,2010,,TM 31 / QP 31
KB13068050,Kit compresor A/C,VOLVO,B11R,D11K380 (Euro 6) | D11K430 (Euro 6) | D11K470 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.837,no,"2B Ø180
2.884 rpm",,N,2013,,BOCK FK40
KB13098051,Kit compresor A/C,,B8R (Euro 6),D8K280 (Euro 6) | D8K320 (Euro 6) | D8K350 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,2B Ø180 3.278 rpm,,N,2013,,BOCK FK40
KB13108052,Kit compresor A/C,VOLVO,K320 / 360 / 410 / 450 / 490,DC9 (Euro 6) | DC13 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.290_x000D_
6 / 12.740",no,"2B Ø166 (LA16.200Y)
2.625 rpm",,N,2013,,BITZER 4UFC | BOCK FK40
KB13108052X,Kit compresor A/C,VOLVO,K320 / 360 / 410 / 450 / 490,DC9 (Euro 6) | DC13 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.290_x000D_
6 / 12.740",no,"2B Ø204
2.142 rpm",,N,2013,,X-430
KB13118055,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481D (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm","Poly-V 8K A Ø137
3.960 rpm",N-E,11/2011,,TM 21 / QP 21
KB14038057,Kit compresor A/C,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"8K A Ø151
3.730 rpm",,N,2014,,TM 31 / QP 31
KB14058058,Kit compresor A/C,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"8K A Ø151
3.730 rpm",,N,2014,,TM 31 / QP 31
KB14058059,Kit compresor A/C,ACCESSORY,COMPRESSOR BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,TM 43
KB14068060X,Kit compresor A/C,ACCESSORY,COMPRESSOR BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,X-430
KB14078061,Kit compresor A/C,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"8K A Ø137
4.100 rpm","8K A Ø137
4.100 rpm",N-E,2014,,TM 21 / QP 21
KB14088062,Kit compresor A/C,MERCEDES,SPRINTER,M 272 E 35 | (Euro 4-5-6),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 3.498,any,"Poly-V 5K A Ø119
6.200 rpm",,N,09/2008,,SD5H09
KB14098064,Kit compresor A/C,MERCEDES,CHASSIS OC 500 RF,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,"2B Ø203
2.746 rpm",,N,2014,,BOCK FK40
KB14118067,Kit compresor A/C,,B8R (Euro 6),D8K280 (Euro 6) | D8K320 (Euro 6) | D8K350 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,2B Ø180 3.278 rpm,,N,2013,,BOCK FK40
KB14128068X,Kit compresor A/C,,RC2,D0836 LOH67 (Euro 6) | D0836 LOH66 (Euro 6),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,no,"2B Ø204
1681 rpm",,N,2010,,X-430
KB15018069,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481K (Euro 5) | F1CFL411H*C (Euro 5b+) | F1CFL411F*A (Euro 6),2012,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm","Poly-V 8K A Ø119
4.560 rpm",N-E,01/2012,,SD7H15 | SD7L15 | TM 16 / QP 16 | UP 170 / UPF 170
KB15018069,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL411F*A (Euro VID) | F1CFL4115 (Euro VID),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm","Poly-V 8K A Ø119
4.560 rpm",N-E,09/2019,,SD7H15 | SD7L15 | TM 16 / QP 16 | UP 170 / UPF 170
KB15018069,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm","Poly-V 8K A Ø119
4.560 rpm",N-E,09/2021,,SD7H15 | SD7L15 | TM 16 / QP 16 | UP 170 / UPF 170
KB15028070,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481K (Euro 5) | F1CFL411H*C (Euro 5b+) | F1CFL411F*A (Euro 6),2012,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm","Poly-V 8K A Ø137
3.960 rpm",N-E,01/2012,,TM 21 / QP 21
KB15028070,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL411F*A (Euro VID) | F1CFL4115 (Euro VID),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm","Poly-V 8K A Ø137
3.960 rpm",N-E,09/2019,,TM 21 / QP 21
KB15028070,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm","Poly-V 8K A Ø137
3.960 rpm",N-E,09/2021,,TM 21 / QP 21
KB15028072,Kit compresor A/C,MERCEDES,MERCEDES OC 500 RF,OM470 (Euro 6),,,,,,,,,,,,,,,,,,,,,,,,,,6 / 10.676,no,"2B Ø203 / 2A Ø254
2.730 rpm",,N,,,BOCK FK40
KB15028073,Kit compresor A/C,OPTARE,OPTARE 30,Cummins Engine,,,,,,,,,,,,,,,,,,,,,,,,,,,no,,,N,,,BITZER 4UFC | BOCK FK40
KB15038074,Kit compresor A/C,VOLVO,B11R,D11K380 (Euro 6) | D11K430 (Euro 6) | D11K470 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.837,no,"2B Ø180
3.278 rpm",,N,2013,,BOCK FK40
KB15068075,Kit compresor A/C,IRISBUS,EuroMidi,F4AE3681B (Euro 4-5) | F4AFE611A*C (Euro 6),2010,2020,2020,,,,,,,,,,,,,,,,,,,,,,,"6 / 5.880_x000D_
6 / 6.728",any,"2B Ø158
3.400 rpm",,N,2010,01/2020,TM 31 / QP 31
KB15078076,Kit compresor A/C,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"2A Ø145
3.820 rpm",,N,2014,,TM 21 / QP 21
KB15118077,Kit compresor A/C,,B8R (Euro 6),D8K280 (Euro 6) | D8K320 (Euro 6) | D8K350 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,2B Ø158 3.734 rpm,,N,2013,,TM 31 / QP 31
KB16018078,Kit compresor A/C,,B8R (Euro 6),D8K280 (Euro 6) | D8K320 (Euro 6) | D8K350 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,"Linning LA160234Y
2B Ø210 2809 rpm
2B Ø151 4836 rpm",,N,2013,,BOCK FK40 | TM 31 / QP 31
KB16018079,Kit compresor A/C,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.940 rpm",,N,2014,,TM 21 / QP 21
KB16048081,Kit compresor A/C,IRISBUS,EuroMidi,F4AE3681B (Euro 4-5) | F4AFE611A*C (Euro 6),2010,,2020,,,,,,,,,,,,,,,,,,,,,,,"6 / 5.880_x000D_
6 / 6.728",any,"2B Ø158
3.400 rpm",,N,2010,,TM 31 / QP 31
KB16098082,Kit compresor A/C,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
3.520 rpm",,N,2014,,TM 21 / QP 21
KB17028083,Kit compresor A/C,ACCESSORY,STANDARD BOSCH ALTERNATOR BRACKET,,,,,,,,,,,,,,,,,,,,,,,,,,,,any,,,N,,,BITZER 4UFC | BOCK FK40
KB17038084,Kit compresor A/C,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"8PK Ø152
4.237 rpm",,N,2014,,TM 31 / QP 31
KB17038084-A,Kit compresor A/C,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"8PK Ø152
4.237 rpm",,N,2014,,TM 31 / QP 31
KB17038084-B,Kit compresor A/C,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"8PK Ø152
4.237 rpm",,N,2014,,TM 31 / QP 31
KB17118085,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481K (Euro 5) | F1CFL411H*C (Euro 5b+) | F1CFL411F*A (Euro 6),2012,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm",,N,01/2012,,TM 16 / QP 16 | UP 170 / UPF 170
KB17118085,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL411F*A (Euro VID) | F1CFL4115 (Euro VID),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm",,N,09/2019,,TM 16 / QP 16 | UP 170 / UPF 170
KB17118085,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm",,N,09/2021,08/2024,TM 16 / QP 16 | UP 170 / UPF 170
KB17118086,Kit compresor A/C,IVECO,DAILY 3.0,F1CE3481K (Euro 5) | F1CFL411H*C (Euro 5b+) | F1CFL411F*A (Euro 6),2012,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm",,N,01/2012,,TM 21 / QP 21
KB17118086,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL411F*A (Euro VID) | F1CFL4115 (Euro VID),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm",,N,09/2019,,TM 21 / QP 21
KB17118086,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm",,N,09/2021,08/2024,TM 21 / QP 21
KB18028089,Kit compresor A/C,,12250,D0836 LFL 79 (Euro 6c) | D0834 LFL78/79 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"6 / 6.871 &_x000D_
4 / 4.580",yes,"2B Ø158
3.610 rpm",,N,11/2017,,TM 31 / QP 31
KB18038090,Kit compresor A/C,VOLVO,FL 210,D5K210 (Euro 6) | D5K240 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.100,yes,"2B Ø158
3.200 rpm",,N,09/2013,,TM 31 / QP 31
KB18068091,Kit compresor A/C,,12250,D0836 LFL 79 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,any,"8K A Ø151
3.800 rpm",,N,11/2017,,TM 31 / QP 31
KB18068091,Kit compresor A/C,,10.190 / 10.220,D0834 LFL78/79 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.580,any,"8K A Ø151
3.800 rpm",,N,11/2017,,TM 31 / QP 31
KB18068092,Kit compresor A/C,RENAULT,MASTER - RWD,M9T / M9T B7 (Euro 5b+ / Euro 6),2014,,2014,Yes,,,Yes,Yes,Yes,ok,,,,Yes,,,,,,,,,,,,"4 / 2.298_x000D_
",any,"Poly-V 8K A Ø119
4.780 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KB18108093U,Kit compresor A/C,,B8R (Euro 5),D8C330 (EURO 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,2B Ø149 4.530 rpm,,N,2011,,TM 21 / QP 21
KB19058095,Kit compresor A/C,,12250,D0836 LFL 79 (Euro 6c) | D0834 LFL78/79 (Euro 6c),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,,,"6 / 6.871 &_x000D_
4 / 4.580",any,"8K A Ø137
4.200 rpm",,N,11/2017,,TM 21 / QP 21
KB20028096,Kit compresor A/C,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"8K A Ø137
4.100 rpm","8K A Ø137
4.100 rpm",N-E,2014,,TM 21 / QP 21
KB20028097,Kit compresor A/C,IRISBUS,EuroMidi,F4AFE611A*C (Euro 6),2020,,2020,,,,,,,,,,,,,,,,,,,,,,,6 / 6.728,any,"2B Ø158
3.400 rpm",,N,02/2020,,TM 31 / QP 31
KB20118103,Kit compresor A/C,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-E6N (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,,"Poly-V 5K A Ø125
4.100 rpm",#¿NOMBRE?,2014,,TM 21 / QP 21
KB21098106,Kit compresor A/C,IRISBUS,EuroMidi,F4AE3681D (Euro 4-5) | F4AFE611E*C (Euro 6),2010,,2020,,,,,,,,,,,,,,,,,,,,,,,"6 / 5.880_x000D_
6 / 6.728",any,"2B Ø158
3.400 rpm",,N,2010,,TM 31 / QP 31
KB21108107,Kit compresor A/C,IRISBUS,EuroMidi,F4AE3681D (Euro 4-5) | F4AFE611E*C (Euro 6),2010,,2020,,,,,,,ok,,,,,,,,,,,,,,,,"6 / 5.880_x000D_
6 / 6.728",any,"2B Ø158
3.400 rpm",,N,2010,,TM 31 / QP 31
KB22028110,Kit compresor A/C,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2020,Yes,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø137
4.632 rpm","Poly-V 8K A Ø137
4.632 rpm",N-E,2020,,TM 21 / QP 21
KB22028111,Kit compresor A/C,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2020,Yes,,,Yes,,,,,,,,,,,Yes,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
4.940 rpm","Poly-V 8K A Ø119
4.940 rpm",N-E,2020,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KB22068112,Kit compresor A/C,MERCEDES,Econic 1827/1830/1835,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"8PK Ø137
4.046 rpm",,N,2014,,QP 25
KB23068113,Kit compresor A/C,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"Poly-V 8k Ø158
3.735 rpm",,N,2014,,TM 31 / QP 31
KB23068114,Kit compresor A/C,VOLVO,K280 / 320 / 360 / 370,DC07 (Euro 6) | DC09 (Euro 6) | DC13 (Euro 6),2020,,2020,,,,Yes,,,,,,,,,,,,,,,,,,,"5 / 9.300_x000D_
6 / 6.700_x000D_
6 / 12.700",any,"Poly-V 8K A Ø157
2.636 rpm
2AB Ø173
2.393 rpm",,N,2020,,BOCK FK40 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KB23108115,Kit compresor A/C,IVECO,EuroCargo Tector 7 4X4,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6),2014,,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"2B Ø158
2.975 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KB23118116,Kit compresor A/C,VOLVO,B13R/RLE - EURO 6,D11K380 (Euro 6) | D11K430 (Euro 6) | D13K460 (Euro 6) | D13K500(Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.777,yes,"2B Ø180
3.278 rpm",,N,11/2013,,BOCK FK40
KB23118116-A,Kit compresor A/C,VOLVO,B13R/RLE - EURO 6,D11K380 (Euro 6) | D11K430 (Euro 6) | D13K460 (Euro 6) | D13K500(Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.777,yes,"2B Ø180
3.278 rpm",,N,11/2013,,BOCK FK40
KB24088117,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2024,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm",,N,09/2024,,TM 16 / QP 16
KB24088118,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2024,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm",,N,09/2024,,TM 21 / QP 21
KB25018120,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2024,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.960 rpm",,N,09/2024,,TM 16 / QP 16
KB25018121,Kit compresor A/C,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2024,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
4.560 rpm",,N,09/2024,,TM 21 / QP 21
KC05090001,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 611 DE 22 LA | OM 612 DE 27 LA | (Euro 3),2000,2006,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,"4 / 2.151_x000D_
5 / 2.686",no,"Poly-V Ø119
4.854 rpm","Poly-V 6K A Ø178
3.244 rpm",N-E/S,2000,06/2006,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100002,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 611 DE 22 LA | OM 612 DE 27 LA | (Euro 3),2000,2006,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,"4 / 2.151_x000D_
5 / 2.686",any,"2A Ø135
3.716 rpm","1A Ø150
3.344 rpm",N-E/S,2000,06/2006,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100003,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 611 DE 22 LA | OM 612 DE 27 LA | (Euro 3),2000,2006,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,"4 / 2.151_x000D_
5 / 2.686",any,"2A Ø135
3.716 rpm","1A Ø150
3.344 rpm",N-E/S,2000,06/2006,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100004,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,"2A Ø135
2.860 rpm",,N,1998,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100004,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,"2A Ø135
2.860 rpm",,N,1998,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100004,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 906 LA (Euro 3-4-5),2005,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,no,"2A Ø135
2.860 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100005,Kit compresor frío industrial,IVECO,DAILY 2.8,8140.63 (Euro 2) | 8140.43 C / S / N (Euro 2),2001,,2001,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,any,"2A Ø135
2.510 rpm",,N,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100006,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481L (EEV) | F1CE3481C (EEV),2009,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,2009,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100006,Kit compresor frío industrial,IVECO,DAILY 3.0 HPI - HPT,F1CE0481A-F (Euro 3-4) | F1CE0481B-H (Euro 3-4),2004,,2004,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,2004,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100006-E,Kit compresor frío industrial,IVECO,DAILY 3.0 HPI - HPT,F1CE0481A-F (Euro 3-4) | F1CE0481B-H (Euro 3-4),2004,,2004,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,2004,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100006-E,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481L (EEV) | F1CE3481C (EEV),2009,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,2009,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100008,Kit compresor frío industrial,RENAULT,MASTER 3.0 dCi - RWD,ZD30 | (Euro 3),2004,,2004,Yes,,,Yes,,,,,,,,,,,,,,,,,,Yes,4 / 2.953,any,"2A Ø135
3.870 rpm",,N,2004,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100008,Kit compresor frío industrial,,MASCOTT,ZD30 | (Euro 3),2004,,2004,Yes,,,Yes,,,,,,,,,,,,,,,,,,Yes,4 / 2.953,any,"2A Ø135
3.870 rpm",,N,2004,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100009,Kit compresor frío industrial,NISSAN,CABSTAR,BD-30 T (Euro 3) | BD-30 Ti (Euro 3),2003,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.120 rpm",,N,06/2003,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100009,Kit compresor frío industrial,NISSAN,ATLEON,BD-30 Ti | (Euro 3),2003,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.120 rpm",,N,06/2003,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100010,Kit compresor frío industrial,FORD,TRANSIT,2.4 Duratorq TDdi,2000,,2011,Yes,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.402,any,,"1A Ø150
2.930 rpm",#¿NOMBRE?,2000,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100011,Kit compresor frío industrial,CITROEN,JUMPER,8140.43,2000,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 8K A Ø119
2.874 rpm",N-E,2000,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100011,Kit compresor frío industrial,FIAT,DUCATO,8140.43,1998,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 8K A Ø119
2.874 rpm",N-E,1998,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100011,Kit compresor frío industrial,PEUGEOT,BOXER,8140.43,2000,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 8K A Ø119
2.874 rpm",N-E,2000,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100012,Kit compresor frío industrial,NISSAN,PRIMASTAR,G9U 630 | (Euro 3 / Euro 4),2003,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.464,no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100012,Kit compresor frío industrial,NISSAN,INTERSTAR,G9T | G9U (Euro 3) | G9U 630 (Euro 4),2001,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 2.188_x000D_
4 / 2.464",no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2001,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100012,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,G9U 630 | (Euro 3 / Euro 4),2003,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.464 ,no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100012,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO,G9T | G9U (Euro 3) | G9U 630(Euro 4),2001,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 2.188 _x000D_
4 / 2.464",no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2001,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100012,Kit compresor frío industrial,RENAULT,TRAFIC,G9U 630 | (Euro 3 / Euro 4),2003,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.464,no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100012,Kit compresor frío industrial,RENAULT,MASTER,G9T | G9U (Euro 3) | G9U 630 (Euro 4),2001,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 2.188 _x000D_
4 / 2.464",no,"Poly-V Ø119
4.387 rpm","Poly-V 7K A Ø119
4.387 rpm",N-E,2001,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100013,Kit compresor frío industrial,,LT,AGX (Euro 3),1999,,1999,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 2.461,any,"2A Ø135
2.850 rpm",,N,09/1999,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100014,Kit compresor frío industrial,,LT,MWM (Euro 3),1999,,1999,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.799,any,"2A Ø135
3.500 rpm",,N,09/1999,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100015,Kit compresor frío industrial,CITROEN,JUMPER,DW10TD (Euro 3) | DW12TED (Euro 3),2004,,2024,,,,Yes,,,,Yes,,,,,,Yes,,,,,,,,,"4 / 1.997_x000D_
4 / 2.178",no,"Poly-V Ø119
5.210 rpm","Poly-V 6K A Ø142
4.366 rpm",N-E/S,07/2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100015,Kit compresor frío industrial,FIAT,DUCATO,DW10TD (Euro 3),2004,,2024,,,,Yes,,,,Yes,,,,,,Yes,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5.210 rpm","Poly-V 6K A Ø142
4.366 rpm",N-E/S,07/2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100015,Kit compresor frío industrial,PEUGEOT,BOXER,DW10TD (Euro 3) | DW12TED (Euro 3),2004,,2024,,,,Yes,,,,Yes,,,,,,Yes,,,,,,,,,"4 / 1.997 _x000D_
4 / 2.178",no,"Poly-V Ø119
5.210 rpm","Poly-V 6K A Ø142
4.366 rpm",N-E/S,07/2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100016,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE0481D (Euro 3) | F4AE0481C (Euro 3) | F4AE0481A (Euro 3),2002,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 3.920,any,"2A Ø135
3.800 rpm",,N,10/2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100017,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE0681E (Euro 3) | F4AE0681D (Euro 3),2001,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100018,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE0681E (Euro 3) | F4AE0681B (Euro 3) | F4AE0681A (Euro 3),2001,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100019,Kit compresor frío industrial,MERCEDES,VITO,OM 646 DE 22 LA | (Euro 3),2003,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.148,no,"2A Ø135
3.040 rpm",,N,2003,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100020,Kit compresor frío industrial,MAN,TGL,D0834 LFL40-50 (Euro 3-4) | D0834 LFL41-51 (Euro 3-4) | D0834 LFL42-52 (Euro 3-4),2005,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.580,any,"2A Ø135
3.300 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100022,Kit compresor frío industrial,MERCEDES,VARIO,OM 904 LA (Euro 3) | OM 904 LA (Euro 4) | OM 904 LA (Euro 5),1997,,1997,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.249,any,"2A Ø135
2.860 rpm",,N,1997,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100023,Kit compresor frío industrial,NISSAN,PRIMASTAR,F9Q (Euro 3),2002,2006,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.265 rpm","Poly-V 8K A Ø119
4.265 rpm",N-E,2002,06/2006,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100023,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,F9Q (Euro 3),2001,2006,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.265 rpm","Poly-V 8K A Ø119
4.265 rpm",N-E,2001,06/2006,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100023,Kit compresor frío industrial,RENAULT,TRAFIC,F9Q (Euro 3),2001,2006,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.265 rpm","Poly-V 8K A Ø119
4.265 rpm",N-E,2001,06/2006,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100024,Kit compresor frío industrial,MITSUBISHI,CANTER,4M42-02AT (Euro 3),2001,2006,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.977,any,"2A Ø135
2.960 rpm",,N,2001,06/2006,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100025,Kit compresor frío industrial,,FA LF45.130,Paccar BE 99C (Euro 3) | Paccar BE 110C (Euro 3) | Paccar BE 123C (Euro 3),2001,2006,2001,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 3.900,no,"Poly-V 8K A Ø119
3.782 rpm","Poly-V 8K A Ø157
2.886 rpm",N-E/S,2001,2006,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100025,Kit compresor frío industrial,,FA LF45.180 / FA LF55.180 / FT LF55.180 / FAN LF55.180,Paccar CE 136C (Euro 3) | Paccar CE 162C (Euro 3) | Paccar CE 184C (Euro 3),2001,2006,2001,,,,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 5.900,no,"Poly-V 8K A Ø119
3.782 rpm","Poly-V 8K A Ø157
2.886 rpm",N-E/S,2001,2006,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100025,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4) | Paccar FR118 (Euro 4) | Paccar FR136 (Euro 4),2006,,2006,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 4.500,no,"Poly-V 8K A Ø119
3.782 rpm","Poly-V 8K A Ø157
2.886 rpm",N-E/S,2006,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100025,Kit compresor frío industrial,,FA LF45.220 / FA LF55.165 / FT LF55.220,Paccar GR165 (Euro 4) | Paccar GR184 (Euro 4) | Paccar GR210 (Euro 4),2006,,2006,,,,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 6.700,no,"Poly-V 8K A Ø119
3.782 rpm","Poly-V 8K A Ø157
2.886 rpm",N-E/S,2006,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100025,Kit compresor frío industrial,,KW45 160,Paccar FR160 (Euro 3-4),2006,,2006,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 4.500,no,"Poly-V 8K A Ø119
3.782 rpm","Poly-V 8K A Ø157
2.886 rpm",N-E/S,2006,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,,FA LF45.130,Paccar BE 99C (Euro 3) | Paccar BE 110C (Euro 3) | Paccar BE 123C (Euro 3),2001,2006,2001,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 3.900,any,"2A Ø135
3.480 rpm",,N,2001,2006,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,,FA LF45.180 / FA LF55.180 / FT LF55.180 / FAN LF55.180,Paccar CE 136C (Euro 3) | Paccar CE 162C (Euro 3) | Paccar CE 184C (Euro 3),2001,2006,2001,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.900,any,"2A Ø135
3.480 rpm",,N,2001,2006,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4-5) | Paccar FR118 (Euro 4-5) | Paccar FR136 (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2A Ø135
3.480 rpm",,N,2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,,FA LF45.220 / FA LF55.165 / FT LF55.220,Paccar GR165 (Euro 4-5) | Paccar GR184 (Euro 4-5) | Paccar GR210 (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2A Ø135
3.480 rpm",,N,2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,,FA LF45.140 / FA LF45.160,Paccar FR103 (Euro 5) | Paccar FR118 (Euro 5) | Paccar FR136 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2A Ø135
3.480 rpm",,N,2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100026,Kit compresor frío industrial,DAF,LF45.220 / LF45.250 / LF55.220,Paccar GR165 (Euro 5) | Paccar GR184 (Euro 5) | Paccar GR210 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2A Ø135
3.480 rpm",,N,2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100027,Kit compresor frío industrial,FORD,TRANSIT,2.0 Duratorq TDdi | (Euro 3),2000,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.998,no,"2A Ø135
3.555 rpm",,N,2000,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100028,Kit compresor frío industrial,VOLVO,FL 6,D6B180 | D6B220 | D6B250,1999,,1999,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.480,no,,"1A Ø150
2.800 rpm",#¿NOMBRE?,1999,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100029,Kit compresor frío industrial,CITROEN,BERLINGO,DW8B,2003,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.867,no,"Poly-V Ø119
5.914 rpm","Poly-V 6K A Ø142
4.956 rpm",N-E/S,01/2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100029,Kit compresor frío industrial,PEUGEOT,PARTNER,DW8,2003,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.867,no,"Poly-V Ø119
5.914 rpm","Poly-V 6K A Ø142
4.956 rpm",N-E/S,01/2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100031,Kit compresor frío industrial,CITROEN,BERLINGO,DW10,2003,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5.914 rpm","Poly-V 6K A Ø142
4.956 rpm",N-E/S,01/2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100031,Kit compresor frío industrial,PEUGEOT,PARTNER,DW10,2003,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5.914 rpm","Poly-V 6K A Ø142
4.956 rpm",N-E/S,01/2003,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100033,Kit compresor frío industrial,FIAT,SCUDO,DW8,1999,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.867,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,1999,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100033,Kit compresor frío industrial,PEUGEOT,EXPERT,DW8,1999,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.867,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,1999,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100033,Kit compresor frío industrial,CITROEN,JUMPY,DW8,1999,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.867,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,1999,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100035,Kit compresor frío industrial,FIAT,SCUDO,DW10,2004,2006,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,2004,2006,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100035,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10,2004,2006,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,2004,2006,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100035,Kit compresor frío industrial,CITROEN,JUMPY,DW10,2004,2006,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,,"Poly-V 6K A Ø142
4.920 rpm",#¿NOMBRE?,2004,2006,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100037,Kit compresor frío industrial,PEUGEOT,BOXER,DJ5 | DJ5T,1996,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.446,no,"2A Ø135
3.385 rpm",,N,1996,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100037,Kit compresor frío industrial,CITROEN,JUMPER,DJ5 | DJ5T,1996,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.446,no,"2A Ø135
3.385 rpm",,N,1996,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100038,Kit compresor frío industrial,CITROEN,JUMPER,8140.43,2000,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 5K A Ø119
2.874 rpm",N-E,2000,,TM 08 / QP 08 | UP 90
KC05100038,Kit compresor frío industrial,FIAT,DUCATO,8140.43,1998,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 5K A Ø119
2.874 rpm",N-E,1998,,TM 08 / QP 08 | UP 90
KC05100038,Kit compresor frío industrial,PEUGEOT,BOXER,8140.43,2000,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"Poly-V Ø119
2.874 rpm","Poly-V 5K A Ø119
2.874 rpm",N-E,2000,,TM 08 / QP 08 | UP 90
KC05100040,Kit compresor frío industrial,FIAT,DUCATO,F1AE0481 (Euro 3-4-5) | F1AE3481 (Euro 5+),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,11/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,08/2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,06/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE0481A-F / F1AE0481B-G (Euro 3-4) | F1AE0481M-H (Euro 3-4) | F1AE0481U/ F1AE0481V (Euro 4),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100040,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,no,"2A Ø135
3.386 rpm",,N,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100041,Kit compresor frío industrial,FORD,TRANSIT CONNECT,1.8 Duratorq TDdi | 1.8 Duratorq TDCi | (Euro 3 - Euro 4),2002,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.753,no,"2A Ø135
3.260 rpm",,N,2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100044,Kit compresor frío industrial,,H-1 CRDi,D4CB,2005,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.497,no,"2A Ø135
3.040 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100045,Kit compresor frío industrial,,NKR 77L,4JH1-X (Euro 3),2002,,2002,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.652 rpm","1A Ø150
3.287 rpm",N-E/S,2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100045,Kit compresor frío industrial,,ELF 100,4JH1-TCN (Euro 4),2002,,2002,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.652 rpm","1A Ø150
3.287 rpm",N-E/S,2002,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100046,Kit compresor frío industrial,ISUZU,NPR 70,4HE1-XS,1998,2003,1998,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.751,no,"2A Ø135
3.526 rpm",,N,1998,2003,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100046,Kit compresor frío industrial,,ELF 400 / ELF 500 / ELF 600,4HK1-TCS | (Euro 4-5),2009,,2009,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,no,"2A Ø135
3.526 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100049,Kit compresor frío industrial,MITSUBISHI,CANTER,4D34-2AT6 (Euro 3),2001,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 3.907,no,"2A Ø135
4.296 rpm","1A Ø200
2.900 rpm",N-E/S,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100051,Kit compresor frío industrial,,KUBISTAR,K9K (Euro 3),2003,2006,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2003,06/2006,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100051,Kit compresor frío industrial,RENAULT,KANGOO,K9K 812 (Euro 3),2002,2006,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2002,06/2006,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC05100053,Kit compresor frío industrial,NISSAN,PRIMASTAR,F9Q (Euro 3),2002,2006,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.229 rpm","Poly-V 6K A Ø119
4.229 rpm",N-E,2002,06/2006,TM 08 / QP 08 | UP 90
KC05100053,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,F9Q (Euro 3),2001,2006,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.229 rpm","Poly-V 6K A Ø119
4.229 rpm",N-E,2001,06/2006,TM 08 / QP 08 | UP 90
KC05100053,Kit compresor frío industrial,RENAULT,TRAFIC,F9Q (Euro 3),2001,2006,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.870,no,"Poly-V Ø119
4.229 rpm","Poly-V 6K A Ø119
4.229 rpm",N-E,2001,06/2006,TM 08 / QP 08 | UP 90
KC05100055,Kit compresor frío industrial,NISSAN,INTERSTAR,ZD30 - Euro 3 | DXi3 - Euro 4,2004,,2006,,,,Yes,,,,Yes,,,,,,,,,,,,,,Yes,4 / 2.953,no,"Poly-V Ø119
4.689 rpm","Poly-V 8K A Ø157
3.554 rpm",N-E/S,2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100055,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO,ZD30 (Euro 3) | DXi3 (Euro 4),2004,,2006,,,,Yes,,,,Yes,,,,,,,,,,,,,,Yes,4 / 2.953,no,"Poly-V Ø119
4.689 rpm","Poly-V 8K A Ø157
3.554 rpm",N-E/S,2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100055,Kit compresor frío industrial,RENAULT,MASTER,ZD30 - Euro 3 | DXi3 - Euro 4,2004,,2006,,Yes,,Yes,,,,Yes,,,,,,,,,,,,,,Yes,4 / 2.953,no,"Poly-V Ø119
4.689 rpm","Poly-V 8K A Ø157
3.554 rpm",N-E/S,2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100056,Kit compresor frío industrial,NISSAN,CABSTAR,TD-27 T | BD-30 Ti,1997,2003,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,"4 / 2.663 _x000D_
4 / 2.953",no,"2A Ø135
4.019 rpm","1A Ø150
3.617 rpm",N-E/S,1997,2003,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100056,Kit compresor frío industrial,NISSAN,ATLEON,BD-30 Ti,1997,2003,2007,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.953,no,"2A Ø135
4.019 rpm","1A Ø150
3.617 rpm",N-E/S,1997,2003,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100057,Kit compresor frío industrial,NISSAN,CABSTAR,TD-27 T | BD-30 Ti,2001,2003,2011,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 2.663 _x000D_
4 / 2.953",any,"2A Ø135
3.465 rpm",,N,2001,2003,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100057,Kit compresor frío industrial,NISSAN,ATLEON,BD-30 Ti,2001,2003,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.465 rpm",,N,2001,2003,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100058,Kit compresor frío industrial,NISSAN,ATLEON,B4-40 Ti | (Euro 3),2001,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 3.989,any,"2A Ø135
2.700 rpm",,N,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100059,Kit compresor frío industrial,NISSAN,ATLEON,B6-60 Ti | B6-60 Ti (H) | (Euro 3),2001,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.984,any,"2A Ø135
2.700 rpm",,N,2001,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100060,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,Y17 (Euro 3),2001,2005,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.686,no,"2A Ø135
3.520 rpm",,N,2001,2005,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100061,Kit compresor frío industrial,,MASCOTT,8140.43B (S9W 206) | 8140.43S (S9W 208) | 8140.43N (S9W 212),1998,,2004,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,no,"2A Ø135
3.800 rpm",,N,1998,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100062,Kit compresor frío industrial,,MASCOTT,8140.43B (S9W 206) | 8140.43S (S9W 208) | 8140.43N (S9W 212),1998,,2004,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.798,yes,"2A Ø135
2.810 rpm",,N,1998,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100064,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,MIDR040226B (Euro 2) | 4 dCi 4 (Euro 3),,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 4.000,no,"2A Ø135
4.373 rpm","1A Ø150
3.936 rpm",N-E/S,,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100065,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,dCi 6 (Euro 3),,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 6.200,no,"2A Ø135
4.373 rpm","1A Ø150
3.936 rpm",N-E/S,,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100066,Kit compresor frío industrial,,DYNA,D-4D (2KD-FTV) | (Euro 3),2005,2007,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.494,no,"2A Ø135
3.600 rpm",,N,2005,2007,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100066,Kit compresor frío industrial,,HILUX 2.5 D-4D,D-4D(2KD-FTV) | (Euro 3),2005,2007,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.494,no,"2A Ø135
3.600 rpm",,N,2005,2007,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100066,Kit compresor frío industrial,,HIACE,D-4D(2KD-FTV) | (Euro 3),2005,2007,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.494,no,"2A Ø135
3.600 rpm",,N,2005,2007,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100067,Kit compresor frío industrial,VW,CADDY,BDJ | (Euro 3),,2004,2015,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
4.706 rpm","Poly-V 6K A Ø157
3.567 rpm",N-E/S,,2004,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC05100068,Kit compresor frío industrial,VW,TRANSPORTER,86TDI(AXB) - Euro 3 | 104TDI(AXB) - Euro 3,2003,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.896,no,,"Poly-V 6K A Ø125
3.880 rpm",#¿NOMBRE?,2003,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06040074,Kit compresor frío industrial,MAN,TGL,D0836 LFL40-50 (Euro 3-4),2005,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06040074,Kit compresor frío industrial,MAN,TGM,D0836 LFL40-50 (Euro 3-4) | D0836 LFL41-51 (Euro 3-4) | D0836 LFL44-54 (Euro 3-4),2005,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06040074,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2013,2017,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06040074,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.300 rpm",,N,2013,2017,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06040075,Kit compresor frío industrial,IVECO,EuroCargo,8060.45,1997,2001,1997,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 5.861,no,"2A Ø135
3.740 rpm",,N,1997,2001,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06060076,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 646 DE LA | (Euro 4),2006,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.148,any,"2A Ø135
3.740 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06060077,Kit compresor frío industrial,MERCEDES,VITO,OM 646 DE 22 LA | (Euro 4),2006,,2014,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.148,any,,"Poly-V 6K A Ø125
3.369 rpm",#¿NOMBRE?,2006,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06070079,Kit compresor frío industrial,,DYNA,D-4D (SO5C-TB),2005,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.613,no,"2A Ø135
3.760 rpm",,N,2005,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06070081,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,,Yes,,,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,,"1A Ø150
3.173 rpm",#¿NOMBRE?,06/2011,,TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC06070082,Kit compresor frío industrial,RENAULT,KANGOO,K9K (Euro 4),2006,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06070082,Kit compresor frío industrial,,KUBISTAR,K9K (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06070083,Kit compresor frío industrial,,L-200,4D56 | 4D56 TDI,,2000,,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.477,no,"2A Ø135
3.825 rpm",,N,,2000,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06090084,Kit compresor frío industrial,PEUGEOT,BOXER,4 HV / HU (Euro 4) | 4 H6 / HH / HJ (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06090084,Kit compresor frío industrial,CITROEN,JUMPER,4 HV / HU (Euro 4) | 4 H6 / HH / HJ (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06090084,Kit compresor frío industrial,FIAT,DUCATO,4 HV (Euro 4) | 4 H6 (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06090084,Kit compresor frío industrial,CITROEN,JUMPER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06090084,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06090085,Kit compresor frío industrial,,TGA,D2066LF04 // D2066LF03 | D2066LF02 // D2066LF01,2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,"2A Ø135
3.850 rpm",,N,2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06100086,Kit compresor frío industrial,FORD,TRANSIT,2.4 Duratorq TDCi | (Euro 4),2006,,2011,Yes,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.402,any,,"1A Ø150
3.550 rpm",#¿NOMBRE?,06/2006,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06100087,Kit compresor frío industrial,FIAT,DOBLO CARGO,223 A 6000 | 182 B 9000 | 1.9 Multijet (Euro 4),2002,,2021,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.910,no,,"Poly-V 6K A Ø178
4.250 rpm",#¿NOMBRE?,2002,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06100088,Kit compresor frío industrial,MITSUBISHI,CANTER,4M42 T1 (Euro 4) | 4M42 T2 (Euro 4) | 4M42 T4 (Euro 4),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.977,no,"2A Ø135
3.555 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06100089,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 642 DE LA | (Euro 4-5-6),2006,,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06100089,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06100089,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 6d Temp),2006,,2006,,,Yes,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110090,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO,G9U 650 (Euro 4) | G9U 632 (Euro 4),2006,,2006,,,,,,,,,,,,,,,,,,,,,,,4 / 2.464,any,"Poly-V Ø119
3.529 rpm","Poly-V 8K A Ø119
3.529 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110090,Kit compresor frío industrial,NISSAN,INTERSTAR,G9U 650 (Euro 4) | G9U 632 (Euro 4),2006,,2006,,,,,,,,,,,,,,,,,,,,,,,4 / 2.464,any,"Poly-V Ø119
3.529 rpm","Poly-V 8K A Ø119
3.529 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110090,Kit compresor frío industrial,RENAULT,MASTER,G9U 650 (Euro 4) | G9U 632 (Euro 4),2006,,2006,,,,,,,,,,,,,,,,,,,,,,,4 / 2.464,any,"Poly-V Ø119
3.529 rpm","Poly-V 8K A Ø119
3.529 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110090,Kit compresor frío industrial,NISSAN,PRIMASTAR,G9U 650 (Euro 4) | G9U 632 (Euro 4),2006,,2010,,,,,,,,,,,,,,,,,,,,,,,4 / 2.464,any,"Poly-V Ø119
3.529 rpm","Poly-V 8K A Ø119
3.529 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110091,Kit compresor frío industrial,MITSUBISHI,CANTER,4M42 T1 (Euro 4) | 4M42 T2 (Euro 4) | 4M42 T4 (Euro 4),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.977,any,"Poly-V Ø119
3.388 rpm","Poly-V 8K A Ø119
3.388 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110092,Kit compresor frío industrial,NISSAN,ATLEON,ZD30Kai(Hi) (Euro 4-5) | ZD30DDTI (Euro 5) HDT,2006,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.220 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,NISSAN,CABSTAR,ZD30 Kai (Hi) (Euro 4),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,NISSAN,MAXITY,ZD30 Kai (Hi) (Euro 4),2007,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,03/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,NISSAN,MAXITY,DXi3 (FAP EEV Euro 5),2007,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,03/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,NISSAN,CABSTAR,ZD30H HD-5 (Euro 5),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,ISUZU,NT400 - CABSTAR,ZD30 KE (Euro 6),2016,,2016,,,,,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110093,Kit compresor frío industrial,NISSAN,MAXITY,DTI 3 (Euro 6),2016,,2016,,,,,,,,,,,,,,,,,,,,,,,4 / 2.953,no,"Poly-V Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110094,Kit compresor frío industrial,NISSAN,CABSTAR,ZD30 Kai (Hi) (Euro 4),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110094,Kit compresor frío industrial,NISSAN,MAXITY,ZD30 Kai (Hi) (Euro 4),2007,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,03/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110094,Kit compresor frío industrial,NISSAN,MAXITY,DXi3 (FAP EEV Euro 5),2007,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,03/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06110094,Kit compresor frío industrial,NISSAN,CABSTAR,ZD30H HD-5 (Euro 5),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 7K A Ø119
4.286 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06120095,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 780 (Euro 4),2006,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 5b+),2014,,2016,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 780 (Euro 4) | M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 780 (Euro 4) | M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120095,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC06120096,Kit compresor frío industrial,NISSAN,CABSTAR,YD25DDTi | (Euro 4),2006,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC06120096,Kit compresor frío industrial,NISSAN,MAXITY,YD25DDTi | (Euro 4),2007,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,03/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07010097,Kit compresor frío industrial,MITSUBISHI,CANTER,4M42 T1 (Euro 4) | 4M42 T2 (Euro 4),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.977,any,"Poly-V Ø119
3.388 rpm","Poly-V 8K A Ø119
3.388 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07010098,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 4) | DXi7 (Euro 4),2006,,2010,,,,,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"2A Ø135
3.680 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07010098,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"2A Ø135
3.680 rpm",,N,09/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07010099,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 4) | DXi7 (Euro 4),2006,,2010,,,,,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"2A Ø135
3.900 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07010099,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"2A Ø135
3.900 rpm",,N,09/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07020100,Kit compresor frío industrial,NISSAN,ATLEON,ISB4-6L (Euro 4) | ISB4-6H (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2A Ø135
3.630 rpm",,N,02/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07020101,Kit compresor frío industrial,NISSAN,ATLEON,ISB4-4L (Euro 4) | ISB4-4H (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.462,any,"Poly-V Ø119
3.929 rpm","Poly-V 8K A Ø119
3.929 rpm",N-E,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07020102,Kit compresor frío industrial,VW,CRAFTER,BJJ / BJK (Euro 4) | BJL / BJM (Euro 4),2006,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 2.459,any,"2A Ø135
3.295 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030103,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481A (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 3.920,any,"2A Ø135
3.800 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030103,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"2A Ø135
3.520 rpm",,N,2014,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030103,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML120E19 / ML140E19,F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"2A Ø135
3.520 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,CITROEN,JUMPER,F1C (Euro 4-5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,FIAT,DUCATO,F1C(Euro 4-5-5b+),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,PEUGEOT,BOXER,F1C (Euro 4-5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,CITROEN,JUMPER,F1C (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,PEUGEOT,BOXER,F1C (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,RAM/FIAT,ProMaster 3.0,Eco Diesel 3.0 - Euro 4,2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030104,Kit compresor frío industrial,FIAT,DUCATO 3.0,3.0 Natural Power (Euro 6D / VI-D ) | Dual-fuel CNG/petrol,2019,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.680 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030105,Kit compresor frío industrial,FIAT,SCUDO,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5109 rpm","Poly-V 6K A Ø142
4282 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030105,Kit compresor frío industrial,PEUGEOT,EXPERT,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5109 rpm","Poly-V 6K A Ø142
4282 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07030105,Kit compresor frío industrial,CITROEN,JUMPY,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
5109 rpm","Poly-V 6K A Ø142
4282 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040106,Kit compresor frío industrial,VOLVO,FL 240,D7E240 (Euro 4) | D7E280 (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"2A Ø135
3.680 rpm",,N,2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040106,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"2A Ø135
3.680 rpm",,N,09/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040107,Kit compresor frío industrial,VOLVO,FL 240,D7E240 (Euro 4) | D7E280 (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"2A Ø135
3.900 rpm",,N,2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040107,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"2A Ø135
3.900 rpm",,N,09/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040108,Kit compresor frío industrial,CITROEN,JUMPER,4 HV (Euro 4) | 4 HU (Euro 4),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040108,Kit compresor frío industrial,PEUGEOT,BOXER,4 HV(Euro 4) | 4 HU(Euro 4),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040108,Kit compresor frío industrial,FIAT,DUCATO,4 HV (Euro 4),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,07/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040109,Kit compresor frío industrial,CITROEN,JUMPY,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,02/2007,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,02/2007,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 ATED4 | (Euro 4-5),2007,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,01/2007,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 ATED4 | (Euro 4-5),2007,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,01/2007,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,,NEMO,DV4 TED | (Euro 4-5),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,01/2008,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,,BIPPER,DV4 TED | (Euro 4-5),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,01/2008,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,FORD,TRANSIT CONNECT,DV6 ATED4 | (Euro 5),2013,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,12/2013,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,FORD,TRANSIT COURIER,Duratorq TDCI 1.6 (Euro 5b+),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,TOYOTA,PROACE 1.6D,DV6 UTED 4 | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,09/2013,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,FIAT,SCUDO,DV6 UTED 4 | (Euro 4-5),2007,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,02/2007,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,CITROEN,JUMPY,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,TOYOTA,PROACE,1.6D-4D 95 (Euro 6) | 1.6D-4D 115 (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 | (Euro 6.1),,2016,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,,2016,TM 08 / QP 08 | UP 90
KC07040109,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 | (Euro 6.1),,2016,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,,2016,TM 08 / QP 08 | UP 90
KC07040110,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481C (Euro 4-5) | F4AE3481D (Euro 4-5) | F4AE3481B (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 3.920,any,"2A Ø135
3.800 rpm",,N,10/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040110,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"2A Ø135
3.520 rpm",,N,2014,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040110,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"2A Ø135
3.520 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040111,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,10/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040111,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,01/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040111,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,N,2014,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040111,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI B/C) - CNG,2015,2019,2019,,,,Yes,,,not,,,,,,,,,,,,,,,,6 / 5.880,any,"2A Ø135
3.520 rpm",,N,2015,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040111,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI-D) - CNG,2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.520 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040112,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,10/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040112,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.800 rpm",,N,01/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040112,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,N,2014,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040112,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI B/C) - CNG,2015,2019,2019,,,,Yes,,,not,,,,,,,,,,,,,,,,6 / 5.880,any,"2A Ø135
3.520 rpm",,N,2015,09/2019,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07040112,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro 6D Temp) | F4AFE611E*N (Euro 6D Temp) | F4AFE611C*N (Euro 6D Temp) | F4AFE611D*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07050114,Kit compresor frío industrial,FIAT,DUCATO,F1AE0481 (Euro 3-4-5) | F1AE3481 (Euro 5+),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V Ø119
3.130 rpm","Poly-V 5K A Ø119
3.130 rpm",N-E,2002,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07050114,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V Ø119
3.130 rpm","Poly-V 5K A Ø119
3.130 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07050114,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V Ø119
3.130 rpm","Poly-V 5K A Ø119
3.130 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07070115,Kit compresor frío industrial,,DYNA,D-4D(1KD-FTV) | (Euro 4),2006,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.982,any,"Poly-V Ø119
3.529 rpm","Poly-V 7K A Ø119
3.529 rpm",N-E,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC07070116,Kit compresor frío industrial,NISSAN,CABSTAR,YD25DDTi | (Euro 4),2006,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,yes,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07070116,Kit compresor frío industrial,NISSAN,MAXITY,YD25DDTi | (Euro 4),2007,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,yes,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,03/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07080117,Kit compresor frío industrial,,HIACE,D-4D (2KD-FTV) | (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.495,any,"2A Ø135
4.267 rpm",,N,2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07090118,Kit compresor frío industrial,ISUZU,NPR 85 / NKR85,4JJ1-TCS | (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
3.482 rpm","Poly-V 8K A Ø119
3.482 rpm",N-E,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07100119,Kit compresor frío industrial,RENAULT,MASTER 3.0 dCi - RWD,ZD30 (Euro 3) | DXi 3 (Euro 4),2004,,2004,Yes,,,Yes,,,,,,,,,,,,,,,,,,Yes,4 / 2.953,any,"2A Ø135
3.870 rpm",,N,2004,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC07100119,Kit compresor frío industrial,,MASCOTT,ZD30 (Euro 3) | DXi 3 (Euro 4),2004,,2004,Yes,,,Yes,,,,,,,,,,,,,,,,,,Yes,4 / 2.953,any,"2A Ø135
3.870 rpm",,N,2004,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08010120,Kit compresor frío industrial,,HILUX 2.5 D-4D,D-4D(2KD-FTV) | (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.494,any,"Poly-V Ø119
4.235 rpm","Poly-V 7K A Ø119
4.235 rpm",N-E,2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08010121,Kit compresor frío industrial,FORD,TRANSIT CONNECT,1.8 Duratorq TDCi | (Euro 3 / Euro 4 / Euro 5),2002,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.753,any,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2002,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08010121,Kit compresor frío industrial,CITROEN,BERLINGO,1.8 Duratorq TDCi (Euro 3 / Euro 4 / Euro 5),2002,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.753,any,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2002,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08020122,Kit compresor frío industrial,FORD,TRANSIT CONNECT,1.8 Duratorq TDCi (Euro 3-4),2002,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.753,no,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2002,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08020123,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4) | Paccar FR118 (Euro 4) | Paccar FR136 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2B Ø152
3.100 rpm",,N,2006,,TK-315
KC08020123,Kit compresor frío industrial,,FA LF45.220 / FA LF55.165 / FT LF55.220,Paccar GR165 (Euro 4) | Paccar GR184 (Euro 4) | Paccar GR210 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2B Ø152
3.100 rpm",,N,2006,,TK-315
KC08030124,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 ATED4 | (Euro 4-5),2007,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,01/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,CITROEN,JUMPY,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 ATED4 | (Euro 4-5),2007,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,01/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,,NEMO,DV4 TED | (Euro 4-5),2008,,2008,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,01/2008,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,,BIPPER,DV4 TED | (Euro 4-5),2008,,2008,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,01/2008,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,FORD,TRANSIT CONNECT,DV6 ATED4 | (Euro 5),2013,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,12/2013,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,FORD,TRANSIT COURIER,Duratorq TDCI 1.6 (Euro 5b+),2014,,2014,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,TOYOTA,PROACE 1.6D,DV6 UTED 4 | (Euro 5),2013,,2013,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,09/2013,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030124,Kit compresor frío industrial,FIAT,SCUDO,DV6 UTED 4 | (Euro 4-5),2007,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,02/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08030125,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,2B Ø152 / 2.845 rpm,,N,1998,,TK-315
KC08030125,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,2B Ø152 / 2.845 rpm,,N,1998,,TK-315
KC08030125,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),2005,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,no,2B Ø152 / 2.845 rpm,,N,2005,,TK-315
KC08030126,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 780 (Euro 4) | M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 780 (Euro 4),2006,,2010,,,,Yes,,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2010,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 5b+),2014,,2016,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 780 (Euro 4) | M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC08030126,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 630 (Euro 5) | M9R 692 (Euro 5),2006,,2010,,,,Yes,,,not,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 7K A Ø119
4.353 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC08040127,Kit compresor frío industrial,RENAULT,KANGOO,X61 K9K (Euro 4),2008,,2012,,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040127,Kit compresor frío industrial,,LOGAN VAN,K9K 792 (Euro 4),2008,,2008,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040127,Kit compresor frío industrial,RENAULT,KANGOO,K9K (Euro 4 / Euro 5 / Euro 6),2006,2019,2012,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2006,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040127,Kit compresor frío industrial,,DOKKER VAN,K9K 612 (Euro 5 / Euro 6),2013,2019,2013,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,05/2013,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040127,Kit compresor frío industrial,,CITAN,OM 607 DE15LA | (Euro 4 / Euro 5 / Euro 6),2012,,2012,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040127,Kit compresor frío industrial,NISSAN,NV200,K9K (Euro 4 / Euro 5 / Euro 6),2009,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2009,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08040128,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,2014,09/2019,TM 21 / QP 21
KC08040128,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481C (Euro 4-5) | F4AE3481D (Euro 4-5) | F4AE3481B (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 3.920,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,10/2006,,TM 21 / QP 21
KC08040128,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,09/2019,,TM 21 / QP 21
KC08040129,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,2014,09/2019,TM 21 / QP 21
KC08040129,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481A (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 3.920,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,06/2006,,TM 21 / QP 21
KC08040129,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML120E19 / ML140E19,F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.130 rpm","1B Ø150
3.130 rpm",N-E,09/2019,,TM 21 / QP 21
KC08040130,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,2014,09/2019,TM 21 / QP 21
KC08040130,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,10/2006,,TM 21 / QP 21
KC08040130,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,01/2011,,TM 21 / QP 21
KC08040130,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI B/C) - CNG,2015,2019,2019,,,,Yes,,,not,,,,,,,,,,,,,,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,2015,09/2019,TM 21 / QP 21
KC08040130,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI-D) - CNG,2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,09/2019,,TM 21 / QP 21
KC08040131,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"2B Ø152
3.100 rpm",,N,10/2006,,TK-315
KC08040131,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"2B Ø152
3.100 rpm",,N,01/2011,,TK-315
KC08040131,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"2B Ø152
3.100 rpm",,N,2014,09/2019,TK-315
KC08040132,Kit compresor frío industrial,FIAT,SCUDO,DW 10 UTED 4  (Euro 4) | DW 10 BTED 4  (Euro 4),2007,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08040132,Kit compresor frío industrial,PEUGEOT,EXPERT,DW 10 UTED 4  (Euro 4) | DW 10 BTED 4  (Euro 4),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08040132,Kit compresor frío industrial,CITROEN,JUMPY,DW 10 UTED 4  (Euro 4) | DW 10 BTED 4  (Euro 4),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08050133,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 4) | DXi7 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,06/2006,,TM 21 / QP 21
KC08050133,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,09/2010,,TM 21 / QP 21
KC08050134,Kit compresor frío industrial,PEUGEOT,BOXER,4 HV / HU (Euro 4) | 4 H6 / HH / HJ (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,TM 08 / QP 08 | UP 90
KC08050134,Kit compresor frío industrial,FIAT,DUCATO,4 HV (Euro 4) | 4 H6 (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,TM 08 / QP 08 | UP 90
KC08050134,Kit compresor frío industrial,CITROEN,JUMPER,4 HV / HU (Euro 4) | 4 H6 / HH / HJ (Euro 5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,07/2006,,TM 08 / QP 08 | UP 90
KC08050134,Kit compresor frío industrial,CITROEN,JUMPER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC08050134,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"2A Ø135
3.530 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC08060135,Kit compresor frío industrial,,MAXUS,2.5 CRD 16v | (Euro-4),2005,,2005,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.499 ,no,"Poly-V Ø119
5.429 rpm","Poly-V 6K A Ø178
3.629 rpm",N-E/S,2005,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08060136,Kit compresor frío industrial,FIAT,DOBLO CARGO,199 A 2000 (Euro 4),2004,2009,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,2004,2009,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08060136,Kit compresor frío industrial,,FIORINO,199 A 2000/9000 (Euro 4),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,01/2008,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08060136,Kit compresor frío industrial,,BIPPER,199 A 9000 (Euro 4) | F13DTE5 (Euro 5),2004,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,2004,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08060136,Kit compresor frío industrial,,NEMO,199 A 9000 (Euro 4) | F13DTE5 (Euro 5),2004,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,2004,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08070138,Kit compresor frío industrial,FORD,TRANSIT,3.2 Duratorq TDCi | (Euro 4),2008,,2011,Yes,,,Yes,,,,Yes,,,,,,,,,,,,,,,5 / 3.199,any,,"1A Ø150
3.550 rpm",#¿NOMBRE?,06/2008,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08090139,Kit compresor frío industrial,FIAT,DOBLO CARGO,199 A 2000 (Euro 4),2004,2009,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 5K A Ø119
3.697 rpm",N-E,2004,2009,TM 08 / QP 08 | UP 90
KC08090139,Kit compresor frío industrial,,NEMO,199 A 2000 (Euro 4),2004,2009,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 5K A Ø119
3.697 rpm",N-E,2004,2009,TM 08 / QP 08 | UP 90
KC08090139,Kit compresor frío industrial,,BIPPER,199 A 9000 (Euro 4) | F13DTE5 (Euro 5),2004,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 5K A Ø119
3.697 rpm",N-E,2004,,TM 08 / QP 08 | UP 90
KC08090140,Kit compresor frío industrial,FIAT,DOBLO CARGO,199 A 2000 (Euro 4),2004,2009,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2004,2009,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08090140,Kit compresor frío industrial,,NEMO,199 A 2000 (Euro 4),2004,2009,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2004,2009,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08090140,Kit compresor frío industrial,,BIPPER,199 A 9000 (Euro 4) | F13DTE5 (Euro 5),2004,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
3.697 rpm","Poly-V 8K A Ø119
3.697 rpm",N-E,2004,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08100141,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 646 DE LA | (Euro 4),2006,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.148,any,"2A Ø135
3.740 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08100141,Kit compresor frío industrial,MERCEDES,VITO,OM 646 DE 22 LA | (Euro 4),2006,,2014,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.148,any,"2A Ø135
3.740 rpm",,N,2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08110142,Kit compresor frío industrial,MERCEDES,SPRINTER,M 272 E 35 | (Euro 4 / Euro 5),2008,,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,6 / 3.498,any,"Poly-V 8K A Ø119
4.958 rpm","Poly-V 8K A Ø157
3.758 rpm",N-E,09/2008,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08110143,Kit compresor frío industrial,FIAT,SCUDO,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC08110143,Kit compresor frío industrial,PEUGEOT,EXPERT,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC08110143,Kit compresor frío industrial,CITROEN,JUMPY,DW 10 UTED 4 (Euro 4) | DW 10 BTED 4 (Euro 4),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,"Poly-V 6K A Ø125
3.200 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC08110144,Kit compresor frío industrial,,MAXUS,2.5 CRD 16v | (Euro-4),2005,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.499 ,any,"Poly-V Ø119
3.097 rpm","Poly-V 8K A Ø119
3.097 rpm",N-E,2005,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC08120145,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 780 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08120145,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 780 (Euro 4),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC08120145,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 780 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC09010146,Kit compresor frío industrial,,DYNA,N04C-TW | (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,no,"2A Ø135
3.200 rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09010146,Kit compresor frío industrial,,300 Series (Euro 4),N04C-VC (Euro 4) | N04C-UV (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,no,"2A Ø135
3.200 rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09020147,Kit compresor frío industrial,,300 Series (Euro 4),N04C-VC (Euro 4) | N04C-UV (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.200 rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09020147,Kit compresor frío industrial,,DYNA,N04C-TW | (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.200 rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030148,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 6K A Ø145
2.960 rpm",,N,2008,2017,CR2318
KC09030149,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø152 / 1B Ø155
3.050 rpm",,N,2009,,CR2318 | CR2323
KC09030149,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø152 / 1B Ø155
3.050 rpm",,N,2013,2017,CR2318 | CR2323
KC09030149,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø152 / 1B Ø155
3.050 rpm",,N,2009,,CR2318 | CR2323
KC09030149,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø152 / 1B Ø155
3.050 rpm",,N,2013,2017,CR2318 | CR2323
KC09030150,Kit compresor frío industrial,VW,CADDY,BLS | (Euro 4),2006,,2015,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.896,no,"Poly-V Ø119
4.672 rpm","Poly-V 6K A Ø142
3.915 rpm",N-E/S,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030151,Kit compresor frío industrial,VW,CADDY,BLS | (Euro 4),2006,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.896,no,,"Poly-V 6K A Ø142
3.915 rpm",#¿NOMBRE?,2006,,TM 08 / QP 08 | UP 90
KC09030155,Kit compresor frío industrial,CITROEN,JUMPER,F1C(Euro 4-5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,PEUGEOT,BOXER,F1C (Euro 4-5),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,FIAT,DUCATO,F1C(Euro 4-5-5b+),2006,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,FIAT,DUCATO,3.0 Natural Power 16 V | (Euro 4-5 / EVV),2010,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,01/2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,FIAT,DUCATO 3.0,3.0 Natural Power (Euro 6 ) | Dual-fuel CNG/petrol,2015,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,PEUGEOT,BOXER,F1C (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,CITROEN,JUMPER,F1C (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,RAM/FIAT,ProMaster 3.0,Eco Diesel 3.0 - Euro 4,2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030155,Kit compresor frío industrial,FIAT,DUCATO 3.0,3.0 Natural Power (Euro 6D / VI-D ) | Dual-fuel CNG/petrol,2019,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V Ø119
4.039 rpm","Poly-V 8K A Ø119
4.039 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030156,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE0481A-F / F1AE0481B-G (Euro 3-4) | F1AE0481M-H (Euro 3-4) | F1AE0481U/ F1AE0481V (Euro 4),2002,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,"2A Ø135
3.670 rpm",,N,2002,,TM 08 / QP 08 | UP 90
KC09030157,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09030157,Kit compresor frío industrial,MAN,TGL,D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,ISUZU,NPR 75,4HK1-TCS | (Euro 4-5),2009,,2009,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro6,4HK1-E6C | (Euro6),2014,,2018,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,,ELF 400 / ELF 500 / ELF 600,4HK1-TCS | (Euro 4-5),2009,,2009,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4HK1-TCS | (Euro 4-5),2009,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4HK1- Euro VI OBD-D,2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040158,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 6D / VI,4HK1-E6C | (Euro 6D / VI E),2014,,2014,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09040159,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 646 DE LA | (Euro 4),2006,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.148,any,"2A Ø135
3.740 rpm",,N,06/2006,,TM 08 / QP 08 | UP 90
KC09050160,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 7 Ø145
2.960 rpm",,N,2008,2017,CR2323
KC09050161,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,,"Poly-V 8K A Ø145
3.041 rpm",#¿NOMBRE?,2008,2017,TK-315
KC09050162,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 8K A Ø137
3.128 rpm","Poly-V 8K A Ø137
3.128 rpm",N-E,2008,2017,TM 21 / QP 21
KC09050163,Kit compresor frío industrial,RENAULT,KANGOO,X61 K9K (Euro 4),2008,,2012,,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 08 / QP 08 | UP 90
KC09050163,Kit compresor frío industrial,,LOGAN VAN,K9K 792 (Euro 4),2008,,2008,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 08 / QP 08 | UP 90
KC09050163,Kit compresor frío industrial,NISSAN,NV200,K9K (Euro 4 / Euro 5 / Euro 6),2009,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2009,,TM 08 / QP 08 | UP 90
KC09050163,Kit compresor frío industrial,RENAULT,KANGOO,K9K (Euro 4 / Euro 5 / Euro 6),2008,2019,2012,,,,Yes,,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,09/2019,TM 08 / QP 08 | UP 90
KC09050163,Kit compresor frío industrial,,CITAN,OM 607 DE15LA | (Euro 4 / Euro 5 / Euro 6),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 08 / QP 08 | UP 90
KC09050163,Kit compresor frío industrial,,DOKKER VAN,K9K 612 (Euro 5 / Euro 6),2013,2019,2013,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,no,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,05/2013,09/2019,TM 08 / QP 08 | UP 90
KC09060164,Kit compresor frío industrial,IVECO,STRALIS,Cursor 8 (Euro 5 / EEV) | F2B E3681C | F2B E3681B | F2B E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,"Poly-V 6K A Ø145 /Poly-V 7K A Ø145
2.996 rpm",,N,2004,,CR2318 | CR2323
KC09060165,Kit compresor frío industrial,IVECO,STRALIS,Cursor 8 (Euro 5 / EEV) | F2B E3681C | F2B E3681B | F2B E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,,"Poly-V 8K A Ø145
3.720 rpm",#¿NOMBRE?,2004,,TK-315
KC09060166,Kit compresor frío industrial,MERCEDES,ACTROS,OM 501 LA (Euro 4-5),2004,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.950,any,"Poly-V 6K A Ø145 /Poly-V 7K A Ø145
3.793 rpm",,N,2004,,CR2318 | CR2323
KC09060167,Kit compresor frío industrial,MERCEDES,ACTROS,OM 501 LA (Euro 4-5),2004,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.950,any,,"Poly-V 8K A Ø145
3.898 rpm",#¿NOMBRE?,2004,,TK-315
KC09060168,Kit compresor frío industrial,MERCEDES,SPRINTER,M 271 E18 ML | (Euro 4 / Euro 5 / Euro 6),2008,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.796,any,"2A Ø135
4.000 rpm",,N,2008,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070169,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
",any,"1B Ø152 / 1B Ø155
3.111 rpm",,N,2009,,CR2318 | CR2323
KC09070170,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2B Ø152 / 1B Ø149
3.111 rpm",,N,2009,,TK-312 | TK-315
KC09070170,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2B Ø152 / 1B Ø149
3.111 rpm",,N,2013,2017,TK-312 | TK-315
KC09070170,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2B Ø152 / 1B Ø149
3.111 rpm",,N,2009,,TK-312 | TK-315
KC09070170,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2B Ø152 / 1B Ø149
3.111 rpm",,N,2013,2017,TK-312 | TK-315
KC09070171,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070171,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2009,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070171,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6d Temp),2014,,2018,Yes,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070172,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070172,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09070172,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6d Temp),2014,,2018,Yes,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09080173,Kit compresor frío industrial,CITROEN,BERLINGO,OM 651 DE22 LA | (Euro 5),2009,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,any,"Poly-V 6K A Ø119
4.695 rpm","Poly-V 6K A Ø157
3.560 rpm",N-E,2009,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09090174,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC09090174,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530rpm",N-E,2009,,TM 08 / QP 08 | UP 90
KC09090175,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V 8K A Ø137
4.412 rpm","Poly-V 8K A Ø137
4.412 rpm",N-E,2014,,TM 21 / QP 21
KC09090175,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V 8K A Ø137
4.412 rpm","Poly-V 8K A Ø137
4.412 rpm",N-E,2009,,TM 21 / QP 21
KC09090175,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6d Temp),2014,,2018,,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V 8K A Ø137
4.412 rpm","Poly-V 8K A Ø137
4.412 rpm",N-E,2014,,TM 21 / QP 21
KC09090176,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 6K A Ø119
3.705 rpm","Poly-V 8K A Ø119
3.705 rpm",N-E,2008,2017,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09090177,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2B Ø152
2.981 rpm",,N,2009,,TK-315
KC09090178,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 780 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,TM 08 / QP 08 | UP 90
KC09090178,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 780 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,TM 08 / QP 08 | UP 90
KC09090178,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 780 (Euro 4),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,yes,"2A Ø135
3.111 rpm",,N,06/2006,,TM 08 / QP 08 | UP 90
KC09090179,Kit compresor frío industrial,NISSAN,NV200,K9K (Euro 4),2009,2012,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.500 rpm",#¿NOMBRE?,2009,2012,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC09090179,Kit compresor frío industrial,NISSAN,NV200,K9K (Euro 5),2012,,2012,,,,Yes,,,not,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC09100180,Kit compresor frío industrial,,P230 / P250 / P270 / P280 / P310 / P320,DC9 / OC9 (Euro 4-5) | DC09 (Euro 6),2008,2017,2008,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 6K A Ø145
2.960 rpm",,N,2008,2017,TK-312
KC09100181,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,2009,,TM 21 / QP 21
KC09100181,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,2013,2017,TM 21 / QP 21
KC09100181,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,2009,,TM 21 / QP 21
KC09100181,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,2013,2017,TM 21 / QP 21
KC09100182,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
",any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,2009,,TM 21 / QP 21
KC09100183,Kit compresor frío industrial,MERCEDES,VARIO,OM 904 LA (Euro 3) | OM 904 LA (Euro 4) | OM 904 LA (Euro 5),1997,,1997,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.249,any,"1B Ø152 / 1B Ø155
2.790 rpm",,N,1997,,CR2318 | CR2323
KC09110184,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"2A Ø135
3.060 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC09120185,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,2013,2017,CS150 | CS90
KC09120185,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,2009,,CS150 | CS90
KC09120185,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,2009,,CS150 | CS90
KC09120185,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,2013,2017,CS150 | CS90
KC10010186,Kit compresor frío industrial,CITROEN,BERLINGO,F1CE0481A-F (Euro 3-4) | F1CE0481B-H (Euro 3-4),2004,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,"Poly-V 6K A Ø145
3.875 rpm",,N,2004,,CR2318
KC10010186,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481L (EEV) | F1CE3481C (EEV),2009,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,no,"Poly-V 6K A Ø145
3.875 rpm",,N,2009,,CR2318
KC10010188,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5 / Euro 5b+,2010,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10010188,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5b+,2015,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD,M9T (Euro 4-5) | M9T / M9T B7 (Euro 5b+),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T (Euro 4-5),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T (Euro 4-5) | M9T / M9T B7 (Euro 5b+),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T / M9T B7 (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T / M9T B7 (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",any,"2A Ø135
3.111 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - RWD,M9T / M9T B7 (Euro 6),2016,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - RWD,M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD (EURO 6D),M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD (EURO 6D),M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD (EURO6D),M9T (Euro VI-D Temp / Euro VI-E),2019,,2022,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10020189,Kit compresor frío industrial,NISSAN,INTERSTAR 2.3 dCi - RWD (EURO 6D Full),M9T (Euro VI-D Full),2022,,2022,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10030190,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A3000 | (Euro 5),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
3.495 rpm",,N,2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10030190,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A16FDL | (Euro 5),2012,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
3.495 rpm",,N,01/2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10030190,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A3000 (Euro 4),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
3.495 rpm",,N,2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10040191,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5 / Euro 5b+,2010,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10040191,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5b+,2015,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050192,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 642 DE LA | (Euro 4-5-6),2006,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V 8K A Ø137
3.964 rpm","Poly-V 8K A Ø137
3.964 rpm",N-E,06/2006,,TM 21 / QP 21
KC10050192,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,,,,,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V 8K A Ø137
3.964 rpm","Poly-V 8K A Ø137
3.964 rpm",N-E,06/2006,,TM 21 / QP 21
KC10050192,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 6d Temp),2006,,2006,,,Yes,Yes,,,,,,,,,,,,,,,,,,,6 / 2.987,any,"Poly-V 8K A Ø137
3.964 rpm","Poly-V 8K A Ø137
3.964 rpm",N-E,06/2006,,TM 21 / QP 21
KC10050193,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481C (Euro 4-5) | F4AE3481D (Euro 4-5) | F4AE3481B (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 3.920,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,10/2006,,CR2318 | CR2323
KC10050193,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,2014,09/2019,CR2318 | CR2323
KC10050193,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,2014,09/2019,CR2318 | CR2323
KC10050194,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050194,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050194,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050194,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050194,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,"4 / 2.298_x000D_
",any,"2A Ø135
3.111 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10050195,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,199A3000 | (Euro 4),2011,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
4.100 rpm","Poly-V 8K A Ø119
4.100 rpm",N-E,12/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC10050195,Kit compresor frío industrial,FIAT,DOBLO CARGO,199A3000 (Euro 4),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
4.100 rpm","Poly-V 8K A Ø119
4.100 rpm",N-E,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC10070197,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5 / Euro 5b+,2010,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10070197,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5b+,2015,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10070198,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5 / Euro 5b+,2010,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10070198,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 | EA189 - Euro 5b+,2015,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10080199,Kit compresor frío industrial,DAF,CF75.250,Paccar PR183 (Euro 5) | Paccar PR228 (Euro 5) | Paccar PR265 (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,6 / 9.186,any,"2B Ø152
2.865 rpm",,N,2010,,TK-315
KC10080200,Kit compresor frío industrial,FIAT,DOBLO CARGO,199A3000 (Euro 4),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
4.100 rpm","Poly-V 6K A Ø119
4.100 rpm",N-E,2010,,TM 08 / QP 08 | UP 90
KC10080200,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,199A3000 | (Euro 4),2011,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,any,"Poly-V Ø119
4.100 rpm","Poly-V 6K A Ø119
4.100 rpm",N-E,12/2011,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T (Euro 4-5),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T (Euro 4-5) | M9T / M9T B7 (Euro 5b+),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD,M9T (Euro 4-5) | M9T / M9T B7 (Euro 5b+),2010,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T / M9T B7 (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T / M9T B7 (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,TM 08 / QP 08 | UP 90
KC10090201,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - RWD,M9T / M9T B7 (Euro 6),2016,,2019,Yes,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2016,,TM 08 / QP 08 | UP 90
KC10090202,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090202,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090202,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC10090202,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 5b+),2014,,2016,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC10090202,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.111 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC10090203,Kit compresor frío industrial,MERCEDES,VITO,OM 651 DE 22 LA | (Euro 5),2010,,2014,,,,Yes,,,not,Yes,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V Ø119
4.695 rpm","Poly-V 6K A Ø157
3.560 rpm",N-E/S,2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC10090204,Kit compresor frío industrial,MERCEDES,VITO,OM 651 DE 22 LA | (Euro 5),2010,,2014,,,,Yes,,,not,,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V Ø119
4.695 rpm","Poly-V 6K A Ø157
3.560 rpm",N-E,2010,,TM 08 / QP 08 | UP 90
KC10100206,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"1B Ø152 / 1B Ø155
3.484 rpm",,N,09/2010,,CR2318 | CR2323
KC10100206,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"1B Ø152 / 1B Ø155
3.484 rpm",,N,09/2010,,CR2318 | CR2323
KC10110207,Kit compresor frío industrial,FIAT,SCUDO,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2010,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,"Poly-V 6K A Ø125
3.000 rpm",#¿NOMBRE?,07/2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10110207,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,"Poly-V 6K A Ø125
3.000 rpm",#¿NOMBRE?,07/2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10110207,Kit compresor frío industrial,CITROEN,JUMPY,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,"Poly-V 6K A Ø125
3.000 rpm",#¿NOMBRE?,07/2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10110207,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2013,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,"Poly-V 6K A Ø125
3.000 rpm",#¿NOMBRE?,09/2013,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC10120211,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
",any,"1B Ø145
3.260 rpm",,N,2009,,UPF 200
KC10120212,Kit compresor frío industrial,NISSAN,CABSTAR,YD25DDTi | (Euro 4),2006,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V 8K A Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC10120212,Kit compresor frío industrial,NISSAN,MAXITY,YD25DDTi | (Euro 4),2007,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V 8K A Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E,03/2007,,TM 08 / QP 08 | UP 90
KC10120213,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"2B Ø152 / 1B Ø149
3.552 rpm",,N,09/2010,,TK-312 | TK-315
KC10120213,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"2B Ø152 / 1B Ø149
3.552 rpm",,N,09/2010,,TK-312 | TK-315
KC11030214,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481C (Euro 4-5) | F4AE3481D (Euro 4-5) | F4AE3481B (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 3.920,any,"1B Ø128 4.297 rpm / 1B Ø134
4.104 rpm",,N,10/2006,,CS150 | CS90
KC11030214,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø128 3.710 rpm
1B Ø134 3.545 rpm",,N,2014,09/2019,CS150 | CS90
KC11030214,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø128 3.710 rpm
1B Ø134 3.545 rpm",,N,09/2019,,CS150 | CS90
KC11030215,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3481A (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 3.920,any,"1B Ø128 4.297 rpm / 1B Ø134
4.104 rpm",,N,06/2006,,CS150 | CS90
KC11030215,Kit compresor frío industrial,IVECO,EuroCargo Tector 5,F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,2019,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø128 3.711 rpm
1B Ø134 3.545 rpm",,N,2014,09/2019,CS150 | CS90
KC11030215,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML120E19 / ML140E19,F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"1B Ø128 3.711 rpm
1B Ø134 3.545 rpm",,N,09/2019,,CS150 | CS90
KC11030216,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"1B Ø128 4.297 rpm / 1B Ø134
4.104 rpm",,N,10/2006,,CS150 | CS90
KC11030216,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"1B Ø128 3.710 rpm
1B Ø134 3.545 rpm",,N,2014,09/2019,CS150 | CS90
KC11030217,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"1B Ø128 4.297 rpm / 1B Ø134
4.104 rpm",,N,10/2006,,CS150 | CS90
KC11030217,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"1B Ø128 4.297 rpm / 1B Ø134
4.104 rpm",,N,2014,,CS150 | CS90
KC11030218,Kit compresor frío industrial,MERCEDES,VARIO,OM 904 LA (Euro 3) | OM 904 LA (Euro 4) | OM 904 LA (Euro 5),1997,,1997,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.249,any,"1B Ø128 3.953 rpm / 1B Ø134
3.776 rpm",,N,1997,,CS150 | CS90
KC11030219,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,"1B Ø128 / 3.953 rpm
1B Ø134 / 3.776 rpm",,N,1998,,CS150 | CS90
KC11030219,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,"1B Ø128 / 3.953 rpm
1B Ø134 / 3.776 rpm",,N,1998,,CS150 | CS90
KC11040220,Kit compresor frío industrial,,\\N,OM 651 DE22 LA | (Euro 5b - CDI | Euro 6 - BlueTEC),2009,,2009,,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"1B Ø119 5.876rpm / 1B Ø128
5.463 rpm",,N,2009,,CS55 | CS90
KC11040222,Kit compresor frío industrial,FIAT,DUCATO,F1AE0481 (Euro 3-4-5) | F1AE3481 (Euro 5+),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,any,"Poly-V Ø95
6.063 rpm",,N,2002,,CS55
KC11040222,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,any,"Poly-V Ø95
6.063 rpm",,N,2014,,CS55
KC11040223,Kit compresor frío industrial,CITROEN,JUMPER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"1B Ø119
5.147 rpm",,N,12/2011,,CS55
KC11040223,Kit compresor frío industrial,FIAT,DUCATO,4 H6(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"1B Ø119
5.147 rpm",,N,12/2011,,CS55
KC11040223,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"1B Ø119
5.147 rpm",,N,12/2011,,CS55
KC11040223,Kit compresor frío industrial,CITROEN,JUMPER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"1B Ø119
5.147 rpm",,N,2014,,CS55
KC11040223,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"1B Ø119
5.147 rpm",,N,2014,,CS55
KC11050227,Kit compresor frío industrial,,\\N,OM 651 DE22 LA ECO | (Euro 5b - CDI | Euro 6 - BlueTEC),2009,,2009,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050228,Kit compresor frío industrial,,\\N,OM 651 DE22 LA ECO | (Euro 5b - CDI | Euro 6 - BlueTEC),2009,,2009,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2009,,TM 08 / QP 08 | UP 90
KC11050229,Kit compresor frío industrial,IVECO,STRALIS,Cursor 8 (Euro 5 / EEV) | F2B E3681C | F2B E3681B | F2B E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,"Poly-V 8K A Ø137
3.258 rpm","Poly-V 8K A Ø137
3.258 rpm",N-E,2004,,TM 21 / QP 21
KC11050230,Kit compresor frío industrial,VW,CADDY,CAYE | CAYD | (Euro 5),2010,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,,"Poly-V 6K A Ø125
4.416 rpm",#¿NOMBRE?,08/2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050230,Kit compresor frío industrial,VW,CADDY,CLCA | CFHC | (Euro 5),2010,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
4.637 rpm",#¿NOMBRE?,08/2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050231,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 642 DE LA | (Euro 4-5-6),2006,,2018,,,,Yes,,,,Yes,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050231,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,,,,Yes,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050231,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 6d Temp),2006,,2006,,,Yes,Yes,,,,Yes,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E/S,06/2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050232,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 642 DE LA | (Euro 4-5-6),2006,,2018,,,,Yes,,,,,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC11050232,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,,,,,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V Ø119
4.694 rpm","Poly-V 6K A Ø142
3.934 rpm",N-E,06/2006,,TM 08 / QP 08 | UP 90
KC11050236,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A3000 | (Euro 5),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"2A Ø135
3.495 rpm",,N,2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050236,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A16FDL | (Euro 5),2012,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"2A Ø135
3.495 rpm",,N,01/2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11050236,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A3000 (Euro 4),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"2A Ø135
3.495 rpm",,N,2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11060237,Kit compresor frío industrial,VW,CRAFTER,TDI 2.0 CKTB (Euro 5/Euro 6) | TDI 2.0 CKTC (Euro 5/Euro 6) | BiTDI 2.0 CKUC (Euro 5/Euro 6) | BiTDI 2.0 CKUB (Euro 5/Euro 6),2011,2016,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"2A Ø135
3.111 rpm",,N,06/2011,12/2016,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11060238,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"2B Ø152
2.990 rpm",,N,2009,,TK-315
KC11070239,Kit compresor frío industrial,MERCEDES,ACTROS,OM 501 LA (Euro 4-5),2004,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.950,any,CS090 6PKØ90 6.290 rpm / CS150 6PKØ115 4.915 rpm,,N,2004,,CS150 | CS90
KC11070240,Kit compresor frío industrial,IVECO,STRALIS,Cursor 8 (Euro 5 / EEV) | F2B E3681C | F2B E3681B | F2B E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,"Poly-V 6K A Ø95 4.699 rpm / Poly-V K Ø115
3.882 rpm",,N,2004,,CR150 | CR90
KC11070241,Kit compresor frío industrial,IVECO,STRALIS,Cursor 10  (Euro 5 / EEV) | F3A E3681D | F3A E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.300,any,,"Poly-V 8K A Ø145
2.809 rpm",#¿NOMBRE?,2004,,TK-315
KC11080242,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,11/2011,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11080242,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,08/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11080242,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A (Euro 6) | F1CFL411F*A (Euro 6),2014,,2024,,,,Yes,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,08/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11090243,Kit compresor frío industrial,IVECO,STRALIS,Cursor 10  (Euro 5 / EEV) | F3A E3681D | F3A E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.300,any,"Poly-V 6PK Ø98
5.383 rpm / Poly-V 6PK Ø118 4.471 rpm",,N,2004,,CS150 | CS90
KC11090245,Kit compresor frío industrial,,FA LF45.140 / FA LF45.160,Paccar FR103 (Euro 5) | Paccar FR118 (Euro 5) | Paccar FR136 (Euro 5) | Paccar FR152 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2B Ø152 / 1B Ø149 / 1B Ø150
2.597 rpm","1B Ø150
2.597 rpm",N-E,2012,,TK-312 | TK-315 | TM 21 / QP 21
KC11090245,Kit compresor frío industrial,DAF,LF45.220 / LF45.250 / LF55.220,Paccar GR165 (Euro 5) | Paccar GR184 (Euro 5) | Paccar GR210 (Euro 5) | Paccar GR220 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2B Ø152 / 1B Ø149 / 1B Ø150
2.597 rpm","1B Ø150
2.597 rpm",N-E,2012,,TK-312 | TK-315 | TM 21 / QP 21
KC11100247,Kit compresor frío industrial,MAN,TGM,D0836 LFL 60/63 (Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100247,Kit compresor frío industrial,MAN,TGL,D0834 LFL 60/63 (EEV/Euro 5) | D0834 LFL 61/64 (EEV/Euro 5) | D0834 LFL 62/65 (EEV/Euro 5) | D0836 LFL 60/63 (EEV/Euro 5),2009,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100247,Kit compresor frío industrial,MAN,TGL,D0834 LFL 66/67/68 (Euro 6) | D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.300 rpm",,N,2013,2017,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100247,Kit compresor frío industrial,MAN,TGM,D0836 LFL 66/67 (Euro 6),2013,2017,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.300 rpm",,N,2013,2017,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100248,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø157
3.630 rpm",N-E/S,07/2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100248,Kit compresor frío industrial,FIAT,SCUDO,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2010,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø157
3.630 rpm",N-E/S,07/2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100248,Kit compresor frío industrial,CITROEN,JUMPY,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø157
3.630 rpm",N-E/S,07/2010,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11100248,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2013,,2021,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø157
3.630 rpm",N-E/S,09/2013,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11110250,Kit compresor frío industrial,IVECO,STRALIS,Cursor 10  (Euro 5 / EEV) | F3A E3681D | F3A E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.300,any,,"Poly-V 6K A Ø145
2.809 rpm",#¿NOMBRE?,2004,,TK-312
KC11110252,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,,"1A Ø150
4.060 rpm",#¿NOMBRE?,06/2011,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11120253,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø150
3.048 rpm",#¿NOMBRE?,11/2011,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11120254,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,Yes,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,,"1A Ø174
3.500 rpm",#¿NOMBRE?,06/2011,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC11120255,Kit compresor frío industrial,,FRR90,4HK1-E5S | (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,12/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010256,Kit compresor frío industrial,NISSAN,CABSTAR,YD25K3 LD-5 (Lo) (Euro 5) | YD25K3 LD-5 (Hi) (Euro 5),2011,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,11/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010256,Kit compresor frío industrial,ISUZU,NT400 - CABSTAR,YD25K3 LD-5 (Lo) (Euro 5b+) | YD25K3 LD-5 (Mo) (Euro 5b+) | YD25K3 LD-5 (Ho) (Euro 5b+),2014,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010256,Kit compresor frío industrial,NISSAN,MAXITY,DXi2.5 Euro 5 / 5b+ (FAP),2011,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,no,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,11/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010257,Kit compresor frío industrial,NISSAN,CABSTAR,YD25K3 LD-5 (Lo) (Euro 5) | YD25K3 LD-5 (Hi) (Euro 5),2011,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,yes,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,11/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010257,Kit compresor frío industrial,ISUZU,NT400 - CABSTAR,YD25K3 LD-5 (Lo) (Euro 5b+) | YD25K3 LD-5 (Mo) (Euro 5b+) | YD25K3 LD-5 (Ho) (Euro 5b+),2014,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,yes,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010257,Kit compresor frío industrial,NISSAN,MAXITY,DXi2.5 Euro 5 / 5b+ (FAP),2011,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.488,yes,"Poly-V Ø119
4.992 rpm","Poly-V 8K A Ø157
3.783 rpm",N-E/S,11/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010258,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø145
4.200 rpm",,N,06/2011,,TM 21 / QP 21
KC12010259,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,,"1A Ø174
3.500 rpm",#¿NOMBRE?,06/2011,,TM 08 / QP 08
KC12010260,Kit compresor frío industrial,VOLVO,FE 300 Hybrid,D7F300 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.145,yes,,Poly-V 8k Ø145,#¿NOMBRE?,01/2012,,TK-315
KC12010260,Kit compresor frío industrial,CITROEN,BERLINGO,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F300 (Euro 5) | D7F340 (Euro 5),2012,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.145,yes,,Poly-V 8k Ø145,#¿NOMBRE?,01/2012,,TK-315
KC12010261,Kit compresor frío industrial,FIAT,DUCATO,250A2000 (Euro 6),2016,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 1.956,any,"2A Ø135
3.500 rpm",,N,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12010262,Kit compresor frío industrial,VW,CRAFTER,TDI 2.0 CKTB (Euro 5/Euro 6) | TDI 2.0 CKTC (Euro 5/Euro 6) | BiTDI 2.0 CKUC (Euro 5/Euro 6) | BiTDI 2.0 CKUB (Euro 5/Euro 6),2011,2016,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"2A Ø135
3.111 rpm",,N,06/2011,12/2016,TM 08 / QP 08 | UP 90
KC12020263,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4) | Paccar FR118 (Euro 4) | Paccar FR136 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø128 4.238 rpm / 1B Ø134
4.049 rpm",,N,2006,,CS150 | CS90
KC12020264,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,any,"Poly-V Ø95
6.080 rpm / Poly-V Ø99 5.834",,N,2014,,CS55 | CS90
KC12020264,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,any,"Poly-V Ø95
6.080 rpm / Poly-V Ø99 5.834",,N,2009,,CS55 | CS90
KC12020265,Kit compresor frío industrial,FIAT,DUCATO,250A1000 (Euro 5 / Euro 5b+),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.956,no,"2A Ø135
3.234 rpm",,N,10/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030266,Kit compresor frío industrial,CITROEN,JUMPER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030266,Kit compresor frío industrial,FIAT,DUCATO,4 H6(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030266,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030266,Kit compresor frío industrial,CITROEN,JUMPER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030266,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12030267,Kit compresor frío industrial,,TGA,D2066LF04 // D2066LF03 | D2066LF02 // D2066LF01,2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,"1B Ø128
4.070rpm / 1B Ø134 3.900",,N,2006,,CS150 | CS90
KC12040269,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"1B Ø128 3.594 rpm / 1B Ø134
3.433 rpm",,N,09/2010,,CS150 | CS90
KC12050270,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12050270,Kit compresor frío industrial,CITROEN,JUMPY,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12050270,Kit compresor frío industrial,TOYOTA,PROACE 1.6D,DV6 UTED 4 | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,09/2013,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12050270,Kit compresor frío industrial,FIAT,SCUDO,DV6 UTED 4 | (Euro 4-5),2007,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12050271,Kit compresor frío industrial,NISSAN,NV200,K9K (Euro 5),2012,,2012,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12050272,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481D (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,11/2011,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12060274,Kit compresor frío industrial,IVECO,STRALIS,Cursor 8 (Euro 5 / EEV) | F2B E3681C | F2B E3681B | F2B E3681A,2004,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.790,any,,"Poly-V 8K A Ø145
3.720 rpm",#¿NOMBRE?,2004,,TK-312
KC12060275,Kit compresor frío industrial,VW,CADDY,CAYE | CAYD | (Euro 5),2010,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,,"Poly-V 6K A Ø125
4.416 rpm",#¿NOMBRE?,08/2010,,TM 08 / QP 08 | UP 90
KC12060275,Kit compresor frío industrial,VW,CADDY,CLCA | CFHC | (Euro 5),2010,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
4.637 rpm",#¿NOMBRE?,08/2010,,TM 08 / QP 08 | UP 90
KC12060276,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC12060276,Kit compresor frío industrial,CITROEN,JUMPY,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC12060276,Kit compresor frío industrial,TOYOTA,PROACE 1.6D,DV6 UTED 4 | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,09/2013,,TM 08 / QP 08 | UP 90
KC12060276,Kit compresor frío industrial,FIAT,SCUDO,DV6 UTED 4 | (Euro 4-5),2007,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 @ 1.560,yes,,"Poly-V 6K A Ø125
3.136 rpm",#¿NOMBRE?,02/2007,,TM 08 / QP 08 | UP 90
KC12060277,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12060277,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12060277,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12060278,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC12060278,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC12060278,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5),2010,,2016,,Yes,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 2.298,any,"2A Ø135
3.059 rpm",,N,06/2010,,TM 08 / QP 08 | UP 90
KC12060279,Kit compresor frío industrial,MAN,TGS,D2066 SCR 360 (Euro 5) | D2066 SCR 400 (Euro 5) | D2066 SCR 440 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,,"Poly-V 8K A Ø145
3.157 rpm",#¿NOMBRE?,2012,,TK-312
KC12060280,Kit compresor frío industrial,MAN,TGS,D2066 SCR 360 (Euro 5) | D2066 SCR 400 (Euro 5) | D2066 SCR 440 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,,"Poly-V 8K A Ø145
3.157 rpm",#¿NOMBRE?,2012,,TK-315
KC12060281,Kit compresor frío industrial,MAN,TGS,D2066 SCR 360 (Euro 5) | D2066 SCR 400 (Euro 5) | D2066 SCR 440 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,Poly-V 6K A Ø95 4.820 rpm / Poly-V 6K A Ø3.981,,N,2012,,CS150 | CS90
KC12060282,Kit compresor frío industrial,FIAT,DOBLO CARGO,263 A2000 (Euro 5),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,2010,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12060282,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263 A2000 (Euro 5),2010,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
4.000 rpm",,N,2010,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC12070283,Kit compresor frío industrial,DAF,CF75.250,Paccar PR183 (Euro 5) | Paccar PR228 (Euro 5) | Paccar PR265 (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,6 / 9.186,any,1B Ø128 3.403 rpm / 1B Ø134 3.251 rpm,,N,2010,,CS150 | CS90
KC12070284,Kit compresor frío industrial,,FA LF45.140 / FA LF45.160,Paccar FR103 (Euro 5) | Paccar FR118 (Euro 5) | Paccar FR136 (Euro 5) | Paccar FR152 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2A Ø135
3.480 rpm",,N,2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070284,Kit compresor frío industrial,DAF,LF45.220 / LF45.250 / LF55.220,Paccar GR165 (Euro 5) | Paccar GR184 (Euro 5) | Paccar GR210 (Euro 5) | Paccar GR220 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2A Ø135
3.480 rpm",,N,2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070284,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"2A Ø135
3.480 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070284,Kit compresor frío industrial,,XB230 / XB260 / XB290 / XB310,PX-7 (Euro 6) | PX-7 (Euro 6) | PX-7 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"2A Ø135
3.480 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070285,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø150
3.048 rpm",#¿NOMBRE?,11/2011,,TM 08 / QP 08 | UP 90
KC12070286,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,06/2011,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070286,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 4),2006,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,06/2006,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070286,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,2013,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12070287,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø140
4.250 rpm",#¿NOMBRE?,11/2011,,CS90
KC12070287,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø140
4.250 rpm",#¿NOMBRE?,08/2014,,CS90
KC12070287,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A (Euro 6) | F1CFL411F*A / F1CGL411F*A (Euro 6),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø140
4.250 rpm",#¿NOMBRE?,08/2014,,CS90
KC12090289,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø140
4.650 rpm",#¿NOMBRE?,11/2011,,CS90
KC12090290,Kit compresor frío industrial,VW,CRAFTER,TDI 2.0 CKTB (Euro 5/Euro 6) | TDI 2.0 CKTC (Euro 5/Euro 6) | BiTDI 2.0 CKUC (Euro 5/Euro 6) | BiTDI 2.0 CKUB (Euro 5/Euro 6),2011,2016,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"1B Ø110
5.918 rpm",,N,06/2011,12/2016,CS55
KC12090291,Kit compresor frío industrial,CITROEN,JUMPY,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 6K A Ø150
3.800 rpm",,N,07/2010,,SD5H09
KC12090291,Kit compresor frío industrial,FIAT,SCUDO,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 6K A Ø150
3.800 rpm",,N,07/2010,,SD5H09
KC12090291,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 6K A Ø150
3.800 rpm",,N,07/2010,,SD5H09
KC12090292,Kit compresor frío industrial,CITROEN,JUMPY,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V 6K A Ø150
3.800 rpm",,N,02/2007,,SD5H09
KC12090292,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 ATED4 | (Euro 4-5-6.1),2007,,2022,,,,,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V 6K A Ø150
3.800 rpm",,N,01/2007,,SD5H09
KC12090292,Kit compresor frío industrial,,NEMO,DV4 TED | (Euro 4-5),2008,,2008,,,,,,,,,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V 6K A Ø150
3.800 rpm",,N,01/2008,,SD5H09
KC12090292,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6 UTED 4 | (Euro 4-5),2007,,2019,,,,,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V 6K A Ø150
3.800 rpm",,N,02/2007,,SD5H09
KC12090292,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 ATED4 | (Euro 4-5-6.1),2007,,2022,,,,,,,,,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V 6K A Ø150
3.800 rpm",,N,01/2007,,SD5H09
KC12090292,Kit compresor frío industrial,,BIPPER,DV4 TED | (Euro 4-5),2008,,2008,,,,,,,,,,,,,,,,,,,,,,,4 / 1.399,no,"Poly-V 6K A Ø150
3.800 rpm",,N,01/2008,,SD5H09
KC12090292,Kit compresor frío industrial,FIAT,SCUDO,DV6 UTED 4 | (Euro 4-5),2007,,2010,,,,,,,,,,,,,,,,,,,,,,,4 @ 1.560,no,"Poly-V 6K A Ø150
3.800 rpm",,N,02/2007,,SD5H09
KC12100293,Kit compresor frío industrial,,FA LF45.140 / FA LF45.160,Paccar FR103 (Euro 5) | Paccar FR118 (Euro 5) | Paccar FR136 (Euro 5) | Paccar FR152 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø128 3.380 rpm /
1B Ø134 3.230 rpm",,N,2012,,CS150 | CS90
KC12100293,Kit compresor frío industrial,DAF,LF45.220 / LF45.250 / LF55.220,Paccar GR165 (Euro 5) | Paccar GR184 (Euro 5) | Paccar GR210 (Euro 5) | Paccar GR220 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"1B Ø128 3.380 rpm /
1B Ø134 3.230 rpm",,N,2012,,CS150 | CS90
KC12100294,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,1B Ø128 3.554 rpm / 1B Ø134 3.395 rpm,,N,2009,,CS150 | CS90
KC12110295,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi5 210 (Euro 6) | DTi5 240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø135
3.380 rpm",,N,09/2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12110295,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø135
3.380 rpm",,N,09/2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12110295,Kit compresor frío industrial,VOLVO,FL 210,D5K210 (Euro 6) | D5K240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø135
3.380 rpm",,N,09/2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12110295,Kit compresor frío industrial,VOLVO,FL 250,D8K250 (Euro 6) | D8K280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø135
3.380 rpm",,N,09/2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12110296,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611A,2013,2016,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 6K A Ø145
2.760 rpm",,N,01/2013,01/2016,CR2318
KC12110297,Kit compresor frío industrial,DAF,CF65.220,Paccar GR165 (E5 / EEV) | Paccar GR184 (E5 / EEV) | Paccar GR220 (E5 / EEV),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"2A Ø135
3.480 rpm",,N,2012,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC12120298,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.941 rpm",N-E,01/2010,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC12120298,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.941 rpm",N-E,01/2010,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC12120298,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.941 rpm",N-E,01/2010,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC12120298Z,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm",,N,01/2010,,UP 150 / UPF 150
KC12120298Z,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm",,N,01/2010,,UP 150 / UPF 150
KC12120298Z,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.941 rpm",N-E,01/2010,,UP 150 / UPF 150
KC12120299,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,1B Ø128 3.402 rpm / 1BØ134 2.904 rpm,,N,2012,,CS150 | CS90
KC12120300,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300,Kit compresor frío industrial,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Full) | M9T (Euro VI-D Full),2022,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,03/2022,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC12120300Z,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120300Z,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC12120301,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611A,2013,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,,"Poly-V 8K A Ø145
3.012 rpm",#¿NOMBRE?,2013,,TK-315
KC12120302,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611A,2013,2016,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 6K A Ø95 4.700 rpm / Poly-V K Ø115
3.880 rpm",,N,01/2013,01/2016,CS150 | CS90
KC12120304,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611A,2013,2016,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 8K A Ø137
3.260 rpm",,N,01/2013,01/2016,TM 21 / QP 21
KC13010305,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"1B Ø152 / 1B Ø155
2.935 rpm",,N,2009,,CR2318 | CR2323
KC13020306,Kit compresor frío industrial,,FA LF45.220 / FA LF55.165 / FT LF55.220,Paccar GR165 (Euro 4) | Paccar GR184 (Euro 4) | Paccar GR210 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"1B Ø150 / 1B Ø155
3.032 rpm",,N,2006,,CR2318 | CR2323
KC13020306,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4) | Paccar FR118 (Euro 4) | Paccar FR136 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150 / 1B Ø155
3.032 rpm",,N,2006,,CR2318 | CR2323
KC13020307,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,01/2011,,CR2318 | CR2323
KC13020307,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 5.880,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,10/2006,,CR2318 | CR2323
KC13020307,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"1B Ø152 / 1B Ø155
3.100 rpm",,N,2014,,CR2318 | CR2323
KC13020308,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611A,2013,2016,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 7K A Ø145
3.012 rpm",,N,01/2013,01/2016,CR2323
KC13020309,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,1B Ø149 / 2.845 rpm,,N,1998,,TK-312
KC13020309,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø149 / 2.845 rpm,,N,1998,,TK-312
KC13020309,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø149 / 2.845 rpm,,N,1998,,TK-312
KC13020310,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,"1B Ø150 / 2B Ø149
2.845 rpm",1B Ø150 / 2.845 rpm,N-E,1998,,TM 21 / QP 21
KC13020310,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,"1B Ø150 / 2B Ø149
2.845 rpm",1B Ø150 / 2.845 rpm,N-E,1998,,TM 21 / QP 21
KC13020310,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 906 LA (Euro 3-4-5),1998,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,no,"1B Ø150 / 2B Ø149
2.845 rpm",1B Ø150 / 2.845 rpm,N-E,1998,,TM 21 / QP 21
KC13020311,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø152 / 2.845 rpm,,N,1998,,CR2318
KC13020311,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,1B Ø152 / 2.845 rpm,,N,1998,,CR2318
KC13020311,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø152 / 2.845 rpm,,N,1998,,CR2318
KC13020312,Kit compresor frío industrial,MERCEDES,ATEGO,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø155 / 2.845 rpm,,N,1998,,CR2323
KC13020312,Kit compresor frío industrial,MERCEDES,ATEGO,OM 906 LA (Euro 3) | OM 906 LA (Euro 4) | OM 906 LA (Euro 5),1998,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.374,any,1B Ø155 / 2.845 rpm,,N,1998,,CR2323
KC13020312,Kit compresor frío industrial,MERCEDES,AXOR 1823 / 1828 / 2523 / 2528,OM 904 LA (Euro 3-4-5) | OM 924 LA (Euro 3-4-5),1998,,2005,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.249_x000D_
4 / 4.800",any,1B Ø155 / 2.845 rpm,,N,1998,,CR2323
KC13020313,Kit compresor frío industrial,ISUZU,- CAB 2.0 m -,DTi3 180 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
2.600 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13020313,Kit compresor frío industrial,,NT500,ZDK2 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
2.600 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13020314,Kit compresor frío industrial,IVECO,EuroCargo Tector,FPT Tector 6 | CNG engine,2011,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,01/2011,,TM 21 / QP 21
KC13020314,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,2014,09/2019,TM 21 / QP 21
KC13020314,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,10/2006,,TM 21 / QP 21
KC13020314,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI B/C) - CNG,2015,2019,2019,,,,Yes,,,not,,,,,,,,,,,,,,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,2015,09/2019,TM 21 / QP 21
KC13020314,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro 6D Temp) | F4AFE611E*N (Euro 6D Temp) | F4AFE611C*N (Euro 6D Temp) | F4AFE611D*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,09/2019,,TM 21 / QP 21
KC13020315,Kit compresor frío industrial,,FA LF45.140,Paccar FR103 (Euro 4) | Paccar FR118 (Euro 4) | Paccar FR136 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.150 rpm","1B Ø150
3.150 rpm",N-E,2006,,TM 21 / QP 21
KC13020315,Kit compresor frío industrial,,FA LF45.220 / FA LF55.165 / FT LF55.220,Paccar GR165 (Euro 4) | Paccar GR184 (Euro 4) | Paccar GR210 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,any,"1B Ø150
3.150 rpm","1B Ø150
3.150 rpm",N-E,2006,,TM 21 / QP 21
KC13020315,Kit compresor frío industrial,,KW45 225,Paccar GR225 (Euro 4) | Paccar GR250 (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.150 rpm","1B Ø150
3.150 rpm",N-E,2006,,TM 21 / QP 21
KC13020316-D,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
2.955 rpm",,N,2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC13020316-E,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
2.955 rpm",,N,2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC13020316-F,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
2.955 rpm",,N,2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC13030317,Kit compresor frío industrial,IVECO,DAILY 3.0 Natural Power,F1CE0441 EEV,2011,,2011,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,11/2011,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13030317,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFA401A*A (CNG) | F1CFA401A*B (NPW),2014,,2024,,,,Yes,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,09/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13030318,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi5 210 (Euro 6) | DTi5 240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø145
3.150rpm",,N,09/2013,,TM 21 / QP 21
KC13030318,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
3.150rpm",,N,09/2013,,TM 21 / QP 21
KC13030318,Kit compresor frío industrial,VOLVO,FL 210,D5K210 (Euro 6) | D5K240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø145
3.150rpm",,N,09/2013,,TM 21 / QP 21
KC13030318,Kit compresor frío industrial,VOLVO,FL 250,D8K250 (Euro 6) | D8K280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
3.150rpm",,N,09/2013,,TM 21 / QP 21
KC13030319,Kit compresor frío industrial,,LOGAN VAN,K9K 792 (Euro 4),2008,,2008,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC13030319,Kit compresor frío industrial,RENAULT,KANGOO,K9K (Euro 5 / Euro 6),2012,2019,2012,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC13030319,Kit compresor frío industrial,,DOKKER VAN,K9K 612 (Euro 5 / Euro 6),2013,2019,2013,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,05/2013,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC13030319,Kit compresor frío industrial,,CITAN,OM 607 DE15LA | (Euro 4 / Euro 5 / Euro 6),2012,,2012,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC13030320,Kit compresor frío industrial,RENAULT,KANGOO,K9K (Euro 5 / Euro 6),2012,2019,2012,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,09/2019,TM 08 / QP 08 | UP 90
KC13030320,Kit compresor frío industrial,,CITAN,OM 607 DE15LA | (Euro 4 / Euro 5 / Euro 6),2012,,2012,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,2012,,TM 08 / QP 08 | UP 90
KC13030320,Kit compresor frío industrial,,LOGAN VAN,K9K 792 (Euro 4),2008,,2008,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,03/2008,,TM 08 / QP 08 | UP 90
KC13030320,Kit compresor frío industrial,,DOKKER VAN,K9K 612 (Euro 5 / Euro 6),2013,2019,2013,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.461,yes,,"Poly-V 6K A Ø125
4.800 rpm",#¿NOMBRE?,05/2013,09/2019,TM 08 / QP 08 | UP 90
KC13040322,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,"1B Ø150
2.904 rpm",,N,2012,,TM 21 / QP 21
KC13040323,Kit compresor frío industrial,RENAULT,TRAFIC,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.491 rpm",N-E,01/2010,,TM 08 / QP 08 | UP 90
KC13040323,Kit compresor frío industrial,NISSAN,PRIMASTAR,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2010,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.491 rpm",N-E,01/2010,,TM 08 / QP 08 | UP 90
KC13040323,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,M9R 630 (Euro 5) | M9R 692 (Euro 5),2010,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8K A Ø119
2.941 rpm","Poly-V 7K A Ø119
2.491 rpm",N-E,01/2010,,TM 08 / QP 08 | UP 90
KC13040324,Kit compresor frío industrial,FIAT,SCUDO,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 6K A Ø142
4.014 rpm",N-E,07/2010,,TM 08 / QP 08 | UP 90
KC13040324,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 6K A Ø142
4.014 rpm",N-E,07/2010,,TM 08 / QP 08 | UP 90
KC13040324,Kit compresor frío industrial,CITROEN,JUMPY,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2010,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 6K A Ø142
4.014 rpm",N-E,07/2010,,TM 08 / QP 08 | UP 90
KC13040324,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10CTED4 (Euro 5) | DW10CD (Euro 5),2013,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 rpm","Poly-V 6K A Ø142
4.014 rpm",N-E,09/2013,,TM 08 / QP 08 | UP 90
KC13050326,Kit compresor frío industrial,MERCEDES,SPRINTER,M 272 E 35 | (Euro 4 / Euro 5),2008,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 3.498,any,"Poly-V 8K A Ø137
4.306 rpm","Poly-V 8K A Ø137
4.306 rpm",N-E,09/2008,,TM 21 / QP 21
KC13050327,Kit compresor frío industrial,MERCEDES,ACTROS,OM 501 LA (Euro 4-5),2004,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.950,any,"Poly-V 6PK Ø137
4.125 rpm",,N,2004,,TM 21 / QP 21
KC13050328,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,11/2011,,TM 21 / QP 21
KC13050328,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,09/2014,,TM 21 / QP 21
KC13050328,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A (Euro 6) | F1CFL411F*A / F1CGL411F*A (Euro 6),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,,"1A Ø150
3.220 rpm",#¿NOMBRE?,09/2014,,TM 21 / QP 21
KC13050329,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6) | 4PT10-AAT6 (Euro 6),2014,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,2014,,TM 21 / QP 21
KC13050329,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-BAT2 (Euro 5b+) | 4PT10-BAT4 (Euro 5b+) | 4PT10-BAT6 (Euro 5b+),2014,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,2014,,TM 21 / QP 21
KC13050329,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,2009,,TM 21 / QP 21
KC13050329,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2019,,TM 21 / QP 21
KC13050330,Kit compresor frío industrial,,NT500,ZDK2 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø145
2.420 rpm",,N,2014,,TM 21 / QP 21
KC13050330,Kit compresor frío industrial,ISUZU,- CAB 2.0 m -,DTi3 180 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø145
2.420 rpm",,N,2014,,TM 21 / QP 21
KC13050331,Kit compresor frío industrial,ISUZU,- CAB 2.0 m -,DTi3 150 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.440 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13050331,Kit compresor frío industrial,,NT500,ZDKe (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø135
3.440 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13050332,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481D (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,11/2011,,TM 21 / QP 21
KC13050333,Kit compresor frío industrial,VW,CRAFTER,TDI 2.0 CKTB (Euro 5) | TDI 2.0 CKTC (Euro 5) | BiTDI 2.0 CKUC (Euro 5) | BiTDI 2.0 CKUB (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"2A Ø145
2.896 rpm",,N,06/2011,,TM 21 / QP 21
KC13050334,Kit compresor frío industrial,DAF,CF75.250,Paccar PR183 (Euro 5) | Paccar PR228 (Euro 5) | Paccar PR265 (Euro 5),2010,,2010,,,,,,,,,,,,,,,,,,,,,,,6 / 9.186,any,"1B Ø152
2.904 rpm","1B Ø152
2.904 rpm",N-E,2010,,TM 21 / QP 21
KC13060335,Kit compresor frío industrial,,NP300,KA24DEN (petrol supply),2010,,2015,,,,,,,,,,,,,,,,,,,,,,,4 / 2.389,no,"2A Ø135
5.585 rpm","1A Ø165
4.570 rpm",N-E,2010,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13070336,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A4000 CNG (Euro 5),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC13070336,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,198A4000 CNG (Euro 5),2012,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2012,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC13070336,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A4000 CNG (Euro 6),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC13070336,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A14FCCNG (Euro 6),2010,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC13070336,Kit compresor frío industrial,FIAT,DOBLO CARGO,1.4 Petrol (Euro 6D Temp) | 1.4 CNG (Euro 6D Temp),2019,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,09/2019,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC13080337,Kit compresor frío industrial,IVECO,STRALIS,Cursor 11 (Euro 6) | F3GFE611D | F3GFE611B | F3GFE611A,2013,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.118,yes,Poly-V 8K A Ø137 3.318 rpm,Poly-V 8K A Ø137 3.318 rpm,N-E,2013,,TM 21 / QP 21
KC13080338,Kit compresor frío industrial,IVECO,STRALIS,Cursor 11 (Euro 6) | F3GFE611D | F3GFE611B | F3GFE611A,2013,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 11.118,yes,"Poly-V 6PK Ø95 4.784 rpm
Poly-V 6PK Ø115 3.952 rpm",,N,2013,,CS150 | CS90
KC13080339,Kit compresor frío industrial,CITROEN,JUMPER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,TM 08 / QP 08 | UP 90
KC13080339,Kit compresor frío industrial,FIAT,DUCATO,4 H6(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,TM 08 / QP 08 | UP 90
KC13080339,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6(Euro 5) | 4 HH(Euro 5) | 4 HJ(Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,12/2011,,TM 08 / QP 08 | UP 90
KC13080339,Kit compresor frío industrial,PEUGEOT,BOXER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC13080339,Kit compresor frío industrial,CITROEN,JUMPER,4 H6 (Euro 5b+) | 4 HH (Euro 5b+) | 4 HJ (Euro 5b+),2014,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,any,"2A Ø135
3.530 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC13080340,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
3.530 rpm",,N,06/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13080340,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 4),2006,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
3.530 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13080340,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
2.955 rpm",,N,2013,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC13080340-C,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 4),2006,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
3.530 rpm",,N,06/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC13080340-C,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,yes,"2A Ø135
3.530 rpm",,N,06/2011,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
KC13090341,Kit compresor frío industrial,FIAT,DUCATO,F1AE0481 (Euro 3-4-5) | F1AE3481 (Euro 5+),2002,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,any,"Poly-V Ø119
3.130 rpm","Poly-V 5K A Ø119
3.130 rpm",N-E,2002,,TM 08 / QP 08 | UP 90
KC13090341,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,any,"Poly-V Ø119
3.130 rpm","Poly-V 5K A Ø119
3.130 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC13090342,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 642 DE LA | (Euro 4-5-6),2006,,2018,,,,Yes,,,,,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V 6K A Ø95
5.880 rpm",,N,06/2006,,CS90
KC13090342,Kit compresor frío industrial,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,,,,,,,,,,,,,Yes,,,,,,6 / 2.987,any,"Poly-V 6K A Ø95
5.880 rpm",,N,06/2006,,CS90
KC13120343,Kit compresor frío industrial,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø135
3.000 rpm",,N,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC13120344,Kit compresor frío industrial,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
2.790 rpm",,N,2014,,TM 21 / QP 21
KC14010345,Kit compresor frío industrial,,NT500,ZDKe (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø145
3.200 rpm",,N,2014,,TM 21 / QP 21
KC14010345,Kit compresor frío industrial,ISUZU,- CAB 2.0 m -,DTi3 150 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,any,"2A Ø145
3.200 rpm",,N,2014,,TM 21 / QP 21
KC14010346,Kit compresor frío industrial,VW,CRAFTER,TDI 2.0 CKTB (Euro 5) | TDI 2.0 CKTC (Euro 5) | BiTDI 2.0 CKUC (Euro 5) | BiTDI 2.0 CKUB (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,no,"2A Ø145
2.896 rpm",,N,06/2011,,TM 21 / QP 21
KC14020347,Kit compresor frío industrial,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"2A Ø135
3.000 rpm",,N,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC14020348,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.150 rpm","TM 21 / QP 21
1B Ø150 -3.150rpm",N-E,2014,,TK-315 | TM 21 / QP 21
KC14020348,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,,"TK-315
2B Ø150 -3.150rpm",#¿NOMBRE?,2014,,TK-315 | TM 21 / QP 21
KC14020348,Kit compresor frío industrial,,XB230 / XB260 / XB290 / XB310,PX-7 (Euro 6) | PX-7 (Euro 6) | PX-7 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.150 rpm","TM 21 / QP 21
1B Ø150 -3.150rpm",N-E,2014,,TK-315 | TM 21 / QP 21
KC14020349,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"2A Ø135
3.480 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14020349,Kit compresor frío industrial,,XB230 / XB260 / XB290 / XB310,PX-7 (Euro 6) | PX-7 (Euro 6) | PX-7 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"2A Ø135
3.480 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14030350,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-BAT2 (Euro 5b+) | 4PT10-BAT4 (Euro 5b+) | 4PT10-BAT6 (Euro 5b+),2014,,2019,,,,Yes,,,ok,Yes,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14030350,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6) | 4PT10-AAT6 (Euro 6),2014,,2019,,,,Yes,,,ok,Yes,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14030350,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,Yes,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14030350,Kit compresor frío industrial,MITSUBISHI,CANTER,4P10T2 (Euro 5) | 4P10T3 (Euro 5) | 4P10T6 (Euro 5),2009,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14030351,Kit compresor frío industrial,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"2A Ø145
2.790 rpm",,N,2014,,TM 21 / QP 21
KC14040352,Kit compresor frío industrial,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"8K A Ø95 5.928 rpm /
8K A Ø115 4.897 rpm",,N,2014,,CS150 | CS90
KC14040352,Kit compresor frío industrial,MERCEDES,ANTOS,OM936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"8K A Ø95 5.928 rpm /
8K A Ø115 4.897 rpm",,N,2012,,CS150 | CS90
KC14040352,Kit compresor frío industrial,MERCEDES,ACTROS,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"8K A Ø95 5.928 rpm /
8K A Ø115 4.897 rpm",,N,2014,,CS150 | CS90
KC14040354,Kit compresor frío industrial,,F-350XL / FX350XL PLUS,Boss SOHC V8,2010,,2010,,,,,,,,,,,,,,,,,,,,,,,6200-08-01 00:00:00,no,"Poly-V 6PK Ø119
7.764 rpm",,N,2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC14040355,Kit compresor frío industrial,,F-450 XL (SUPER DUTY),Triton SOHC V10,2010,,2010,,,,,,,,,,,,,,,,,,,,,,,6800-10-01 00:00:00,no,"Poly-V 6PK Ø119
6.705 rpm",,N,2010,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC14040356,Kit compresor frío industrial,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"7K A Ø95 5.928 rpm /
7K A Ø115 4.897 rpm",,N,2014,,CS150 | CS90
KC14050357,Kit compresor frío industrial,VOLVO,FE 250,D8K250 (Euro 6) | D8K280 (Euro 6) | D8K320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050357,Kit compresor frío industrial,ISUZU,- D Wide CAB 2.3 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6) | DTi8 320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050358,Kit compresor frío industrial,ISUZU,- D Wide CAB 2.3 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6) | DTi8 320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,TM 21 / QP 21
KC14050358,Kit compresor frío industrial,VOLVO,FE 250,D8K250 (Euro 6) | D8K280 (Euro 6) | D8K320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,TM 21 / QP 21
KC14050359,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,6PK Ø95 4547 rpm / 6PK Ø115 3756 rpm,,N,2012,,CS150 | CS90
KC14050360,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,"8PK Ø 135
3200 rpm",,N,2012,,TM 21 / QP 21
KC14050360,Kit compresor frío industrial,MERCEDES,ACTROS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,"8PK Ø 135
3200 rpm",,N,2012,,TM 21 / QP 21
KC14050361,Kit compresor frío industrial,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.000 rpm","1B Ø150
3.000 rpm",N-E,2014,,TM 21 / QP 21
KC14050361,Kit compresor frío industrial,,XB170 / XB190 / XB210,PX-5 170 (Euro 6) | PX-5 190 (Euro 6) | PX-5 210 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.000 rpm","1B Ø150
3.000 rpm",N-E,2014,,TM 21 / QP 21
KC14050362,Kit compresor frío industrial,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2A Ø135
3.100 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050362,Kit compresor frío industrial,,XB170 / XB190 / XB210,PX-5 170 (Euro 6) | PX-5 190 (Euro 6) | PX-5 210 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"2A Ø135
3.100 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050363,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2014,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050363,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2009,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14050363,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6d Temp),2018,,2018,Yes,,,Yes,,,,Yes,,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14060364,Kit compresor frío industrial,MERCEDES,ATEGO,OM934 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.132,any,"6K A Ø145
2.791 rpm",,N,2014,,CR2318 | CR2323
KC14060364,Kit compresor frío industrial,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"6K A Ø145
2.791 rpm",,N,2014,,CR2318 | CR2323
KC14060365,Kit compresor frío industrial,MERCEDES,ANTOS,OM 936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø150
2.958 rpm",,N,2012,,TM 21 / QP 21
KC14060365,Kit compresor frío industrial,MERCEDES,ACTROS,OM 936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø150
2.958 rpm",,N,2012,,TM 21 / QP 21
KC14060366,Kit compresor frío industrial,MERCEDES,ANTOS,OM 936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø135
3.177 rpm",,N,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC14070367,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2014,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2014,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2014,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2016,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2016,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2016,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,2016,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,09/2019,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,09/2019,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,09/2019,,SD5H14 | SD7H15
KC14070367,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 6-8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-S,09/2019,,SD5H14 | SD7H15
KC14070368,Kit compresor frío industrial,RENAULT TRUCKS,SERIE F,4HK1E6H (Euro 6),2014,,2017,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
2.933 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14070369,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+/ Euro 6),2014,,2016,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2014,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC14070369,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 5b+/ Euro 6),2014,,2019,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2014,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC14070369,Kit compresor frío industrial,NISSAN,NV300 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC14070369,Kit compresor frío industrial,FIAT,TALENTO 1.6 Multijet / Ecojet,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC14070369Z,Kit compresor frío industrial,FIAT,TALENTO 1.6 Multijet / Ecojet,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC14070369Z,Kit compresor frío industrial,NISSAN,NV300 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2016,,UP 150 / UPF 150 | UP 170 / UPF 170
KC14070369Z,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 5b+/ Euro 6),2014,,2019,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC14070369Z,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+/ Euro 6),2014,,2016,,,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC14070370,Kit compresor frío industrial,FORD,TRANSIT CUSTOM,2.2 Duratorq TDCi | (Euro 5),2013,,2013,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,2013,,TM 08 / QP 08
KC14070370,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 5),2011,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,06/2011,,TM 08 / QP 08
KC14070370,Kit compresor frío industrial,FORD,TRANSIT,2.2 Duratorq TDCi | (Euro 4),2006,,2011,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.198,no,"Poly-V 8PK Ø119
4.706 rpm","Poly-V 8PK Ø142
3.943 rpm",N-E,06/2006,,TM 08 / QP 08
KC14080372,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080372,Kit compresor frío industrial,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Full) | M9T (Euro VI-D Full),2022,,2024,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2022,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080373,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JJ1E6N-D (Euro 6d Temp),2020,2021,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8K A Ø119
3.453 rpm","Poly-V 8K A Ø119
3.453 rpm",N-E,2020,2021,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080373,Kit compresor frío industrial,,N-Evolution,4JJ1-TCS (Euro 4) | 4JJ1-E5N (Euro 5 EEV),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8K A Ø119
3.453 rpm","Poly-V 8K A Ø119
3.453 rpm",N-E,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080373,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-E5L (Euro 5b+) | 4JJ1E6N (Euro 6),2014,2019,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,"Poly-V 8K A Ø119
3.453 rpm","Poly-V 8K A Ø119
3.453 rpm",N-E,2014,2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080374,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411G*C (Euro 5b+),2014,2019,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,08/2014,09/2019,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14080374,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411C*E (Euro 6) / F1CGL411C*E (Euro 6),2014,2019,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,08/2014,09/2019,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14090375,Kit compresor frío industrial,RENAULT TRUCKS,SERIE F,4HK1E6S (Euro 6),2014,2016,2017,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
2.933 rpm",,N,2014,2016,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC14090376,Kit compresor frío industrial,VOLVO,FL 250,D8K250 (Euro 6) | D8K280 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø135
3.380 rpm",,N,09/2013,,TM 08 / QP 08 | UP 90
KC14090376,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi5 210 (Euro 6) | DTi5 240 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø135
3.380 rpm",,N,09/2013,,TM 08 / QP 08 | UP 90
KC14090376,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
3.150 rpm",,N,09/2013,,TM 08 / QP 08 | UP 90
KC14090376,Kit compresor frío industrial,VOLVO,FL 210,D5K210 (Euro 6) | D5K240 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.100,any,"2A Ø135
3.380 rpm",,N,09/2013,,TM 08 / QP 08 | UP 90
KC14090377,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411G*C (Euro 5b+),2014,2019,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,08/2014,09/2019,TM 21 / QP 21
KC14090377,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411C*E (Euro 6) / F1CGL411C*E (Euro 6),2014,2019,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,08/2014,09/2019,TM 21 / QP 21
KC14090378,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14090378,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 2.298,no,"Poly-V 8K A Ø119
4.353 rpm","Poly-V 8K A Ø119
4.353 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14120379,Kit compresor frío industrial,MERCEDES,VITO,OM622  DE16LA | (Euro 5b+ / Euro 6),2014,2019,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,11/2014,2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120379,Kit compresor frío industrial,MERCEDES,VITO 1.7 FWD,OM622  DE17LA | (Euro 6dtemp),2019,2023,2019,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.749,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,09/2019,2023,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,MERCEDES,VITO,OM622  DE16LA | (Euro 5b+ / Euro 6),2014,2019,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,11/2014,2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+),2014,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2014,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 6),2016,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,NISSAN,NV300 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,FIAT,TALENTO 1.6 Multijet / Ecojet,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120380,Kit compresor frío industrial,MERCEDES,VITO 1.7 FWD,OM622  DE17LA | (Euro 6dtemp),2019,2023,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.749,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,09/2019,2023,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120381,Kit compresor frío industrial,MERCEDES,VITO,OM622  DE16LA | (Euro 5b+ / Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,11/2014,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,MERCEDES,VITO,OM622  DE16LA | (Euro 5b+ / Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,11/2014,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+),2014,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2014,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 6),2016,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,NISSAN,NV300 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14120382,Kit compresor frío industrial,FIAT,TALENTO 1.6 Multijet / Ecojet,R9M (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
4.790 rpm","Poly-V 8K A Ø119
4.790 rpm",N-E,2016,,TM 08 / QP 08 | UP 90
KC14120383,Kit compresor frío industrial,MERCEDES,VITO,OM651 DE22LA | (Euro 5b+ / Euro 6),2014,,2014,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V Ø119
4.695 rpm","Poly-V Ø157
3.560 rpm",N-E/S,2014,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC14120384,Kit compresor frío industrial,MERCEDES,VITO,OM651 DE22LA | (Euro 5b+ / Euro 6),2014,,2014,,,,Yes,,,not,,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V Ø119
4.695 rpm","Poly-V Ø157
3.560 rpm",N-E,11/2014,,TM 08 / QP 08 | UP 90
KC14120385,Kit compresor frío industrial,MERCEDES,VITO,OM651 DE22LA | (Euro 5b+ / Euro 6),2014,,2014,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.143,any,"2A Ø135
3.237 rpm",,N,2014,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC14120386,Kit compresor frío industrial,MERCEDES,VITO,OM651 DE22LA | (Euro 5b+ / Euro 6),2014,,2014,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.143,any,"2A Ø135
3.237 rpm",,N,2014,,TM 08 / QP 08 | UP 90
KC15010387,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15010387,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA (Euro 5),2009,,2018,,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2009,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15010387,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6d Temp),2018,,2018,Yes,,,Yes,,,,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"2A Ø135
3.300 rpm",,N,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15020388,Kit compresor frío industrial,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+/ Euro 6),2014,,2016,,,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2014,,TM 08 / QP 08 | UP 90
KC15020388,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 5b+/ Euro 6),2016,,2019,,,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC15020388,Kit compresor frío industrial,NISSAN,NV300 1.6 dCi,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC15020388,Kit compresor frío industrial,FIAT,TALENTO 1.6 Multijet / Ecojet,R9M (Euro 6),2016,,2016,,,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC15020388,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,R9M (Euro 5b+/ Euro 6),2014,,2019,,,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,2014,,TM 08 / QP 08 | UP 90
KC15050389,Kit compresor frío industrial,ISUZU,NT400 - CABSTAR,ZD30 KE (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 8K A Ø119
4.286 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15050389,Kit compresor frío industrial,NISSAN,MAXITY,DTI 3 (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.953,yes,"Poly-V 8K A Ø119
4.286 rpm","Poly-V 8K A Ø119
4.286 rpm",N-E,2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15050390,Kit compresor frío industrial,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390,Kit compresor frío industrial,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390,Kit compresor frío industrial,PEUGEOT,BOXER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,2024,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,04/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,2024,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,04/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390,Kit compresor frío industrial,CITROEN,JUMPER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,2024,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,04/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390,Kit compresor frío industrial,FIAT,DUCATO,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,2024,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,04/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15050390Z,Kit compresor frío industrial,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø119
3.150 r.p.m.",,N,09/2016,09/2019,UP 150 / UPF 150 | UP 170 / UPF 170
KC15050390Z,Kit compresor frío industrial,PEUGEOT,BOXER,DW12 RU (Euro 6.2 / Euro 6.3),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15050390Z,Kit compresor frío industrial,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø119
3.150 r.p.m.",,N,09/2016,09/2019,UP 150 / UPF 150 | UP 170 / UPF 170
KC15050390Z,Kit compresor frío industrial,CITROEN,JUMPER,DW12 RU (Euro 6.2 / Euro 6.3),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø119
3.150 r.p.m.",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15060391,Kit compresor frío industrial,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15060391,Kit compresor frío industrial,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15060391,Kit compresor frío industrial,PEUGEOT,BOXER,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,no,"Poly-V 8K A Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15060391,Kit compresor frío industrial,CITROEN,JUMPER,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,no,"Poly-V Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15060391,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 2.179,no,"Poly-V 8K A Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15060392,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,,6PK Ø157 2.751 rpm,#¿NOMBRE?,2012,,SD7H15 | SD7L15
KC15060393,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611D | F2CFE611C | F2CFE611B,2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 8K A Ø137
3.260 rpm","Poly-V 8K A Ø137
3.260 rpm",N-E,01/2016,,TM 21 / QP 21
KC15060393-B,Kit compresor frío industrial,IVECO,STRALIS,F2CFE611D (Euro 6) | F2CFE611C (Euro 6) | F2CFE611B (Euro 6),2013,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 8K A Ø137
3.260 rpm",,N,2013,,TM 21 / QP 21
KC15060394,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611D | F2CFE611C | F2CFE611B,2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 7K A Ø137
3.260 rpm",,N,01/2016,,CS150 | CS90
KC15060395,Kit compresor frío industrial,IVECO,STRALIS,Cursor 9 (Euro 6) | F2CFE611D | F2CFE611C | F2CFE611B,2013,2016,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 7K A Ø137
3.260 rpm",,N,01/2013,01/2016,CR2318 | CR2323
KC15070396,Kit compresor frío industrial,,TORA FSR - Euro 5,4HK1-E5S | (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
2.933 rpm",,N,12/2011,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15070397,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 | (Euro 6.1),2016,2018,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.361 rpm","Poly-V 8K A Ø119
3.361 rpm",N-E,2016,2018,TM 08 / QP 08 | UP 90
KC15070397,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 | (Euro 6.1),2016,2018,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.361 rpm","Poly-V 8K A Ø119
3.361 rpm",N-E,2016,2018,TM 08 / QP 08 | UP 90
KC15070398,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070398,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070398,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,,,Yes,Yes,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,11/2011,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070398,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2019,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070398,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2021,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070398Z,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070398Z,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,,,Yes,Yes,,,,,,,,,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm",,N,11/2011,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070398Z,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070398Z,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm","Poly-V 8K A Ø119
3.235 rpm",N-E,09/2014,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070398Z,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
3.235 rpm",,N,09/2021,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070399,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2014,,TM 21 / QP 21
KC15070399,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2014,,TM 21 / QP 21
KC15070399,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2024,,,,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,11/2011,,TM 21 / QP 21
KC15070399,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2019,,TM 21 / QP 21
KC15070399,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2021,,TM 21 / QP 21
KC15070400,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,2019,2024,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø147
3.380 rpm",#¿NOMBRE?,06/2016,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070400,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),,2019,2024,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø147
3.380 rpm",#¿NOMBRE?,,09/2019,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC15070400Z,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,2019,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"1A Ø147
3.380 rpm",,N,06/2016,2019,UP 150 / UPF 150 | UP 170 / UPF 170
KC15070400Z,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"1A Ø147
3.380 rpm",,N,09/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15090402,Kit compresor frío industrial,,ELF 200 / ELF 300,4JJ1-TC | (US EPA 04),2006,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
2.800 rpm",,N,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15090402,Kit compresor frío industrial,ISUZU,NPR 85 / NKR85,4JJ1-TCS | (Euro 4-5),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
3.000 rpm",,N,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15090403,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 EU6d-TEMP BMT,2019,,2019,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,,"Poly-V 6K A Ø125
3.150 rpm",#¿NOMBRE?,10/2019,,TM 13 / QP 13
KC15090403Z,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 EU6d-TEMP BMT,2019,,2019,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V 6K A Ø125
3.150 rpm",,N,10/2019,,UP 150 / UPF 150 | UP 170 / UPF 170
KC15100404,Kit compresor frío industrial,,H350 CRDi,D4CB 2.5 CRDi | (Euro 5b+ / Euro 6),2015,,2015,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.497,any,"Poly-V Ø119
3.449 rpm","Poly-V 8K A Ø119
3.449 rpm",N-E,2015,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15110405,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 BMT | EA288 - Euro 6,2015,2019,2019,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V Ø119
4.058 rpm","Poly-V 8K A Ø119
4.058 rpm",N-E,2015,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC15120407,Kit compresor frío industrial,RENAULT TRUCKS,Serie K,DONGFENG BG 13-20 | Fuel and Bi-fuel Autogas GLP (Euro 5b+),2015,,2020,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.300,no,"2A Ø135
4.888 rpm",,N,2015,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16060408,Kit compresor frío industrial,FORD,TRANSIT CONNECT,DV5 (Euro 6),2016,2018,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.498,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,2016,2018,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,CITROEN,JUMPY,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,TOYOTA,PROACE,1.6D-4D 95 (Euro 6) | 1.6D-4D 115 (Euro 6),2016,,2019,,,,Yes,Yes,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,CITROEN,BERLINGO,DV6 | (Euro 6.1),,2016,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,,2016,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,PEUGEOT,PARTNER,DV6 | (Euro 6.1),,2016,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,,2016,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16060408,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO 2018 (PSA Platform),DV6FDU (Euro 6.1) | DV6FCU (Euro 6.1),2018,,2018,,,,Yes,Yes,,,Yes,,,,,,,,,,,,,,,4 / 1.560,no,"Poly-V Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E/S,09/2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16070409,Kit compresor frío industrial,,500 Series (Euro 2),J05C-TF | (Euro 2),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.307,no,"2A Ø135
3.370 rpm",,N,09/2007,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16070410,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,,2024,,,Yes,,,,ok,Yes,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø147
3.380 rpm",#¿NOMBRE?,06/2016,,TM 08 / QP 08 | UP 90
KC16070411,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16070411,Kit compresor frío industrial,TOYOTA,PROACE,1.6D-4D 95 (Euro 6) | 1.6D-4D 115 (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8PK Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16070411,Kit compresor frío industrial,CITROEN,JUMPY,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8PK Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16080412,Kit compresor frío industrial,CITROEN,JUMPY,DW10FE (Euro 6) | DW10FD (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,09/2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,TOYOTA,PROACE,2.0D-4D 120 (Euro 6) | 2.0D-4D 150 (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,09/2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10FE (Euro 6) | DW10FD (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,09/2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,CITROEN,JUMPY,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,2021,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2019,11/2021,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,2021,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2019,11/2021,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,2021,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2019,11/2021,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412,Kit compresor frío industrial,TOYOTA,PROACE,DW10FE (Euro 6D Temp) | DW10FD (Euro 6D Temp) | DW10FC (Euro 6D Temp),2019,2021,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2019,11/2021,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2019,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2019,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,CITROEN,JUMPY,DW10FE (Euro 6) | DW10FD (Euro 6),2016,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2016,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,CITROEN,JUMPY,DW10FE (Euro 6.2) | DW10FD (Euro 6.2) | DW10FC (Euro 6.2),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2019,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,TOYOTA,PROACE,DW10FE (Euro 6D Temp) | DW10FD (Euro 6D Temp) | DW10FC (Euro 6D Temp),2019,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2019,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10FE (Euro 6) | DW10FD (Euro 6),2016,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2016,,UP 150 / UPF 150
KC16080412Z,Kit compresor frío industrial,TOYOTA,PROACE,2.0D-4D 120 (Euro 6) | 2.0D-4D 150 (Euro 6),2016,,2019,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm",,N,09/2016,,UP 150 / UPF 150
KC16090413,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2021,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
5.546 rpm","Poly-V 6K A Ø142
4.647 rpm",N-E/S,09/2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16090413,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,2018,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
5.546 rpm","Poly-V 6K A Ø142
4.647 rpm",N-E/S,09/2016,2018,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16090413,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2016,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
5.546 rpm","Poly-V 6K A Ø142
4.647 rpm",N-E/S,09/2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16090413,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6d Temp) | 940C1000 (Euro 6d Temp),2019,2021,2021,,,,Yes,Yes,,,Yes,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
5.546 rpm","Poly-V 6K A Ø142
4.647 rpm",N-E/S,09/2019,11/2021,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16090414,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue,YLF6/YLFS (Euro 6) | YMF6/YMFS (Euro 6) | YNF6/YNFS (Euro 6),2016,2019,2016,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,FORD,TRANSIT CUSTOM 2.0 EcoBlue,YLF6/YLFS (Euro 6) | YMF6/YMFS (Euro 6) | YNF6/YNFS (Euro 6),2016,2019,2016,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,FORD,TRANSIT CUSTOM 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6AR / 6EA,BKFB Euro 6EA,2023,,2024,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB Euro 6EA,2023,,2024,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090414,Kit compresor frío industrial,VW,TRANSPORTER T7 - Euro 6,,2023,,2024,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,2018,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2016,2018,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6d Temp) | 940C1000 (Euro 6d Temp),2019,2021,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2019,11/2021,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415D,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415D,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,2018,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2016,2018,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16090415D,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6d Temp) | 940C1000 (Euro 6d Temp),2019,2021,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.598,yes,"2A Ø135
4.888 rpm",,N,09/2019,11/2021,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16100416,Kit compresor frío industrial,FIAT,DOBLO CARGO,225A2000 (Euro 6) | 330A1000 (Euro 6),2016,2019,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
3.750 rpm",,N,09/2016,09/2019,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16100416,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,330A1000 (Euro 6),2016,2019,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.248,no,"2A Ø135
3.750 rpm",,N,09/2016,09/2019,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC16100417,Kit compresor frío industrial,PEUGEOT,EXPERT,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC16100417,Kit compresor frío industrial,CITROEN,JUMPY,DV6FDU (Euro 6) | DV6FCU (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8PK Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC16100417,Kit compresor frío industrial,TOYOTA,PROACE,1.6D-4D 95 (Euro 6) | 1.6D-4D 115 (Euro 6),2016,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8PK Ø119
3.136 rpm","Poly-V 8PK Ø119
3.136 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC16100418,Kit compresor frío industrial,,300 Series (EPA TIER 3),N04C-VB | (EPA TIER 3),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.360 rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110419,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue,YLF6/YLFS (Euro 6) | YMF6/YMFS (Euro 6) | YNF6/YNFS (Euro 6),2016,2019,2016,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110419,Kit compresor frío industrial,FORD,TRANSIT CUSTOM 2.0 EcoBlue,YLF6/YLFS (Euro 6) | YMF6/YMFS (Euro 6) | YNF6/YNFS (Euro 6),2016,2019,2016,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110419,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110419,Kit compresor frío industrial,FORD,TRANSIT CUSTOM 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110419,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6AR / 6EA,BKFB Euro 6EA,2023,2024,2024,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2023,11/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110420,Kit compresor frío industrial,IVECO,EuroCargo Tector 7 4X4,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6),2014,,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,N,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16110420,Kit compresor frío industrial,IVECO,EuroCargo Tector 4X4,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2006,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"2A Ø135
3.520 rpm",,N,10/2006,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16120421,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 BMT | EA288 - Euro 6,2015,,2019,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
3.860 rpm",#¿NOMBRE?,2015,,TM 08 / QP 08 | UP 90
KC16120422,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue,YLR6 (Euro 6) | YMR6 (Euro 6) | YNR6 (Euro 6),2016,,2016,Yes,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V Ø119
3.823 rpm","Poly-V Ø119
3.823 rpm",N-E,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16120422,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLR6 (Euro 6D Temp) | YMR6 (Euro 6D Temp) | YNR6 (Euro 6D Temp),2019,,2019,Yes,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V Ø119
3.823 rpm","Poly-V 8PK Ø119
3.823 rpm",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC16120422,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6EA / 6AR,BKFB Euro 6EA,2023,2024,2024,Yes,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V Ø119
3.823 rpm","Poly-V 8PK Ø119
3.823 rpm",N-E,11/2023,11/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17010423,Kit compresor frío industrial,CITROEN,JUMPY,DW10FE (Euro 6) | DW10FD (Euro 6) | DW10FC (Euro 6),2016,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC17010423,Kit compresor frío industrial,PEUGEOT,EXPERT,DW10FE (Euro 6) | DW10FD (Euro 6) | DW10FC (Euro 6),2016,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC17010423,Kit compresor frío industrial,TOYOTA,PROACE,2.0D-4D 120 (Euro 6) | 2.0D-4D 150 (Euro 6) | 2.0D-4D 180 (Euro 6),2016,,2019,,,,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC17010424,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue,YLR6 (Euro 6) | YMR6 (Euro 6) | YNR6 (Euro 6),2016,,2016,Yes,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,2016,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17010424,Kit compresor frío industrial,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLR6 (Euro 6D Temp) | YMR6 (Euro 6D Temp) | YNR6 (Euro 6D Temp),2019,,2019,Yes,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17010424,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6EA / 6AR,BKFB Euro 6EA,2023,,2024,Yes,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø119
4.647 rpm","Poly-V 8PK Ø157
3.522 rpm",N-E,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17010425,Kit compresor frío industrial,MAN,TGS,D2066 SCR 360 (Euro 5) | D2066 SCR 400 (Euro 5) | D2066 SCR 440 (Euro 5),2012,,2012,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.518,any,"Poly-V 8K A Ø137
3.340 rpm",,N,2012,,TM 21 / QP 21
KC17020426,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2014,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC17020426,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 5K A Ø138
3.018 r.p.m.",N-E,2016,,TM 08 / QP 08 | UP 90
KC17020427,Kit compresor frío industrial,FIAT,DOBLO CARGO,198A4000 CNG (Euro 6),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17020427,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A14FCCNG (Euro 6),2010,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17020427,Kit compresor frío industrial,FIAT,DOBLO CARGO,1.4 Petrol (Euro 6D Temp) | 1.4 CNG (Euro 6D Temp),2019,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,09/2019,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17020428,Kit compresor frío industrial,FIAT,DOBLO CARGO,843A1000 (Euro 6),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17020428,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A14FP (Euro 6),2012,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2012,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17020428,Kit compresor frío industrial,FIAT,DOBLO CARGO,1.4 Petrol (Euro 6D Temp),2019,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,no,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,09/2019,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17030429,Kit compresor frío industrial,FIAT,DOBLO CARGO,843A1000 (Euro 6),2010,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2010,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17030429,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,A14FP (Euro 6),2012,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2012,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17030429,Kit compresor frío industrial,FIAT,DOBLO CARGO,1.4 Petrol (Euro 6D Temp),2019,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.368,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,09/2019,,SD5H14 | SD5L14 | TM 13 / QP 13 | UP 120 / UPF 120
KC17030432,Kit compresor frío industrial,FORD,TRANSIT 3.7L V6,Ti-VCT V6,2019,,2019,,,,,,,,,,,,,,,,,,,,,,,3700-06-01 00:00:00,any,"Poly-V 8PK Ø119
5224 rpm",,N,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17050434,Kit compresor frío industrial,,300 Series (Euro 1 / Euro 2),W04D-J (Euro 1) | W04D-TN (Euro 2),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,no,"2A Ø135
3.440 rpm / 2.690rpm",,N,09/2007,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17050435,Kit compresor frío industrial,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC17050435,Kit compresor frío industrial,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V Ø119
4.790 r.p.m.","Poly-V 8K A Ø119
4.790 r.p.m.",N-E,09/2016,,TM 08 / QP 08 | UP 90
KC17060436,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,2018,2016,,,,Yes,,,,,,,,,,Yes,,,,,,,,,4 / 1.598,no,"2A Ø135
3.496 rpm",,N,09/2016,2018,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17060436,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,Yes,,,,,,,,,4 / 1.598,no,"2A Ø135
3.496 rpm",,N,09/2016,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17060436,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6) | 940C1000 (Euro 6),2016,,2021,,,,Yes,,,,,,,,,,Yes,,,,,,,,,4 / 1.598,no,"2A Ø135
3.496 rpm",,N,09/2016,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17060436,Kit compresor frío industrial,FIAT,DOBLO CARGO,263A8000 (Euro 6d Temp) | 940C1000 (Euro 6d Temp),2019,2021,2021,,,,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 1.598,no,"2A Ø135
3.496 rpm",,N,09/2019,11/2021,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17060437,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V k Ø119
4.175 rpm","Poly-V k Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17060437,Kit compresor frío industrial,VW,TGE 2.0 TDI - FWD,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-VK Ø119
4.175 rpm","Poly-Vk Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070438,Kit compresor frío industrial,PEUGEOT,BOXER,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 2.179,no,"Poly-V 8K A Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070438,Kit compresor frío industrial,CITROEN,JUMPER,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 2.179,no,"Poly-V 8K A Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070438,Kit compresor frío industrial,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070438,Kit compresor frío industrial,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2016,09/2019,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070438,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,Yes,,,,,,,,,Yes,,,,,,,,,4 / 2.179,no,"Poly-V 8K A Ø119
3.150 r.p.m.","Poly-V 8K A Ø119
3.150 r.p.m.",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17070439,Kit compresor frío industrial,,D-MAX N57 / N60,RZ4E (Euro 6),2017,2022,2017,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,07/2017,12/2022,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17070440,Kit compresor frío industrial,RENAULT,KANGOO 1.3 TCe (HR13),1.3 Petrol (Euro 6d-full),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.333,no,,"Poly-V 7K A Ø119
4.500 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13
KC17070440,Kit compresor frío industrial,,CITAN 110/113,1.3 Petrol (Euro 6d-full) | M200.73,2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.333,no,,"Poly-V 7K A Ø119
4.500 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13
KC17070440,Kit compresor frío industrial,,TOWNSTAR 1.3 TCe (HR13),1.3 Petrol (Euro 6d-full),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.333,no,,"Poly-V 7K A Ø119
4.500 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13
KC17070440,Kit compresor frío industrial,CITROEN,EXPRESS VAN 1.3 TCe (HR13),1.3 Petrol (Euro 6d-full),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.333,no,,"Poly-V 7K A Ø119
4.500 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13
KC17080441,Kit compresor frío industrial,RENAULT TRUCKS,"SERIE-N 3,5t",RZ4EE6N-L  (Euro 6b-1),2017,2020,2017,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8PK Ø119
2.800 rpm","Poly-V 8PK Ø119
2.800 rpm",N-E,07/2017,06/2020,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17090442,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,6PK Ø95 4547 rpm / 6PK Ø115 3756 rpm,,N,2012,,CR150 | CS150 | CS90
KC17090442,Kit compresor frío industrial,MERCEDES,ACTROS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,6PK Ø95 4547 rpm / 6PK Ø115 3756 rpm,,N,2012,,CR150 | CS150 | CS90
KC17110443,Kit compresor frío industrial,VW,CADDY,TDI 2.0 BMT | EA288 - Euro 6,2015,2021,2015,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
4.416 rpm",#¿NOMBRE?,2015,02/2021,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17110445,Kit compresor frío industrial,VW,CADDY,TDI 2.0 BMT | EA288 - Euro 6,2015,2020,2015,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"Poly-V Ø119
3.361 rpm","Poly-V 8K A Ø119
3.361 rpm",N-E,2015,2020,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC17110446,Kit compresor frío industrial,RENAULT TRUCKS,"SERIE-N 3,5t",RZ4EE6N-L  (Euro 6b-1),2017,2020,2017,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,yes,"Poly-V 8PK Ø119
2.800 rpm","Poly-V 8PK Ø119
2.800 rpm",N-E,07/2017,06/2020,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17110447,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.170 rpm",,N,11/2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17110447,Kit compresor frío industrial,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.170 rpm",,N,11/2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17110447,Kit compresor frío industrial,MAN,TGL,D0834 LFL (Euro 6e) | D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"2A Ø135
3.170 rpm",,N,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17110447,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"2A Ø135
3.170 rpm",,N,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC17110448,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-E6N (Euro 6),2014,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,,"Poly-V 5K A Ø125
3.225 rpm",#¿NOMBRE?,2014,,TM 21 / QP 21
KC17110448,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JJ1-E6N-D (Euro 6d Temp),2020,2021,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,any,,"Poly-V 5K A Ø125
3.225 rpm",#¿NOMBRE?,2020,2021,TM 21 / QP 21
KC17110449,Kit compresor frío industrial,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,11/2017,,TM 21 / QP 21
KC17110449,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,11/2017,,TM 21 / QP 21
KC17110449,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,09/2021,,TM 21 / QP 21
KC17110449,Kit compresor frío industrial,MAN,TGL,D0834 LFL (Euro 6e) | D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø150
3.152 rpm","1B Ø150
3.152 rpm",N-E,09/2021,,TM 21 / QP 21
KC17120450,Kit compresor frío industrial,,HILUX 2.4 D-4D,2.4L D-4D | 2GD-FTV Euro6,2017,2019,2017,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.393,any,"Poly-V 8K A Ø119
3.200 rpm","Poly-V 8K A Ø119
3.200 rpm",N-E,11/2017,10/2019,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18010451,Kit compresor frío industrial,,C31 / C32,DK 15-06 (Euro 5),2017,,2017,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,2017,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18010452,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,M9R (Euro 6d temp),2019,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18010452,Kit compresor frío industrial,NISSAN,NV300 2.0 dCi,M9R (Euro 6d temp),2019,,2019,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18010452,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6d temp),2019,,2021,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18010452,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6D Full),2021,,2021,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18010452,Kit compresor frío industrial,NISSAN,PRIMASTAR 2.0 dCi,M9R (Euro 6D Full),2022,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18010452,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,M9R (Euro 6D Full),2022,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 8K A Ø119
4.441 r.p.m.","Poly-V 8K A Ø119
4.441 r.p.m.",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18020453,Kit compresor frío industrial,VW,TGE 2.0 TDI - RWD,2.0 TDI EA288 (Euro 6 / Euro 6d-Temp),2017,,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V Ø119
4.175 rpm","Poly-V Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18020453,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / Euro 6d-Temp),2017,,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8k Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18020454,Kit compresor frío industrial,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"Poly-V 8K A Ø119
4.850 rpm","Poly-V 8K A Ø142
4.060 rpm",N-E,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18020454,Kit compresor frío industrial,,XB170 / XB190 / XB210,PX-5 170 (Euro 6) | PX-5 190 (Euro 6) | PX-5 210 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"Poly-V 8K A Ø119
4.850 rpm","Poly-V 8K A Ø142
4.060 rpm",N-E,2014,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18040455,Kit compresor frío industrial,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø155
3.050 rpm",,N,11/2017,,CR2318 | CR2323
KC18040455,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø155
3.050 rpm",,N,11/2017,,CR2318 | CR2323
KC18040455,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø155
3.050 rpm",,N,09/2021,,CR2318 | CR2323
KC18040455,Kit compresor frío industrial,MAN,TGL,D0834 LFL (Euro 6e) | D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø155
3.050 rpm",,N,09/2021,,CR2318 | CR2323
KC18040456,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,11/2017,,CS150 | CS90
KC18040456,Kit compresor frío industrial,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,11/2017,,CS150 | CS90
KC18040456,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,09/2021,,CS150 | CS90
KC18040456,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",any,"1B Ø128
3.694 rpm / 1B Ø134
3.528 rpm",,N,09/2021,,CS150 | CS90
KC18050459,Kit compresor frío industrial,,P280 / P320 / P360,"DC09 130 (Euro 6) | DC09 126 (Euro 6) | DC09 127 (Euro 6) | DC09 139 (Euro 6) | OC09 104 (CNG/LNG, Euro 6) | OC09 105 (CNG/LNG, Euro 6)",2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,"Poly-V 8K A Ø119
3.911 rpm","Poly-V 8K A Ø119
3.911 rpm",N-E,2018,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050460,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"2A Ø135
3.170 rpm",,N,11/2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050460,Kit compresor frío industrial,MAN,TGM,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"2A Ø135
3.170 rpm",,N,11/2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050460,Kit compresor frío industrial,MAN,TGL,D0834 LFL (Euro 6e) | D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"2A Ø135
3.170 rpm",,N,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050460,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,yes,"2A Ø135
3.170 rpm",,N,09/2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050461,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA | (Euro 6d Temp),2018,,2018,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,yes,"Poly-V 8K A Ø119
3.575 rpm","Poly-V 8K A Ø119
3.575 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18050461,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6c Gr.III/ VI-C),2018,,2018,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,yes,"Poly-V 8K A Ø119
3.575 rpm","Poly-V 8K A Ø119
3.575 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18060462,Kit compresor frío industrial,RENAULT TRUCKS,SERIE F,4HK1E6S (Euro 6C),2017,,2017,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
2.933 rpm",,N,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18070463,Kit compresor frío industrial,,P220 / P250 / P280,DC07 111 (Euro 6) | DC07 112 (Euro 6) | DC07 113 (Euro 6),2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.700,yes,"Poly-V 8K A Ø119
5.765 rpm","Poly-V 8K A Ø119
5.765 rpm",N-E,2018,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18070464,Kit compresor frío industrial,,P280 / P320 / P360,"DC09 130 (Euro 6) | DC09 126 (Euro 6) | DC09 127 (Euro 6) | DC09 139 (Euro 6) | OC09 104 (CNG/LNG, Euro 6) | OC09 105 (CNG/LNG, Euro 6)",2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,,"Poly-V 5K A Ø125
3.730 rpm",#¿NOMBRE?,2018,,TM 21 / QP 21
KC18070465,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE0481A-F / F1AE0481B-G (Euro 3-4) | F1AE0481M-H (Euro 3-4) | F1AE0481U/ F1AE0481V (Euro 4),2002,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,2002,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC18070465,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,11/2011,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC18070465,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,08/2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC18070465,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC18070465,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120
KC18070465-G,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18070465-H,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC18080467,Kit compresor frío industrial,RENAULT,KANGOO 1.5,K9K Gen8 (Euro 6d-full),2019,,2019,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC18080467,Kit compresor frío industrial,,NV250 1.5 dCi,K9K Gen8 (Euro 6dtemp),2019,2023,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,2023,TM 13 / QP 13
KC18080467,Kit compresor frío industrial,,CITAN 1.5,OM 608 DE 15 LA (Euro 6dtemp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC18080467,Kit compresor frío industrial,,DOKKER 1.5,K9K Gen8 (Euro 6dtemp),2019,2023,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,2023,TM 13 / QP 13
KC18080467,Kit compresor frío industrial,CITROEN,EXPRESS VAN 1.5,K9K Gen8 (Euro 6d-full),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC18080467,Kit compresor frío industrial,,CITAN 1.5,OM 608 DE 15 LA (Euro 6d-full),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC18090468,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,2024,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
2.941 rpm",,N,09/2019,08/2024,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18090468,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
2.941 rpm",,N,09/2021,08/2024,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18090468-A,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,2024,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
2.941 rpm",,N,09/2014,08/2024,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18100469,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,1A Ø128 4375 rpm / 1A Ø134 4179 rpm,,N,09/2014,,CS150 | CS90
KC18100469,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,1A Ø128 4375 rpm / 1A Ø134 4179 rpm,,N,09/2019,,CS150 | CS90
KC18100469,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,1A Ø128 4375 rpm / 1A Ø134 4179 rpm,,N,09/2021,09/2024,CS150 | CS90
KC18100469-B,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,2024,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,1A Ø128 4375 rpm / 1A Ø134 4179 rpm,,N,09/2021,09/2024,CS150 | CS90
KC18100470,Kit compresor frío industrial,CITROEN,BERLINGO 2018,DV6 | (Euro 6.1),2018,,2018,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18100470,Kit compresor frío industrial,PEUGEOT,PARTNER 2018,DV6 | (Euro 6.1),2018,,2018,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18100470,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO 2018 (PSA Platform),DV6 | (Euro 6.1),2018,,2018,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.560,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18110471,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,,Yes,,,,,,,Yes,,,,,,,4 / 2.143,any,"Poly-V Ø119
4.660 rpm","Poly-V 6K A Ø157
3.530 rpm",N-E/S,2014,,SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18110472,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,,Yes,,,,,,,,Yes,,,,,,4 / 2.143,any,"Poly-V Ø109
3.800 rpm","Poly-V 8K A Ø119
3.480 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18110473,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,Yes,,,Yes,,,,,Yes,,,,,,,,Yes,,,,,,4 / 2.143,any,"Poly-V 8K A Ø119
3.480 rpm","Poly-V 8K A Ø119
3.480 rpm",N-E,2014,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18120474,Kit compresor frío industrial,PEUGEOT,PARTNER,DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18120474,Kit compresor frío industrial,CITROEN,BERLINGO,DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18120474,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO (PSA Platform),DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2022,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18120474,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO,DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2018,,,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC18120475,Kit compresor frío industrial,MERCEDES,SPRINTER,OM 651 DE22 LA | (Euro 6d Temp),2018,,2018,,Yes,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V 8K A Ø119
5.100 rpm","Poly-V 8K A Ø157
3.870 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC18120475,Kit compresor frío industrial,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6c Gr.III/ VI-C),2018,,2018,,Yes,,Yes,,,,Yes,,,,,,,,,,,,,,,4 / 2.143,no,"Poly-V 8K A Ø119
5.100 rpm","Poly-V 8K A Ø157
3.870 rpm",N-E/S,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19010476,Kit compresor frío industrial,IVECO,EuroCargo Tector 6 CNG,F4GFE601A (Euro VI B/C) - CNG,2015,2019,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 5.880,any,,"1B Ø156
3.012 rpm",#¿NOMBRE?,2015,09/2019,TM 21 / QP 21
KC19010477,Kit compresor frío industrial,MERCEDES,Econic 1827/1830/1835,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"2A Ø145
2.791 rpm",,N,2014,,TM 21 / QP 21
KC19020481,Kit compresor frío industrial,PEUGEOT,PARTNER,DV5 RE (Euro 6.2 / Euro 6.3) | DV5 RD (Euro 6.2 / Euro 6.3) | DV5 RC (Euro 6.2 / Euro 6.3),2018,2022,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,02/2022,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,CITROEN,BERLINGO,DV5 RE (Euro 6.2 / Euro 6.3) | DV5 RD (Euro 6.2 / Euro 6.3) | DV5 RC (Euro 6.2 / Euro 6.3),2018,2022,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,02/2022,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO (PSA Platform),DV5 RE (Euro 6.2 / Euro 6.3) | DV5 RD (Euro 6.2 / Euro 6.3) | DV5 RC (Euro 6.2 / Euro 6.3),2018,2022,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,02/2022,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO,DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2018,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,TOYOTA,PROACE,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,CITROEN,JUMPY,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,PEUGEOT,EXPERT,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 1.5D,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,TOYOTA,PROACE CITY 1.5 BlueHDi,DV5 RE (Euro 6.2 / Euro 6.3) | DV5 RD (Euro 6.2 / Euro 6.3) | DV5 RC (Euro 6.2 / Euro 6.3),2020,2022,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2020,02/2022,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,CITROEN,JUMPY 1.5 BlueHDi,DV5 (Euro 6.3 / Euro 6.4),2021,2024,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,PEUGEOT,EXPERT 1.5 BlueHDi,DV5 (Euro 6.3),2021,2024,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,FIAT,SCUDO 1.5,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,TOYOTA,PROACE 1.5D,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,CITROEN,JUMPY 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,PEUGEOT,EXPERT 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,FIAT,SCUDO 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,TOYOTA,PROACE 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19020481,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19030482,Kit compresor frío industrial,,MAXUS V80,VM ECO-D Euro VI 2.5,2019,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.499 ,yes,"Poly-V Ø119
3.097 rpm","Poly-V 8K A Ø119
3.097 rpm",N-E,2019,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19030483,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-TCS (Euro 4) | 4JJ1-E5N (Euro 5 EEV),2006,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Poly-V Ø119
3.453 rpm","Poly-V 8K A Ø119
3.453 rpm",N-E,2006,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19030483,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-E5L (Euro 5b+) | 4JJ1-E6N (Euro 6),2014,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Poly-V Ø119
3.453 rpm","Poly-V 8K A Ø119
3.453 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040484,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro6,4HK1-E6C | (Euro6),2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040484,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-E,4HK1- Euro VI OBD-D,2019,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040484,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 6D / VI E,4HK1-E6C | (Euro 6D / VI E),2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 5.193,any,"2A Ø135
3.177 rpm",,N,2018,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040485,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro 5b+ / Euro6 SÃ©rie Bleu,4JJ1-E5L (Euro 5b+) | 4JJ1-E6N (Euro 6),2014,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
2.800 rpm",,N,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040485,Kit compresor frío industrial,,ELF 200 / ELF 300,4JJ1-TC | (US EPA 04),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"2A Ø135
2.800 rpm",,N,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19040486,Kit compresor frío industrial,FORD,TRANSIT CONNECT 1.5,1.5 TDCI EcoBlue (Euro 6.2),2019,2023,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.498,yes,"Poly-V 8K A Ø119
3.412 rpm","Poly-V 8K A Ø119
3.412 rpm",N-E,2019,2023,TM 13 / QP 13
KC19050487,Kit compresor frío industrial,FORD,TRANSIT CONNECT 1.5,1.5 TDCI EcoBlue (Euro 6.2),2019,2023,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.498,no,"Poly-V 8K A Ø119
5.109 rpm","Poly-V 6K A Ø142
4.281 rpm",N-E,2019,2023,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150
KC19060488,Kit compresor frío industrial,,NP300,QR25DE (petrol),2015,,2015,,,,,,,,,,,,,,,,,,,,,,,4 / 2.488,any,"Poly-V 6K/8K A Ø119
4.740 r.p.m.",,N,2015,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150
KC19060489,Kit compresor frío industrial,VOLVO,FE 250,D8K250 (Euro 6) | D8K280 (Euro 6) | D8K320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,TM 21 / QP 21
KC19060489,Kit compresor frío industrial,ISUZU,- D Wide CAB 2.3 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6) | DTi8 320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,no,,"Poly-V 8P Ø157
3.685rpm",#¿NOMBRE?,09/2013,,TM 21 / QP 21
KC19060490,Kit compresor frío industrial,ISUZU,- CAB 2.3 m -,DTI 11 380 (Euro 6) | DTI 11 430 (Euro 6),2016,,2016,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.800,any,,"1A Ø135
5.833 rpm",#¿NOMBRE?,09/2016,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070491,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,M9R (Euro 6d temp),2019,2021,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,12/2021,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC19070491,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6d temp),2019,,2021,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC19070491,Kit compresor frío industrial,NISSAN,NV300 2.0 dCi,M9R (Euro 6d temp),2019,2021,2019,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,12/2021,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC19070491,Kit compresor frío industrial,CITROEN,EXPRESS 2.0 dCi,M9R (Euro 6d temp),2019,2021,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,12/2021,TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120
KC19070492,Kit compresor frío industrial,PEUGEOT,PARTNER,DV5 (Euro 6.2 / Euro 6.3 / Euro 6.4),2018,2024,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,05/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,CITROEN,BERLINGO,DV5 (Euro 6.2 / Euro 6.3 / Euro 6.4),2018,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO (PSA Platform),DV5 (Euro 6.2 / Euro 6.3 / Euro 6.4),2018,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO,DV5 RE (Euro 6.2) | DV5 RD (Euro 6.2) | DV5 RC (Euro 6.2),2018,,2018,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,TOYOTA,PROACE,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,CITROEN,JUMPY,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,CITROEN,JUMPY 1.5 BlueHDi,DV5 (Euro 6.3 / Euro 6.4),2021,2024,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,PEUGEOT,EXPERT,DV5 (Euro 6.2),2018,,2019,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2018,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,TOYOTA,PROACE CITY 1.5 BlueHDi,DV5 (Euro 6.2 / Euro 6.3 / Euro 6.4),2020,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2020,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,PEUGEOT,EXPERT 1.5 BlueHDi,DV5 (Euro 6.3),2021,2024,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 1.5D,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,FIAT,SCUDO 1.5,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,TOYOTA,PROACE 1.5D,DV5 (Euro 6.3),2021,2024,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2021,04/2024,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,,DOBLÃ“,DV5 (Euro 6.3 / Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,CITROEN,JUMPY 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,PEUGEOT,EXPERT 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,FIAT,SCUDO 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,TOYOTA,PROACE 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19070492,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 1.5 BlueHDi,DV5 (Euro 6.4),2024,,2024,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,no,"Poly-V 8K A Ø119
4.800 rpm","Poly-V 6K A Ø142
4.035 rpm",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19090493,Kit compresor frío industrial,FORD,TRANSIT / CUSTOM 2.0 EcoBlue,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,2023,2019,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,09/2019,2023,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150
KC19090494,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 4) | DXi7 (Euro 4),2006,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,06/2006,,TM 21 / QP 21
KC19090494,Kit compresor frío industrial,RENAULT TRUCKS,MIDLUM,DXi5 (Euro 5) | DXi7 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,"4 / 4.760_x000D_
6 / 7.150",any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,09/2010,,TM 21 / QP 21
KC19090494,Kit compresor frío industrial,VOLVO,FL 240,D7E240 (Euro 4) | D7E280 (Euro 4),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,2007,,TM 21 / QP 21
KC19090494,Kit compresor frío industrial,VOLVO,FL240,D7F240 (Euro 5) | D7F260 (Euro 5) | D7F290 (Euro 5),2010,,2010,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.150,any,"1B Ø150
3.710 rpm","1B Ø150
3.710 rpm",N-E,09/2010,,TM 21 / QP 21
KC19110495,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro VI-D) | F4AFE611E*N (Euro VI-D),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,N,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170
KC19110496,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro VI-D) | F4AFE611E*N (Euro VI-D),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"2A Ø135
3.520 rpm",,#¿NOMBRE?,09/2019,,TM 21 / QP 21
KC19120497,Kit compresor frío industrial,RENAULT,KANGOO 1.5,K9K Gen8 (Euro 6d-full),2019,,2019,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC19120497,Kit compresor frío industrial,,NV250 1.5 dCi,K9K Gen8 (Euro 6dtemp),2019,2023,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,2023,TM 13 / QP 13
KC19120497,Kit compresor frío industrial,,CITAN 1.5,OM 608 DE 15 LA (Euro 6dtemp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC19120497,Kit compresor frío industrial,,DOKKER 1.5,K9K Gen8 (Euro 6dtemp),2019,2023,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,2023,TM 13 / QP 13
KC19120497,Kit compresor frío industrial,,CITAN 1.5,OM 608 DE 15 LA (Euro 6d-full),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.461,no,"Poly-V 8K A Ø119
4.750 rpm","Poly-V 8K A Ø119
4.750 rpm",N-E,09/2019,,TM 13 / QP 13
KC20010498,Kit compresor frío industrial,FORD,TRANSIT / CUSTOM 2.0 EcoBlue,YLR6 (Euro 6D Temp) | YMR6 (Euro 6D Temp) | YNR6 (Euro 6D Temp),2019,,2019,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.941 rpm","Poly-V 8PK Ø119
3.941 rpm",N-E,09/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20050500,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2022,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V K Ø119
5.332 rpm","Poly-V K Ø157
4.042 rpm",N-E/S,2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20060501,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2022,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø137
4.632 rpm","Poly-V 8K A Ø137
4.632 rpm",N-E,2021,,TM 21 / QP 21
KC20060501-A,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2022,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø137
4.632 rpm","Poly-V 8K A Ø137
4.632 rpm",N-E,2021,,TM 21 / QP 21
KC20070502,Kit compresor frío industrial,MAN,TGS/TGX,D1556LF09 (Euro 6D Temp) | D1556LF08 (Euro 6D Temp) | D1556LF07 (Euro 6D Temp) | D1556LF17 (Euro 6e) | D1556LF18 (Euro 6e) | D1556LF19 (Euro 6e),2020,,2020,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.037,any,"Poly-V 7K A Ø115
4.950 rpm",,N,2020,,CS150
KC20070503,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,RZ4E-TC (Euro 6d-temp),2020,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8PK Ø119
2.800 rpm","Poly-V 8PK Ø119
2.800 rpm",N-E,06/2020,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20070503-A,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,RZ4E-TC (Euro 6d-temp),2020,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8PK Ø119
2.800 rpm","Poly-V 8PK Ø119
2.800 rpm",N-E,06/2020,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20070504,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,RZ4E-TC (Euro 6d-temp),2020,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,yes,"Poly-V 8PK Ø119
2.800 rpm","Poly-V 8PK Ø119
2.800 rpm",N-E,06/2020,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20080505,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V Ø119
3.227 rpm","Poly-V 8K A Ø119
3.227 rpm",N-E,09/2019,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20080505,Kit compresor frío industrial,FIAT,DUCATO,F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Poly-V Ø119
3.227 rpm","Poly-V 8K A Ø119
3.227 rpm",N-E,2014,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20080506,Kit compresor frío industrial,,PORTER NP6 1.5,EURO 6d-full (petrol/LPG & petrol/methane),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.498,any,"Poly-V Ø119
6.403 rpm","Poly-V 8PK Ø157
4.854 rpm",N-E,2021,,TM 13 / QP 13
KC20080507,Kit compresor frío industrial,CITROEN,EXPRESS 1.6 dCi,R9M (Euro 6),2019,,2019,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.598,any,"Poly-V 8K A Ø119
3.500 r.p.m.",,N,2019,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20080508,Kit compresor frío industrial,RENAULT TRUCKS,Serie K,DONG FENG DK12-06,2020,,2020,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.240,no,"8PK Ø119
3509 rpm",,N,2020,,TM 13 / QP 13
KC20090510,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2022,Yes,,Yes,Yes,,,,,,,,,,,,Yes,Yes,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
3.640 rpm","Poly-V 8K A Ø119
3.640 rpm",N-E,2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC20120512,Kit compresor frío industrial,,RANGER 2.0 EcoBlue TDCi,2.0L EcoBlue TDCi 170CV (125kW) | 2.0L EcoBlue TDCi  213CV (157kW),2019,2022,2023,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8K A Ø119
3.588 rpm","Poly-V 8K A Ø119
3.588 rpm",N-E,09/2019,12/2022,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC21020513,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,no,"Poly-V 8K A Ø119
4.850 rpm","Poly-V 8K A Ø157
3.675 rpm",N-E,09/2021,04/2024,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21020514,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
3.441 rpm","Poly-V 8K A Ø119
3.441 rpm",N-E,09/2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21020514,Kit compresor frío industrial,PEUGEOT,BOXER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
3.441 rpm","Poly-V 8K A Ø119
3.441 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21020514,Kit compresor frío industrial,CITROEN,JUMPER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
3.441 rpm","Poly-V 8K A Ø119
3.441 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21020514,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
3.441 rpm","Poly-V 8K A Ø119
3.441 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21050517,Kit compresor frío industrial,FORD,TRANSIT CONNECT 2.0 EcoBoost,2.0 Euro 6e EcoBoost,2024,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
4.416 rpm",#¿NOMBRE?,2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC21050517,Kit compresor frío industrial,VW,CADDY 2021,TDI 2.0 BMT | DTRF / DTRE / DPBC/ DTRC - Euro 6D Temp,2021,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,,"Poly-V 6K A Ø125
4.416 rpm",#¿NOMBRE?,02/2021,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC21070524,Kit compresor frío industrial,,P280 / P320 / P360,"OC09 104 (CNG/LNG, Euro 6) | OC09 105 (CNG/LNG, Euro 6)",2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,5 / 9.300,any,,"Poly-V 8K A Ø127
3.665 rpm",#¿NOMBRE?,2018,,QP 25
KC21080525,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2022,,2022,,Yes,,Yes,,,,,,,,,,,,Yes,Yes,,,,,,4 / 1.950,yes,"Poly-V 8K A Ø119
3.575 rpm","Poly-V 8K A Ø119
3.575 rpm",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21080526,Kit compresor frío industrial,MAN,TGL,D0834 LFL 77/78/79 (Euro 6c) | D0836 LFL 79 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"1B Ø150
3.968 rpm","1B Ø162
3.674 rpm",N-E,11/2017,,QP 25
KC21080526,Kit compresor frío industrial,MAN,TGM,D0836 LFL 79/80/81 (Euro 6c),2017,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,yes,"1B Ø150
3.968 rpm","1B Ø162
3.674 rpm",N-E,11/2017,,QP 25
KC21080526,Kit compresor frío industrial,MAN,TGL,D0834 LFL (Euro 6e) | D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,"4 / 4.580_x000D_
6 / 6.871",yes,"1B Ø150
3.968 rpm","1B Ø162
3.674 rpm",N-E,09/2021,,QP 25
KC21080526,Kit compresor frío industrial,MAN,TGM,D0836 LFL (Euro 6e),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,Yes,,6 / 6.871,yes,"1B Ø150
3.968 rpm","1B Ø162
3.674 rpm",N-E,09/2021,,QP 25
KC21090527,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.750 rpm",,N,09/2019,,QP 25
KC21090528,Kit compresor frío industrial,IVECO,EuroCargo Tector 5 ML120E19 / ML140E19,F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,4 / 4.485,any,"1B Ø150
3.750 rpm",,N,09/2019,,QP 25
KC21090529,Kit compresor frío industrial,MAN,TGS/TGX,D1556LF09 (Euro 6D Temp) | D1556LF08 (Euro 6D Temp) | D1556LF07 (Euro 6D Temp) | D1556LF17 (Euro 6e) | D1556LF18 (Euro 6e) | D1556LF19 (Euro 6e),2020,,2020,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 9.037,any,"Poly-V 8K A Ø137
4.150 rpm",,N,2020,,QP 25
KC21090530,Kit compresor frío industrial,,XB230 / XB260 / XB290 / XB310,PX-7 (Euro 6) | PX-7 (Euro 6) | PX-7 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.750 rpm",,N,2014,,QP 25
KC21090530,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.750 rpm",,N,2014,,QP 25
KC21090530-A,Kit compresor frío industrial,DAF,LF220 / LF250 / LF280,"PX-7 164,172 (Euro 6) | PX-7 186,194 (Euro 6) | PX-7  208, 217 (Euro 6)",2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 6.690,any,"1B Ø150
3.750 rpm",,N,2014,,QP 25
KC21090531,Kit compresor frío industrial,DAF,LF150 / LF180 / LF210,PX-5 112 (Euro 6) | PX-5 135 (Euro 6) | PX-5 157 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.600 rpm",,N,2014,,QP 25
KC21090531,Kit compresor frío industrial,,XB170 / XB190 / XB210,PX-5 170 (Euro 6) | PX-5 190 (Euro 6) | PX-5 210 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.500,any,"1B Ø150
3.600 rpm",,N,2014,,QP 25
KC21090532,Kit compresor frío industrial,,R370 / R410 / R450 / R500 / R540,DC13 EURO6,2021,,2022,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.700,any,"Poly-V 8K A Ø119
3.360 rpm","Poly-V 8K A Ø119
3.360 rpm",N-E,2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21110533,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2022,,2022,,Yes,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
5.524 rpm","Poly-V 8K A Ø157
4.187 rpm",N-E/S,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21110535,Kit compresor frío industrial,,GAZelle Next EA189 2.0 TDI - RWD,2.0 TDI EA189 - EURO 6,2021,,2021,Yes,,,,,,,,,,,,,,,,,,,,,,4 / 1.968,yes,"Poly-V 8K A Ø119
4.058 rpm","Poly-V 8k Ø157
3.076 rpm",N-E,2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC21110536,Kit compresor frío industrial,,MAXUS DELIVER 9 FWD,Euro 6.2,2021,,2021,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.996,yes,"Poly-V Ø119
3.576 rpm","Poly-V 8K A Ø119
3.576 rpm",N-E,2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22010537,Kit compresor frío industrial,CITROEN,JUMPY 2.0 BlueHDi,DW10 (Euro 6.3),2021,2024,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,11/2021,04/2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC22010537,Kit compresor frío industrial,PEUGEOT,EXPERT 2.0 BlueHDi,DW10 (Euro 6.3),2021,2024,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,11/2021,04/2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC22010537,Kit compresor frío industrial,FIAT,SCUDO 2.0,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,11/2021,05/2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC22010537,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 2.0D,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,11/2021,05/2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC22010537,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,11/2021,05/2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC22010538,Kit compresor frío industrial,FIAT,DOBLO CARGO,Multijet 1.6 Euro 6D Full,2021,,2021,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.598,no,"Poly-V Ø119
5546 rpm","Poly-V 8K A Ø119
5546 rpm",N-E,11/2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22020540,Kit compresor frío industrial,MERCEDES,ANTOS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,"8PK Ø 119
3650 rpm","8PK Ø 119
3650 rpm",N-E,2012,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22020540,Kit compresor frío industrial,MERCEDES,ACTROS,OM 470 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 10.700,any,"8PK Ø 119
3650 rpm","8PK Ø 119
3650 rpm",N-E,2012,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22020541,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6D Full),2021,,2021,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2021,,TM 13 / QP 13 | TM 15 / QP 15
KC22020541,Kit compresor frío industrial,NISSAN,PRIMASTAR 2.0 dCi,M9R (Euro 6D Full),2022,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,2022,,TM 13 / QP 13 | TM 15 / QP 15
KC22020541,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,M9R (Euro 6D Full),2022,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 4K A Ø119
3.120 r.p.m.","Poly-V 4K A Ø119
3.120 r.p.m.",N-E,2022,,TM 13 / QP 13 | TM 15 / QP 15
KC22020541,Kit compresor frío industrial,CITROEN,EXPRESS 2.0 dCi,M9R (Euro 6D Full),2022,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,2022,,TM 13 / QP 13 | TM 15 / QP 15
KC22020542,Kit compresor frío industrial,MERCEDES,ATEGO,OM936 (Euro 6),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"6K A Ø137
3.400 rpm",,N,2014,,QP 25
KC22020543,Kit compresor frío industrial,,R370 / R410 / R450 / R500 / R540,DC13 (Euro 6),2022,,2022,,,,,,,,,,,,,,,,,,,,,,,6 / 12.700,yes,"Poly-V 8K A Ø137
2.917 rpm","Poly-V 8K A Ø137
2.917 rpm",N-E,2022,,TM 21 / QP 21
KC22030544,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1E6N (Euro VI OBD-E),2021,2025,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Poly-V 8K A Ø119
3.294 rpm","Poly-V 8K A Ø119
3.294 rpm",N-E,2021,2025,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030546,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2022,Yes,,Yes,Yes,,,,,,,,,,,Yes,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
4.940 rpm",,N,2020,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030547,Kit compresor frío industrial,VW,TRANSPORTER,TDI 2.0 EU6d-TEMP BMT,2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8K A Ø119
4.175 rpm",N-E,10/2019,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030547,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8K A Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030547,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8K A Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030547,Kit compresor frío industrial,VW,TGE 2.0 TDI - RWD,2.0 TDI EA288 (Euro 6 / Euro 6d-Temp),,2017,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8k Ø119
4.175 rpm",N-E,,2017,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030547,Kit compresor frío industrial,VW,TGE 2.0 TDI - FWD,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø119
4.175 rpm","Poly-V 8k Ø119
4.175 rpm",N-E,2017,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22030549,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø137
3.625 rpm","Poly-V 8K A Ø137
3.625 rpm",N-E,2017,,TM 21 / QP 21
KC22030549,Kit compresor frío industrial,VW,CRAFTER 2.0 TDI,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø137
3.625 rpm","Poly-V 8K A Ø137
3.625 rpm",N-E,2017,,TM 21 / QP 21
KC22030549,Kit compresor frío industrial,VW,TGE 2.0 TDI - FWD,2.0 TDI EA288 (Euro 6 / 6d-Temp / 6AR),2017,,2017,,Yes,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø137
3.625 rpm","Poly-V 8K A Ø137
3.625 rpm",N-E,2017,,TM 21 / QP 21
KC22030549,Kit compresor frío industrial,VW,TGE 2.0 TDI - RWD,2.0 TDI EA288 (Euro 6 / Euro 6d-Temp),2017,,2017,Yes,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.968,no,"Poly-V 8K A Ø137
3.625 rpm","Poly-V 8K A Ø137
3.625 rpm",N-E,2017,,TM 21 / QP 21
KC22060551,Kit compresor frío industrial,PEUGEOT,PARTNER,DV5 (Euro 6.3/Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 6K A Ø119
4.500 rpm","Poly-V 6K A Ø119
4.500 rpm",N-E,02/2022,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22060551,Kit compresor frío industrial,CITROEN,BERLINGO,DV5 (Euro 6.3/Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
4.500 rpm","Poly-V 8K A Ø119
4.500 rpm",N-E,02/2022,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22060551,Kit compresor frío industrial,OPEL/VAUXHALL,COMBO CARGO (PSA Platform),DV5 (Euro 6.3/Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
4.500 rpm","Poly-V 8K A Ø119
4.500 rpm",N-E,02/2022,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22060551,Kit compresor frío industrial,TOYOTA,PROACE CITY 1.5 BlueHDi,DV5 (Euro 6.3/Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
4.500 rpm","Poly-V 8K A Ø119
4.500 rpm",N-E,02/2022,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22060551,Kit compresor frío industrial,,DOBLÃ“,DV5 (Euro 6.3/Euro 6.4),2022,,2022,,,,Yes,Yes,,,,,,,,,,,,,,,,,,4 / 1.499,yes,"Poly-V 8K A Ø119
4.500 rpm","Poly-V 8K A Ø119
4.500 rpm",N-E,02/2022,,SD5H14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22070552,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD (EURO6D),M9T (Euro VI-D Temp / Euro VI-E),2022,,2022,Yes,,,Yes,Yes,Yes,ok,,,,Yes,,,,,,,,,,,,4 / 2.298,any,"Poly-VØ119
4.780 rpm","Poly-V 6K A Ø142
4.005 rpm",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22070552,Kit compresor frío industrial,NISSAN,INTERSTAR 2.3 dCi - RWD (EURO 6D Full),M9T (Euro VI-D Full),2022,,2022,Yes,,,Yes,Yes,Yes,ok,,,,Yes,,,,,,,,,,,,4 / 2.298,any,"Poly-VØ119
4.780 rpm","Poly-V 6K A Ø142
4.005 rpm",N-E,2022,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22070552,Kit compresor frío industrial,RENAULT,MASTER 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,Yes,,,,,,,,,,,,4 / 2.298,any,"Poly-VØ119
4.780 rpm","Poly-V 6K A Ø142
4.005 rpm",N-E,2016,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22070553,Kit compresor frío industrial,ISUZU,- D Wide CAB 2.3 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6) | DTi8 320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
4.225rpm",,N,09/2013,,QP 25
KC22070553,Kit compresor frío industrial,VOLVO,FE 250,D8K250 (Euro 6) | D8K280 (Euro 6) | D8K320 (Euro 6),2013,,2013,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
4.225rpm",,N,09/2013,,QP 25
KC22100555,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2022,Yes,,Yes,Yes,,,,,,,,,,,Yes,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
4.940 rpm","Poly-V 8K A Ø119
4.940 rpm",N-E,2020,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC22100556,Kit compresor frío industrial,PEUGEOT,EXPERT 2.2 BlueHDi,B2.2 Euro 6.4,2026,,2026,,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,01/2026,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC22100556,Kit compresor frío industrial,CITROEN,JUMPY 2.2 BlueHDi,B2.2 Euro 6.4,2026,,2026,,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,01/2026,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC22100556,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 2.2 BlueHDi,B2.2 Euro 6.4,2026,,2026,,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,01/2026,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC22100556,Kit compresor frío industrial,FIAT,SCUDO 2.2 BlueHDi,B2.2 Euro 6.4,2026,,2026,,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,01/2026,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC22100556,Kit compresor frío industrial,TOYOTA,PROACE 2.2 BlueHDi,B2.2 Euro 6.4,2026,,2026,,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,01/2026,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC22110557,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi8 250 (Euro 6) | DTi8 280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
3.400rpm",,N,09/2013,,QP 25
KC22110557,Kit compresor frío industrial,ISUZU,- CAB 2.1 m -,DTi5 210 (Euro 6) | DTi5 240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"Poly-V 8PK Ø137
3.400rpm",,N,09/2013,,QP 25
KC22110557,Kit compresor frío industrial,VOLVO,FL 210,D5K210 (Euro 6) | D5K240 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 5.100,any,"Poly-V 8PK Ø137
3.400rpm",,N,09/2013,,QP 25
KC22110557,Kit compresor frío industrial,VOLVO,FL 250,D8K250 (Euro 6) | D8K280 (Euro 6),2013,,2013,,,,Yes,,,ok,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
3.400rpm",,N,09/2013,,QP 25
KC23010558,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro 6D Temp) | F4AFE611E*N (Euro 6D Temp) | F4AFE611C*N (Euro 6D Temp) | F4AFE611D*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"8K A Ø119
3.487 rpm",,N,09/2019,,CS150
KC23010558,Kit compresor frío industrial,IVECO,EuroCargo Tector 7,F4AFE611A*C (Euro 6) | F4AFE611E*C (Euro 6) | F4AFE611C*C (Euro 6) | F4AFE611D*C (Euro 6),2014,2019,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 6.728,any,"8K A Ø119
3.487 rpm",,N,2014,09/2019,CS150
KC23010558,Kit compresor frío industrial,IVECO,EuroCargo Tector,F4AE3681B-P (Euro 4-5)// F4AE3681D-P (Euro 4-5) | F4AE3681E-P (Euro 4-5)//F4AE3681A-P (Euro 4-5),2006,,2011,,,,Yes,,,not,,,,,,,,,,,,Yes,Yes,,,6 / 5.880,any,"8K A Ø119
3.487 rpm",,N,10/2006,,CS150
KC23010559,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23010559,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23010559-A,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23010559-B,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,,,,,Yes,Yes,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23010560,Kit compresor frío industrial,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Poly-V 8K A Ø137
4.290 rpm",,N,09/2019,,QP 25
KC23010561,Kit compresor frío industrial,,S-WAY,Cursor 9 (Euro 6) | F2CFE611D | F2CFE611C | F2CFE611B,2022,2024,2022,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 8K A Ø137
3.260 rpm","Poly-V 8K A Ø137
3.260 rpm",N-E,01/2022,12/2024,TM 21 / QP 21
KC23010562,Kit compresor frío industrial,MITSUBISHI FUSO,"eCanter 4,25 T / 6,0 T / 7,49 T / 8,55 T",,2023,,2023,,,,Yes,,,,,,,,,,,,,,,,,,,,any,Poly-V 8K A Ø119,Poly-V 8K A Ø119,N-E,2023,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23020563,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE0481A-F / F1AE0481B-G (Euro 3-4) | F1AE0481M-H (Euro 3-4) | F1AE0481U/ F1AE0481V (Euro 4),2002,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø150
3.3312 rpm",#¿NOMBRE?,2002,,TM 21 / QP 21
KC23020563,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø150
3.312 rpm",#¿NOMBRE?,09/2019,,TM 21 / QP 21
KC23020563,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø147
3.380 rpm",#¿NOMBRE?,11/2011,,TM 21 / QP 21
KC23020563,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2024,,,,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø150
3.3312 rpm",#¿NOMBRE?,08/2014,,TM 21 / QP 21
KC23020563,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø150
3.312 rpm",#¿NOMBRE?,09/2021,,TM 21 / QP 21
KC23020563-A,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø150
3.312 rpm",#¿NOMBRE?,09/2021,,TM 21 / QP 21
KC23030564,Kit compresor frío industrial,,U-4000,OM 904 LA (Euro 3),1997,,1997,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.249,any,"8PK Ø119
3.515 rpm","8PK Ø119
3.515 rpm",N-E,1997,,SD5H14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23030566,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2022,Yes,,Yes,Yes,,,,,Yes,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
5.332 rpm","Poly-V 8K A Ø157
4.042 rpm",N-E/S,2021,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23030567,Kit compresor frío industrial,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2022,Yes,,Yes,Yes,,,,,Yes,,,,,,,Yes,Yes,,,,,,4 / 1.950,any,"Poly-V 8K A Ø119
3.640 rpm","Poly-V 8K A Ø119
3.640 rpm",N-E,2020,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23030568,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1E6N (Euro 6N),2021,2025,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"Poly-V 8K A Ø119
3.294 rpm","Poly-V 8K A Ø119
3.294 rpm",N-E,2021,2025,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23040570,Kit compresor frío industrial,MERCEDES,ACTROS,OM 936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
3.400 rpm",,N,2012,,QP 25 | TM 21 / QP 21
KC23040570,Kit compresor frío industrial,MERCEDES,ANTOS,OM 936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
3.400 rpm",,N,2012,,QP 25 | TM 21 / QP 21
KC23040570-A,Kit compresor frío industrial,MERCEDES,ANTOS,OM 936 (Euro 6),2012,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 7.700,any,"Poly-V 8PK Ø137
3.400 rpm",,N,2012,,QP 25 | TM 21 / QP 21
KC23040571,Kit compresor frío industrial,,S-WAY,Cursor 9 (Euro 6) | F2CFE611D | F2CFE611C | F2CFE611B,2022,2024,2022,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 8.709,any,"Poly-V 8K A Ø137
3.680 rpm","Poly-V 8K A Ø137
3.680 rpm",N-E,01/2022,12/2024,QP 25
KC23050572,Kit compresor frío industrial,,DYNA L75.34 / L75.38 / L75.42,N04C-WL (Euro 5)                                               N04C-WM (Euro 5),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.200 rpm",,N,09/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23050572,Kit compresor frío industrial,,HINO SERIE 300 (616/617/716/717/816/817/916/917),N04C-WL (Euro 5)                                               N04C-WM (Euro 5),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.200 rpm",,N,09/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23050572-B,Kit compresor frío industrial,,HINO SERIE 300 (616/617/716/717/816/817/916/917),N04C-WL (Euro 5)                                               N04C-WM (Euro 5),2007,,2007,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 4.009,any,"2A Ø135
3.200 rpm",,N,09/2007,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23070573,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,Yes,,,ok,,,,,,Yes,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
4.460 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070573,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2019,,2024,,,Yes,Yes,,,ok,,,,,,Yes,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
4.460 rpm",#¿NOMBRE?,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070573-A,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,,,,ok,,,,,,Yes,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
4.460 rpm",#¿NOMBRE?,09/2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070573-B,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2019,,2024,,,Yes,,,,ok,,,,,,Yes,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
4.460 rpm",#¿NOMBRE?,09/2019,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070574,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1E6N (Euro VI OBD-E),2021,,2021,,,,Yes,,,,,,,,,Yes,,,,,,,,,,4 / 2.999,yes,"Poly-V 8K A Ø119
4.329 rpm","Poly-V 8K A Ø119
4.329 rpm",N-E,2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070575,Kit compresor frío industrial,VW,TRANSPORTER T7 - Euro 6,,2023,2024,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2023,11/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070575,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2023,2024,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2023,11/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070575-A,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2023,,2024,,Yes,,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23070575-C,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2023,2024,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2023,11/2024,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23100577,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,Yes,,,,,Yes,,,,,4 / 2.998,yes,"Poly-V 8K A Ø119
4558 rpm",,N-E,09/2021,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23100577,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,Yes,,,,,Yes,,,,,4 / 2.998,yes,"Poly-V 8K A Ø119
4558 rpm",,N-E,09/2014,,SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC23110579,Kit compresor frío industrial,,RANGER 2.0 EcoBlue TDCi,2.0L EcoBlue TDCi 170CV (125kW) | 2.0L EcoBlue TDCi  213CV (151kW),2023,,2023,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8K A Ø119
3588 rpm (ilde speed)","Poly-V 8K A Ø119
3588 rpm (ilde speed)",N-E,01/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150
KC23110580,Kit compresor frío industrial,,8.5t GVW,Cummins Intercooler Turbo Diesel Euro6,2023,,2023,,,,,,,,,,,,,,,,,,,,,,,3800-04-01 00:00:00,yes,"2A Ø135
3330 rpm",,N,11/2023,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23110581,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC23110581,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24010582,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.690 rpm",,N,09/2021,,QP 25
KC24010582,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.690 rpm",,N,09/2014,,QP 25
KC24010582,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2019,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
3.690 rpm",,N,09/2019,,QP 25
KC24020583,Kit compresor frío industrial,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 7K A Ø119
4.441 r.p.m.","Poly-V 7K A Ø157
3.366 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24020583,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,no,"Poly-V 7K A Ø119
4.441 r.p.m.","Poly-V 7K A Ø157
3.366 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24020584,Kit compresor frío industrial,,MAXUS DELIVER 9 RWD,Euro 6.2,2021,,2021,Yes,,,,,,,,,,,,,,,,,,,,,,4 / 1.996,any,"Poly-V 8K A Ø119
3.576 rpm","Poly-V 8K A Ø119
3.576 rpm",N-E,2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24040586,Kit compresor frío industrial,,8.5t GVW,Cummins Intercooler Turbo Diesel Euro6,2023,,2023,,,,,,,,,,,,,,,,,,,,,,,3800-04-01 00:00:00,yes,"1B Ø180
3000 rpm","1B Ø150
3000 rpm",N-E,11/2023,,TM 21 / QP 21
KC24040587,Kit compresor frío industrial,CITROEN,JUMPER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
4.323 rpm","Poly-V 8K A Ø119
4.323 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24040587,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
4.323 rpm","Poly-V 8K A Ø119
4.323 rpm",N-E,09/2021,04/2024,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24040587,Kit compresor frío industrial,PEUGEOT,BOXER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
4.323 rpm","Poly-V 8K A Ø119
4.323 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24040587,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø119
4.323 rpm","Poly-V 8K A Ø119
4.323 rpm",N-E,02/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24050588,Kit compresor frío industrial,CITROEN,JUMPY 2.0 BlueHDi,DW10 (Euro 6.4),2024,,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,05/2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,PEUGEOT,EXPERT 2.0 BlueHDi,DW10 (Euro 6.4),2024,,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,05/2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,FIAT,SCUDO 2.0 BlueHDi,DW10 (Euro 6.4),2024,,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,05/2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 2.0 BlueHDi,DW10 (Euro 6.4),2024,,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,05/2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,TOYOTA,PROACE 2.0 BlueHDi,DW10 (Euro 6.4),2024,,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,05/2024,,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,PEUGEOT,EXPERT 2.0 BlueHDi,DW10 (Euro 6.3),2021,2024,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,CITROEN,JUMPY 2.0 BlueHDi,DW10 (Euro 6.3),2021,2024,2024,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,FIAT,SCUDO 2.0,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,OPEL/VAUXHALL,VIVARO 2.0D,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,SD5H14 | SD5L14 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC24050588-A,Kit compresor frío industrial,TOYOTA,PROACE 2.0D,DW10 (Euro 6.3),2021,2024,2021,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø119
3.120 rpm","Poly-V 8PK Ø119
3.120 rpm",N-E,2021,2024,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150
KC24060590,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060590,Kit compresor frío industrial,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060590,Kit compresor frío industrial,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060590,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060590,Kit compresor frío industrial,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060590-B,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24060591,Kit compresor frío industrial,NISSAN,PRIMASTAR 2.0 dCi,Blue dCi Euro 6E,2024,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,12/2024,,TM 13 / QP 13 | TM 15 / QP 15
KC24060591,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 Blue dCi,Blue dCi (Euro 6E),2024,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,12/2024,,TM 13 / QP 13 | TM 15 / QP 15
KC24060591,Kit compresor frío industrial,CITROEN,EXPRESS 2.0 dCi,Blue dCi (Euro 6E),2024,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,12/2024,,TM 13 / QP 13 | TM 15 / QP 15
KC24060591,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,Blue dCi (Euro 6E),2024,,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,12/2024,,TM 13 / QP 13 | TM 15 / QP 15
KC24060591,Kit compresor frío industrial,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6d temp),2019,,2021,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,,TM 13 / QP 13 | TM 15 / QP 15
KC24060591,Kit compresor frío industrial,FIAT,TALENTO 2.0 dCi,M9R (Euro 6d temp),2019,2021,2024,,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.120 r.p.m.","Poly-V 8K A Ø119
3.120 r.p.m.",N-E,09/2019,12/2021,TM 13 / QP 13 | TM 15 / QP 15
KC24070594,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),,2019,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø147
3.380 rpm",#¿NOMBRE?,,09/2019,SD7H15 | SD7L15
KC24070594,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE3481A (Euro 5) | F1AE3481B (Euro 5) | F1AE3481C (Euro 5),2011,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,11/2011,,SD7H15 | SD7L15
KC24070594,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2019,,SD7H15 | SD7L15
KC24070594,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2024,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2021,,SD7H15 | SD7L15
KC24070594-A,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AE0481A-F / F1AE0481B-G (Euro 3-4) | F1AE0481M-H (Euro 3-4) | F1AE0481U/ F1AE0481V (Euro 4),2002,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,2002,,SD7H15 | SD7L15
KC24080598,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24080598,Kit compresor frío industrial,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24080598,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24080598,Kit compresor frío industrial,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24080598,Kit compresor frío industrial,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC24080598-A,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,,,,,,,Yes,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
4205 r.p.m.","Poly-V Ø119
4205 r.p.m.",N-E,05/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25010606,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2024,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø119
2.941 rpm",,N,08/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020607,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6AR / 6EA,BKFB Euro 6EA,2024,,2024,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,11/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020608,Kit compresor frío industrial,FORD,TRANSIT 2.0 Euro 6EA / 6AR,BKFB Euro 6EA,2024,,2024,Yes,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V Ø119
3.823 rpm","Poly-V 8PK Ø119
3.823 rpm",N-E,11/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020609,Kit compresor frío industrial,VW,TRANSPORTER T7 - Euro 6,,2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020609,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020609-A,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020609-B,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020610,Kit compresor frío industrial,,D-MAX N57 / N60,RZ4E (Euro 6),2017,,2017,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8K A Ø119
3.150 rpm","Poly-V 8K A Ø119
3.150 rpm",N-E,07/2017,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | UP 150 / UPF 150
KC25020611,Kit compresor frío industrial,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020611,Kit compresor frío industrial,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020611,Kit compresor frío industrial,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020611,Kit compresor frío industrial,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020611,Kit compresor frío industrial,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020611,Kit compresor frío industrial,,RELAY 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,,,,ok,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø119
3.441 r.p.m.","Poly-V 8K A Ø119
3.441 r.p.m.",N-E,05/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25020612,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC25020612,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC25060618,Kit compresor frío industrial,VW,TRANSPORTER T7 - Euro 6,,2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25060618,Kit compresor frío industrial,FORD,Transit Custom 2.0 EURO 6AR 260 / 280 / 290 - FWD -AWD,BKFB (Euro 6AR),2024,,2024,,Yes,Yes,,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø119
3.617 rpm","Poly-V 8PK Ø119
3.617 rpm",N-E,12/2024,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25070619,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro VI-E),2024,,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.287,any,,"Poly-V Ø127
3.288 rpm",#¿NOMBRE?,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25070620,Kit compresor frío industrial,IVECO,DAILY 2.3,F1AGL411 (Euro VI-E),2024,,2024,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,"1A Ø 126
3.371 rpm",#¿NOMBRE?,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25070621,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25070621,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
4.411 r.p.m.","Poly-V 6K A Ø119
4.411 r.p.m.",N-E,09/2024,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25080622,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1E6N (Euro VI OBD-E),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Poly-V 8K A Ø119
3.294 rpm","Poly-V 8K A Ø119
3.294 rpm",N-E,2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25080623,Kit compresor frío industrial,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1E6N (Euro VI OBD-E),2021,,2021,,,,Yes,,,,,,,,,Yes,,,,,,,,,,4 / 2.999,yes,"Poly-V 8K A Ø119
4.329 rpm","Poly-V 8K A Ø119
4.329 rpm",N-E,2021,,SD5H14 | SD7H15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25080624,Kit compresor frío industrial,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2024,,,Yes,Yes,,,ok,,Yes,Yes,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø137
2.810 rpm","Poly-V 8K A Ø137
2.810 rpm",N-E,09/2021,,TM 21 / QP 21
KC25090625,Kit compresor frío industrial,RENAULT,MASTER 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,Yes,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25090625,Kit compresor frío industrial,NISSAN,INTERSTAR 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,Yes,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25100626,Kit compresor frío industrial,,AUMARK 7.5/8.5 TN,Cummins F3.8EVIE156,2023,,2023,,,,,,,,,,,,,,,,,,,,,,,4/3.780,yes,"2A Ø135
3330 rpm",,N,11/2023,,SD5H14 | SD5L14 | SD7H15 | SD7L15 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 150 / UPF 150 | UP 170 / UPF 170
KC25100629,Kit compresor frío industrial,,P280 / P320 / P360,"OC09 104 (CNG/LNG, Euro 6) | OC09 105 (CNG/LNG, Euro 6)",2018,,2018,,,,Yes,,,,,,,,,,,,,,,,,,,6 / 12.700,any,,"Poly-V 8K A Ø127
3.665 rpm",N,2018,,TM 16 / QP 16
KC26010630,Kit compresor frío industrial,,MAXUS DELIVER 7 FWD,Euro 6.2,2021,,2021,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.996,yes,"Poly-V Ø119
3.576 rpm","Poly-V 8K A Ø119
3.576 rpm",N-E,2021,,TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16
KC26020631,Kit compresor frío industrial,,AUMARK 7.5/8.5 TN,Cummins F3.8EVIE156,2023,,2023,,,,,,,,,,,,,,,,,,,,,,,4/3.780,yes,"2A Ø135
3330 rpm",,N,11/2023,,TM 21 / QP 21
KF22070900,Kit chasis,CITROEN,JUMPY 1.5 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,yes,,,N,2021,,Xarios Integrated
KF22070900,Kit chasis,CITROEN,JUMPY 2.0 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Xarios Integrated
KF22070900,Kit chasis,CITROEN,JUMPY,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Xarios Integrated
KF22070900,Kit chasis,CITROEN,JUMPY,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Xarios Integrated
KF22070900,Kit chasis,FIAT,SCUDO 1.5,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Xarios Integrated
KF22070900,Kit chasis,FIAT,SCUDO 2.0,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Xarios Integrated
KF22070900,Kit chasis,OPEL/VAUXHALL,VIVARO 1.5D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Xarios Integrated
KF22070900,Kit chasis,OPEL/VAUXHALL,VIVARO 2.0D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Xarios Integrated
KF22070900,Kit chasis,OPEL/VAUXHALL,VIVARO,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,yes,,,N,2018,,Xarios Integrated
KF22070900,Kit chasis,OPEL/VAUXHALL,VIVARO,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Xarios Integrated
KF22070900,Kit chasis,PEUGEOT,EXPERT 1.5 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Xarios Integrated
KF22070900,Kit chasis,PEUGEOT,EXPERT 2.0 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,,N,11/2021,,Xarios Integrated
KF22070900,Kit chasis,PEUGEOT,EXPERT,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,any,,,N,2018,,Xarios Integrated
KF22070900,Kit chasis,PEUGEOT,EXPERT,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Xarios Integrated
KF22070900,Kit chasis,TOYOTA,PROACE 1.5D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Xarios Integrated
KF22070900,Kit chasis,TOYOTA,PROACE 2.0D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Xarios Integrated
KF22070900,Kit chasis,TOYOTA,PROACE,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Xarios Integrated
KF22070900,Kit chasis,TOYOTA,PROACE,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Xarios Integrated
KF22070900,Kit chasis,OPEL/VAUXHALL,VIVARO,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Xarios Integrated
KF22090901,Kit chasis,OPEL/VAUXHALL,VIVARO,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,OPEL/VAUXHALL,VIVARO,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,TOYOTA,PROACE,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,TOYOTA,PROACE,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,TOYOTA,PROACE 2.0D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,TOYOTA,PROACE 1.5D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,PEUGEOT,EXPERT,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,PEUGEOT,EXPERT,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,any,,,N,2018,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,PEUGEOT,EXPERT 2.0 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,,,N,11/2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,PEUGEOT,EXPERT 1.5 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,OPEL/VAUXHALL,VIVARO,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,yes,,,N,2018,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,OPEL/VAUXHALL,VIVARO 2.0D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,OPEL/VAUXHALL,VIVARO 1.5D,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,FIAT,SCUDO 2.0,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,FIAT,SCUDO 1.5,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,CITROEN,JUMPY,,2019,2021,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,09/2019,11/2021,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,CITROEN,JUMPY,,2018,,2019,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,no,,,N,2018,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,CITROEN,JUMPY 2.0 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.997,no,,,N,11/2021,,Battery Pack 6KWh Mastervolt
KF22090901,Kit chasis,CITROEN,JUMPY 1.5 BlueHDi,,2021,,2021,,,,,,,,,,,,,,,,,,,,,,,4 / 1.499,yes,,,N,2021,,Battery Pack 6KWh Mastervolt
KF23050904,Kit chasis,RENAULT,TRAFIC 2.0 dCi,M9R (Euro 6D Full),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,,N,09/2021,,Xarios Integrated
KF23050904,Kit chasis,NISSAN,PRIMASTAR 2.0 dCi,M9R (Euro 6D Full),2022,,2022,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,,N,2022,,Xarios Integrated
KF23050904,Kit chasis,FIAT,TALENTO 2.0 dCi,M9R (Euro 6D Full),2022,,2022,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.997,any,,,N,2022,,Xarios Integrated
KG13049001,Kit generador,VW,CRAFTER,TDI 2.0 CKTB (Euro 5) | TDI 2.0 CKTC (Euro 5) | BiTDI 2.0 CKUC (Euro 5) | BiTDI 2.0 CKUB (Euro 5),2011,,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"2A Ø135
3.111 rpm",,N,06/2011,,"Generator ""G3-230V"" | Generator ""G4-400V""  | TM 15 / QP 15 | TM 16 / QP 16"
KG13049002,Kit generador,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 5b / Euro 6 b / Euro 6c Gr.III/ VI-C),2014,,2018,,,,Yes,,,ok,,,,,,,,,,Yes,,,,,,4 / 2.143,any,"Ø60
2.406 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG13049003,Kit generador,MERCEDES,SPRINTER 3.0,OM 642 DE30LA | (Euro 4-5-6),2006,,2006,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,,6 / 2.987,any,"Ø53 7PK
2.500 rpm",,N,06/2006,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG13069005,Kit generador,,ELF 200 / ELF 300,4JJ1-TC | (US EPA 04),2006,,2006,,,,,,,,,,,,,,,,,,,,,,,4 / 2.999,no,"Ø60
2.560 rpm",,N,2006,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG13089007,Kit generador,NISSAN,CABSTAR,YD25DDTi | (Euro 4),2006,,2006,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.488,no,"Ø60
2.750 rpm",,N,06/2006,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15069010,Kit generador,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"Ø60
2.403 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15069010,Kit generador,IVECO,EuroCargo Tector 5,F4AFE411A*C (Euro 6) | F4AFE411B*C (Euro 6) | F4AFE411C*C (Euro 6),2014,,2014,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"Ø60
2.506 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15069010,Kit generador,IVECO,EuroCargo Tector 5 ML60E16 / ML65E16 / ML75E16 / ML80EL16 ML75E19 / ML80E19 / ML80EL19 / ML90E19 / ML100E19 / ML110EL19/ ML120EL19 ML75E21 / ML80E21 / ML80EL21 / ML90E21 / ML100E21 / ML110EL21 / ML120EL21,F4AFE411E*N (Euro 6D Temp) | F4AFE411F*N (Euro 6D Temp) | F4AFE411C*N (Euro 6D Temp),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,4 / 4.485,any,"Ø60
2.506 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15079011,Kit generador,RENAULT,MASTER 2.3 dCi - RWD,M9T (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2014,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,"4 / 2.298_x000D_
",any,"Ø60
2.533 rpm",,N,2014,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,NISSAN,NV400 2.3 dCi - RWD,M9T (Euro 5b+),2014,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2014,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,RENAULT,MASTER 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2016,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2016,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,NISSAN,NV400 2.3 dCi - RWD,M9T / M9T B7 (Euro 6),2016,,2016,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2016,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,OPEL/VAUXHALL,MOVANO - RWD,M9T / M9T B7 (Euro 6),2016,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,2016,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,NISSAN,NV400 2.3 dCi - RWD (EURO 6D),M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,OPEL/VAUXHALL,MOVANO - RWD,M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - RWD (EURO 6D),M9T (Euro VI-D Temp),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079011,Kit generador,RENAULT,MASTER 2.3 dCi - RWD (EURO6D),M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,Yes,,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Ø60
2.533 rpm",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG15079012,Kit generador,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2021,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø60
2.415 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15079012,Kit generador,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø60
2.415 rpm",,N,11/2011,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15079012,Kit generador,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø60
2.415 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15079012,Kit generador,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2021,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø60
2.415 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15099013,Kit generador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Ø60
2.454 rpm",,N,06/2016,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG15099013,Kit generador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Ø60
2.454 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16029014,Kit generador,FIAT,DUCATO,F1AE3481 (Euro 5+) | F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Ø53 7PK
2.583 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16029014,Kit generador,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,yes,"Ø53 7PK
2.583 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16029015,Kit generador,ISUZU,NT400 - CABSTAR,YD25K3 LD-5 (Lo) (Euro 5b+) | YD25K3 LD-5 (Mo) (Euro 5b+) | YD25K3 LD-5 (Ho) (Euro 5b+),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.488,no,"Ø60
2.587 rpm",,N,2014,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG16029015,Kit generador,NISSAN,MAXITY,DXi2.5 Euro 5b+ (FAP),2014,,2014,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.488,no,"Ø60
2.587 rpm",,N,2014,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG16029016,Kit generador,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2021,,,,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Ø60
2.454 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16039017,Kit generador,FIAT,DUCATO,F1AE3481 (Euro 5+) | F1AGL411 (Euro 6 / 6b/ 6c),2014,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16039017,Kit generador,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16039017,Kit generador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,06/2016,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16039017,Kit generador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp),2019,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16039017,Kit generador,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG16129019,Kit generador,VW,CRAFTER,TDI 2.0 CKTB (Euro 5/Euro 6) | TDI 2.0 CKTC (Euro 5/Euro 6) | BiTDI 2.0 CKUC (Euro 5/Euro 6) | BiTDI 2.0 CKUB (Euro 5/Euro 6),2011,2016,2011,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"Ø53 7PK
2.818 rpm",,N,06/2011,12/2016,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17049020,Kit generador,MITSUBISHI,CANTER,4PT10-AAT4 (Euro 6D Temp) | 4PT10-AAT6 (Euro 6D Temp),2019,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Ø53 7PK
2.400 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17049020,Kit generador,MITSUBISHI,CANTER,4P10-HAT4 (Euro 6),2014,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Ø53 7PK
2.400 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17049020-B,Kit generador,MITSUBISHI,CANTER,4P10-HAT4 (Euro 6),2014,,2019,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.998 ,any,"Ø53 7PK
2.400 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,RENAULT,MASTER 2.3 dCi - FWD (EURO VI-D),M9T (Euro VI-D),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2016,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2016,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,NISSAN,NV400 2.3 dCi - FWD (EURO VI-D),M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 6),2016,2019,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2016,09/2019,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17059021,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO VI-D),M9T (Euro VI-D Temp),2019,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG17109022,Kit generador,FORD,TRANSIT 2.0 EcoBlue,YLR6 (Euro 6) | YMR6 (Euro 6) | YNR6 (Euro 6),2016,,2016,Yes,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,any,"Ø60
2.600 rpm",,N,2016,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18059024,Kit generador,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 7K A Ø53
2.580 r.p.m.",,N,09/2016,09/2019,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18059024,Kit generador,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 7K A Ø53
2.580 r.p.m.",,N,09/2016,09/2019,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18059024,Kit generador,CITROEN,JUMPER,DW12 RU (Euro 6.2 / Euro 6.3),2019,,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V 7K A Ø53
2.580 r.p.m.",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18059024,Kit generador,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V 7K A Ø53
2.580 r.p.m.",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18059024,Kit generador,PEUGEOT,BOXER,DW12 RU (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2024,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V 7K A Ø53
2.580 r.p.m.",,N,09/2019,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG18109025,Kit generador,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2021,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,"Ø53
2.460 rpm",,N,09/2021,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG18109025,Kit generador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2021,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG18109026,Kit generador,MERCEDES,SPRINTER 2.143,OM 651 DE22 LA | (Euro 6c Gr.III/ VI-C),2018,,2018,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.143,yes,"Ø53 7PK
2.600 rpm",,N,2018,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG20019029,Kit generador,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6d Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20019029,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20019029,Kit generador,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20019029,Kit generador,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Full),2022,,2022,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.298,yes,"Ø60
2.493 rpm",,N,2022,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20029030,Kit generador,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2021,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø53
2.405 rpm",,N,09/2021,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20029030,Kit generador,IVECO,DAILY 3.0,F1CE3481J (Euro 5) | F1CE3481K (Euro 5),2011,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø53
2.405 rpm",,N,11/2011,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20029030,Kit generador,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2021,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø53
2.405 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20029030,Kit generador,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2021,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø53
2.405 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20029030,Kit generador,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.998,any,"Ø53
2.405 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20069031,Kit generador,RENAULT TRUCKS,"SERIE-N 3,5t",RZ4E-TC (Euro 6d-temp),2020,,2020,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,no,"Ø53
2.570 rpm",,N,06/2020,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20069032,Kit generador,IVECO,EuroCargo Tector 7,F4AFE611A*N (Euro VI-D) | F4AFE611E*N (Euro VI-D),2019,,2019,,,,Yes,,,not,,,,,,,,,,,,Yes,,,,6 / 6.728,any,"Ø63
2.506 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20099033,Kit generador,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,08/2014,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20099033,Kit generador,IVECO,DAILY 2.3,F1AGL411H (Euro 6) | F1AGL411J (Euro 6) | F1AGL411G (Euro 6),2016,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,06/2016,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20099033,Kit generador,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp),2019,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20099033,Kit generador,FIAT,DUCATO,F1AGL411 (Euro 6D Temp),2019,,2024,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 2.287,no,"Ø53
2.475 rpm",,N,09/2019,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20109034,Kit generador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2022,Yes,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Ø53
2.363 rpm",,N,2020,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG20109034-A,Kit generador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2020,,2022,Yes,,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Ø53
2.363 rpm",,N,2020,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG21069036,Kit generador,PEUGEOT,BOXER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Ø53 6PK
2.536 rpm",,N,02/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG21069036,Kit generador,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Ø53 6PK
2.536 rpm",,N,09/2021,04/2024,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG21069036,Kit generador,CITROEN,JUMPER,2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Ø53 6PK
2.536 rpm",,N,02/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG21069036,Kit generador,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO VI-D),2.2 Euro 6d-full,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Ø53 6PK
2.536 rpm",,N,02/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG22039037,Kit generador,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2022,,2022,,Yes,,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,yes,"Ø53
2.363 rpm",,N,2022,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG22069038,Kit generador,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1-E6N (Euro 6N),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Ø53 7PK
2.400 rpm",,N,2021,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG23119039,Kit generador,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N,09/2024,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG23119039,Kit generador,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø119
3.500 r.p.m.","Poly-V 8K A Ø119
3.500 r.p.m.",N,09/2024,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG24079040,Kit generador,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040,Kit generador,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040,Kit generador,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040,Kit generador,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040,Kit generador,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040-A,Kit generador,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG24079040-B,Kit generador,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V Ø53
11.094 r.p.m.",,N,05/2024,,"Generator ""G4-230V"" | Generator ""G4-400V"" "
KG25099041,Kit generador,RENAULT,MASTER 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG25099041,Kit generador,NISSAN,INTERSTAR 2.0 dCi - RWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,Yes,,,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 6K A Ø119
3.500 r.p.m.","Poly-V 6K A Ø119
3.500 r.p.m.",N-E,09/2024,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KG26039043,Kit generador,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,4JZ1-E6N (Euro 6N),2021,,2021,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.999,yes,"Ø53 7PK
2.400 rpm",,N,2021,,"Generator ""G3-230V"" | Generator ""G3-400V"" "
KH14127001,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,06/2010,,HPI 15cc
KH14127001,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,06/2010,,HPI 15cc
KH14127001,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD,M9T (Euro 4-5) | M9T (Euro 5b+) - Single Turbo -,2010,,2016,,Yes,,Yes,Yes,Yes,ok,,,,Yes,Yes,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,06/2010,,HPI 15cc
KH15017002,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2014,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,09/2019,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,09/2019,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2014,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,09/2019,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,09/2019,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2016,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2016,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2016,,HPI 12cc | HPI 15cc
KH15017002,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2014,,HPI 12cc | HPI 15cc
KH15017003,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL411J*C (Euro 5b+) | F1CFL411H*C (Euro 5b+),2014,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø133
932 rpm",,N,09/2014,,IPH 25cc
KH15017003,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø133
932 rpm",,N,09/2014,,IPH 25cc
KH15017003,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø133
932 rpm",,N,09/2019,,IPH 25cc
KH15017003,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø133
932 rpm",,N,09/2021,,IPH 25cc
KH16017005,Kit bomba hidráulica,RENAULT,TRAFIC 1.6 dCi,R9M (Euro 5b+/ Euro 6),2014,,2014,,,,Yes,Yes,Yes,,,,,,,,,,,,,,,,,4 / 1.598,any,"Poly-V 7K A Ø140
3.900 rpm",,N,2014,,HPI 8cc
KH17067006,Kit bomba hidráulica,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 7K A Ø140
4.285 rpm",,N,09/2016,,HPI 12cc | HPI 15cc
KH17067006,Kit bomba hidráulica,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,,2019,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 7K A Ø140
4.285 rpm",,N,09/2016,,HPI 12cc | HPI 15cc
KH17077007,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T B7 (Euro 5b+),2014,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 7K A Ø140
4.000 rpm",,N,2014,,12 cc SALAMI | 16 cc SALAMI
KH17087008,Kit bomba hidráulica,,D-MAX N57 / N60,RZ4E (Euro 6),2017,,2017,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 7K A Ø140
4.000 rpm",,N,07/2017,,HPI 12cc | HPI 15cc
KH17087009,Kit bomba hidráulica,RENAULT TRUCKS,"SERIE-N 3,5t",RZ4EE6N-L  (Euro 6b-1),2017,,2017,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,no,"Poly-V 7K A Ø140
3.985 rpm",,N,07/2017,,HPI 12cc | HPI 15cc
KH17127010,Kit bomba hidráulica,,HILUX 2.4 D-4D,2.4L D-4D | 2GD-FTV Euro 6.1,2017,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.393,any,"Poly-V 8K A Ø145
820 rpm",,N,11/2017,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,CITROEN,JUMPY,DW10FE (Euro 6) | DW10FD (Euro 6),2016,,2016,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,09/2016,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,PEUGEOT,EXPERT,DW10FE (Euro 6) | DW10FD (Euro 6),2016,,2016,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,09/2016,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,TOYOTA,PROACE,DW10FE (Euro 6) | DW10FD (Euro 6),2016,,2016,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,09/2016,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,PEUGEOT,EXPERT 2.0 BlueHDi,DW10 (Euro 6.3 / Euro 6.4),2021,,2021,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,11/2021,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,CITROEN,JUMPY 2.0 BlueHDi,DW10 (Euro 6.3 / Euro 6.4),2021,,2021,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,11/2021,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,TOYOTA,PROACE 2.0D,DW10 (Euro 6.3 / Euro 6.4),2021,,2021,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,11/2021,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,OPEL/VAUXHALL,VIVARO 2.0D,DW10 (Euro 6.3 / Euro 6.4),2021,,2021,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,11/2021,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19037011,Kit bomba hidráulica,FIAT,SCUDO 2.0,DW10 (Euro 6.3 / Euro 6.4),2021,,2021,,,Yes,Yes,Yes,,not,,,,,,,,,,,,,,,,4 / 1.997,any,"Poly-V 8PK Ø145
2.552 rpm",,N,11/2021,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19067012,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO - FWD,M9T / M9T B7 (Euro 6),2016,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,2016,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,2016,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,2016,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD,M9T / M9T B7 (Euro 6),2016,,2016,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,2016,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO - FWD,M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D temp) | M9T (Euro VI-D temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH19067012,Kit bomba hidráulica,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH19067013,Kit bomba hidráulica,,D-MAX N57 / N60,RZ4E (Euro 6),2017,2022,2017,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8K A Ø145
820 rpm (ilde speed)",,N,07/2017,12/2022,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19067013-C,Kit bomba hidráulica,,D-MAX N57 / N60,RZ4E (Euro 6),2017,2022,2017,,,Yes,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8K A Ø145
820 rpm (ilde speed)",,N,07/2017,12/2022,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19107014,Kit bomba hidráulica,,RANGER 2.0 EcoBlue TDCi,2.0L EcoBlue TDCi 170CV (125kW) | 2.0L EcoBlue TDCi  213CV (157kW),2019,2022,2023,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8K A Ø145
880 rpm (ilde speed)",,N,09/2019,12/2022,12 cc SALAMI
KH19107015,Kit bomba hidráulica,IVECO,DAILY 2.3,F1AFL411A*A (Euro 5b+) | F1AFL411B*A (Euro 5b+) | F1AFL411C*A (Euro 5b+),2014,,2019,,,,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,08/2014,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19107015,Kit bomba hidráulica,IVECO,DAILY 2.3,F1AGL411X (Euro 6d-temp) | F1AGL411Y (Euro 6d-temp) | F1AGL411W (Euro 6d-temp) | F1AGL411U (Euro 6d-temp),2019,,2019,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2019,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19107015,Kit bomba hidráulica,IVECO,DAILY 2.3,F1AGL411 (Euro 6d-full / Euro VI-E),2019,,2019,,,Yes,,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.287,any,,,N,09/2019,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19117016,Kit bomba hidráulica,,HILUX 2.4 D-4D,2.4L D-4D | 2GD-FTV Euro 6.1,2017,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.393,any,"Poly-V 8K A Ø145
3750 rpm",,N,2017,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH19117016,Kit bomba hidráulica,,HILUX 2.4 D-4D,2.4L D-4D | 2GD-FTV Euro 6.2,2019,,2019,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.393,any,"Poly-V 8K A Ø145
3750 rpm",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI | 8 cc SALAMI
KH20017017,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL411E*A /  F1CGL411E*A / F1CGL411A*E  (Euro 6) | F1CFL411F*A / F1CGL411F*A / F1CGL411B*E (Euro 6) | <b>F1CFA401A*A (CNG)</b>,2014,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø134
925 rpm",,N,09/2014,,16 cc SALAMI
KH20017017,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL4116  (Euro 6d-temp) | F1CFL4117  (Euro 6d-temp) | F1CFL4115  (Euro 6d-temp) | <b>F1CFA401C (CNG)</b>,2019,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø134
925 rpm",,N,09/2019,,16 cc SALAMI
KH20017017,Kit bomba hidráulica,IVECO,DAILY 3.0,F1CFL (Euro 6d-full / Euro VI-E) | <b>F1CFA401C (CNG)</b>,2021,,2021,,,Yes,Yes,,,ok,,,,,,,,,,,Yes,,,,,4 / 2.998,any,"Poly-V 8K A Ø134
925 rpm",,N,09/2021,,16 cc SALAMI
KH20087018,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø160
800 r.p.m.",,N,09/2019,,12 cc SALAMI
KH20087018,Kit bomba hidráulica,CITROEN,JUMPER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,2024,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø160
800 r.p.m.",,N,09/2019,04/2024,12 cc SALAMI
KH20087018,Kit bomba hidráulica,PEUGEOT,BOXER,DW12 (Euro 6.2 / Euro 6.3 / Euro 6.4),2019,,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 2.179,yes,"Poly-V Ø160
800 r.p.m.",,N,09/2019,,12 cc SALAMI
KH20087018,Kit bomba hidráulica,CITROEN,JUMPER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø160
800 r.p.m.",,N,09/2016,09/2019,12 cc SALAMI
KH20087018,Kit bomba hidráulica,PEUGEOT,BOXER,DW10 FUE (Euro 6) | DW10 FUD (Euro 6) | DW10 FUC (Euro 6),2016,2019,2019,,,Yes,Yes,Yes,,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V Ø160
800 r.p.m.",,N,09/2016,09/2019,12 cc SALAMI
KH20107019,Kit bomba hidráulica,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2021,Yes,,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8PK Ø145
2.552 rpm",,N,2021,,12 cc SALAMI
KH21017020,Kit bomba hidráulica,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø134
943 rpm",,N,09/2019,,12 cc SALAMI
KH21017020,Kit bomba hidráulica,FORD,TRANSIT CUSTOM 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,no,"Poly-V 8PK Ø134
943 rpm",,N,09/2019,,12 cc SALAMI
KH21087022,Kit bomba hidráulica,FORD,TRANSIT 2.0 EcoBlue,YLF6/YLFS (Euro 6) | YMF6/YMFS (Euro 6) | YNF6/YNFS (Euro 6),2016,2019,2016,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø134
950 r.p.m.",,N,2016,09/2019,12 cc SALAMI
KH21087022,Kit bomba hidráulica,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø134
950 r.p.m.",,N,09/2019,,12 cc SALAMI
KH21087022-B,Kit bomba hidráulica,FORD,TRANSIT 2.0 EcoBlue Euro 6dtemp,YLF6/YLFS (Euro 6D Temp) | YMF6/YMFS (Euro 6D Temp) | YNF6/YNFS (Euro 6D Temp),2019,,2019,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø134
950 r.p.m.",,N,09/2019,,12 cc SALAMI
KH21087023,Kit bomba hidráulica,RENAULT,MASTER 2.3 dCi - FWD (EURO6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp / Euro VI-E),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH21087023,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.3 CDTI - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH21087023,Kit bomba hidráulica,NISSAN,INTERSTAR 2.3 dCi - FWD (EURO 6D Full),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH21087023,Kit bomba hidráulica,NISSAN,NV400 2.3 dCi - FWD (EURO 6D),M9T (Euro 6D Temp) | M9T (Euro VI-D Temp),2019,,2019,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 2.298,any,"Poly-V 8PK Ø145,5
870 r.p.m.",,N,09/2019,,12 cc SALAMI | 16 cc SALAMI
KH21097024,Kit bomba hidráulica,FIAT,DUCATO,2.2 Euro 6d-full,2021,2024,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø134
971 rpm (idle speed)",,N,09/2021,04/2024,12 cc SALAMI
KH21117025,Kit bomba hidráulica,,PORTER NP6 1.5,EURO 6d-full (petrol/LPG & petrol/methane),2021,,2021,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.498,any,"Poly-V 8PK Ø134
1.422 rpm",,N,2021,,16 cc SALAMI
KH22117026,Kit bomba hidráulica,MERCEDES,SPRINTER 2.0,OM 654 D20 SCR | (Euro 6d-Temp / VI E),2021,,2021,,Yes,Yes,Yes,,,,,,,,,,,,Yes,,,,,,,4 / 1.950,any,"Poly-V 8PK Ø135
4.700 rpm",,N,2021,,12 cc SALAMI
KH23077027,Kit bomba hidráulica,,RANGER 2.0 EcoBlue TDCi,2.0L EcoBlue TDCi 170CV (125kW) | 2.0L EcoBlue TDCi  213CV (151kW),2023,,2023,,,Yes,Yes,,,,,,,,,,,,,,,,,,,4 / 1.995,any,"Poly-V 8K A Ø135
880 rpm (ilde speed)",,N,01/2023,,12 cc SALAMI
KH23117028,Kit bomba hidráulica,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø145
894 r.p.m.","Poly-V 8K A Ø145
3.910 r.p.m.",N,09/2024,,12 cc SALAMI
KH23117028,Kit bomba hidráulica,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø145
894 r.p.m.","Poly-V 8K A Ø145
3.910 r.p.m.",N,09/2024,,12 cc SALAMI
KH24057030,Kit bomba hidráulica,RENAULT TRUCKS,SERIE - N Euro VI OBD-D,RZ4E-TC (Euro 6d-temp),2020,,2020,,,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.898,any,"Poly-V 8PK Ø138
870 rpm",,N,06/2020,,16 cc SALAMI
KH24067032,Kit bomba hidráulica,,MAXUS DELIVER 9 RWD,Euro 6.2,2021,,2021,Yes,,,Yes,,,,,,,,,,,,,,,,,,,4 / 1.996,any,"Poly-V 8K A Ø135
833 rpm (ilde speed)",,N,2021,,16 cc SALAMI
KH24087033,Kit bomba hidráulica,PEUGEOT,BOXER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,12 cc SALAMI
KH24087033,Kit bomba hidráulica,CITROEN,JUMPER 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,12 cc SALAMI
KH24087033,Kit bomba hidráulica,OPEL/VAUXHALL,MOVANO 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø135
995 rpm",,N-E,05/2024,,12 cc SALAMI
KH24087033,Kit bomba hidráulica,TOYOTA,PROACE MAX 2.2 BlueHDi MY2024,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,yes,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,12 cc SALAMI
KH24087033,Kit bomba hidráulica,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,12 cc SALAMI
KH24087033-A,Kit bomba hidráulica,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,12 cc SALAMI
KH25017034,Kit bomba hidráulica,NISSAN,INTERSTAR 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø145
894 r.p.m.","Poly-V 8K A Ø145
3.910 r.p.m.",N,09/2024,,12 cc SALAMI
KH25017034,Kit bomba hidráulica,RENAULT,MASTER 2.0 dCi - FWD (EURO 6.4),XDD M920 Blue dCi EURO 6.4,2024,,2024,,Yes,,Yes,Yes,Yes,ok,,Yes,,,,,,,,,,,,,,4 / 1.997,yes,"Poly-V 8K A Ø145
894 r.p.m.","Poly-V 8K A Ø145
3.910 r.p.m.",N,09/2024,,12 cc SALAMI
KH25107036,Kit bomba hidráulica,FORD,TRANSIT 2.0 Euro 6AR / 6EA,BKFB Euro 6EA,2024,,2024,,Yes,,Yes,,,ok,,,,,,,,,,,,,,,,4 / 1.995,yes,"Poly-V 8PK Ø134
950 r.p.m.",,N,09/2024,,12 cc SALAMI
KH25127038,Kit bomba hidráulica,FIAT,DUCATO,2.2 Euro 6.4,2024,,2024,,,,Yes,,,,,,,,,,,,,,,,,,,4 / 2.184,any,"Poly-V 8K A Ø135
995 rpm",,N,05/2024,,16 cc SALAMI
Kits T6_old original sump oil,Otro,VW,TRANSPORTER,TDI 2.0 | (Euro 6),2015,,2015,,,,,,,,,,,,,,,,,,,,,,,4 / 1.968,any,"Poly-V Ø119
2.875 rpm","Poly-V 7K A Ø119
2.875 rpm",N-E,2015,,SD5H14 | SD7H15 | TM 08 / QP 08 | TM 13 / QP 13 | TM 15 / QP 15 | TM 16 / QP 16 | UP 120 / UPF 120 | UP 150 / UPF 150 | UP 170 / UPF 170 | UP 90
"""
_BD_NOTES = """code,noteeng_clean
1125008000,
1130008000,
KA19035001,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA19035002,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA19045003,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Non inclus dans le kit :
Alternateur 14V- 200A P/N 1198011200
Alternateur 28V- 100A P/N 1198012100"
KA19055004,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA19095005,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA20045006,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- To install this kit it is essential to use the special tool code P/N 1140000155
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA20085007,"- Can be fit in right hand drive vehicles
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1120995007
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA21055008,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA21075009,"- Can be fit in right hand drive vehicles
- Kit not suitable for vehicles 6x2 with directional rear axle (TA-HYDRS)
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1140000358
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA21105010,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA21125011,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA22065012,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles
- Not included in the kit: Alternator 28V - 150A P/N 1198242150
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- Not suitable for MY2024 vehicles"
KA22065012-B,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles
- Not included in the kit: Alternator 28V - 150A P/N 1198242150
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- Not suitable for MY2024 vehicles"
KA22105013,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles
- Not included in the kit: Alternator 14V - 140A P/N 1198121141"
KA23015014,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC.
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200
Alternator 28V- 100A P/N 1198012100"
KA23025015,"- Can be fit in right hand drive vehicles.
- KIT NOT SUITABLE FOR VEHICLES WITH STTA OPTION (START/STOP AND REVERSIBLE ALTERNATOR 180A)
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- Not included in the kit: Alternator 14V - 140A P/N 1198121141"
KA23035017,"- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
- Not included in the kit:
Alternator 128V - 150V P/N 1198242150"
KA23055018,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Alternador 28V - 150A P/N 1198242150"
KA23055019,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Alternator Valeo 14V - 140A P/N 1198121140"
KA23055020,"- Can be fit in right hand drive vehicles
- Use tool to block the flywheel P/N 1149000412
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" JI01 option (connector 15 ways C036L1A)
- Not included in the kit:
Alternator Valeo 14V - 140A P/N 1198121140"
KA23055021,"- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
- Not included in the kit:
Alternator 14V- 140A P/N 1198121141"
KA23055022,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
- Not included in the kit:
Alternator 14V- 140A P/N 1198121140"
KA23065023,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Not included in the kit:
Alternator 14V - 140A P/N 1198242150"
KA23105027,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Not included in the kit:
Alternator 14V- 200A P/N 1198011200"
KA23115029,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC.
- Not included in the kit:
Alternator 14V- 140A P/N 1198121141"
KA23115030,"- RWD= Rear wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased up to1.000 r.p.m. If you have the AAM module, It is necessary to visit an official workshop."
KA23125031,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox"
KA24015032,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox"
KA24015033,- Can be fit in right hand drive vehicles
KA24045035,"- Can be fit in right hand drive vehicles
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- Not included in the kit:
Alternator 28V- 150A P/N 1198242150"
KA24055038,"- Can be fit in right hand drive vehicles
- Suitable on vehicles WITH optional mPTO NA7"
KA24075040,- Can be fit in right hand drive vehicles
KA24095041,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA -.
- According to the manufacturer, for the installation and running of an additional unit, the engine speed at idling, must not be below 1.000 rpm."
KA24095041-A,"- FWD= Front wheel drive
- Suitability for right hand drive vehicles
- Suitability for automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA o CABADP -.
- According to the manufacturer, for the installation and running of an additional unit, the engine speed at idling, must not be below 1.000 rpm."
KA24125042,"- Can't be fit in right-hand drive vehicles.
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KA25035043,"- Can be fit in right-hand drive vehicles.
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KA25035044,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
- Not included in the kit:
Alternator 28V - 150A P/N 1198242150"
KA25105046,"- FWD: Front wheel drive
- Suitable with right hand drive vehicles
- Suitable for the automatic gear box.
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KB00008000,
KB00008000X,
KB00008001,
KB00008001X,
KB00008002X,
KB07118001,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB07118002X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB08108003,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB08118004X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB09048005,"- ""E""=TM-UNICLA;""S""=SANDEN.
- ""S"" only for SD7H15.
- Can be fit in right hand drive vehicles"
KB09108008,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB09118009,"- FWD= Front wheel drive
- ""E""=TM-UNICLA
- Can be mounted with or without the PTO option.
- Can be fit in right hand drive vehicles"
KB09128010,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10018011X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10018012,"- Only for vehicles with original 504180619.
- Can be fit in right hand drive vehicles."
KB10018013,- Can be fit in right hand drive vehicles.
KB10028014,- Can be fit in right hand drive vehicles
KB10038015X,"- Suitable for additional alternator.
- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038016,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038016X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038017,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038017X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038018,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10038019,- Can be fit in right hand drive vehicles.
KB10038020,"- Suitable for additional alternator.
- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10078021,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Only for vehicles WITHOUT the original MAN FF120 option"
KB10098022X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10098023,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB10098023X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11018024,- Compressor fittings not supplied in the kit
KB11028025,"- FWD= Front wheel drive
- Can be fit in right hand drive vehicles
- Not recommended in vehicles with automatic gear box
- It canâ€™t be fit in vehicles whit Start & Stop"
KB11038026X,"- Without additional alternator.
- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11038027,"- Suitable for additional alternator.
- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11068028,- Can be fit in right hand drive vehicles.
KB11068029,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11068029X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11068030X,"- Chassis 15m.
- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11078031,
KB11078032,"- When vehicle is not equipped with the crankshaft pulley N87, request code P/N 1111008032.
- Can be fit in right hand drive vehicles."
KB11088033,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11088033X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11098034,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11118035X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB11128036,- Can be fit in right hand drive vehicles
KB12018037,"- Only for vehicles with original 504180619.
- Can be fit in right hand drive vehicles."
KB12028038,"- ""E""=TM-UNICLA;""S""=SANDEN.
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KB12048040,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB12048041,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB12068042,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB12078043,"- RWD:Rear wheel drive
- Can be fit in right hand drive vehicles"
KB12118045,- Can be fit in right hand drive vehicles
KB12118046,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KB13028047,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB13038048,"- Can't be fit in right hand drive vehicles.
- No suitable for 220HP engine with automatic gear box."
KB13058049,"- Can be fit in right hand drive vehicles
- Only for vehicles with original option MAN FF120."
KB13068050,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Clutch references:
LINNIG (LA16.0172) Ø180
LANG (KK73.1.36.N-St) Ø180"
KB13098051,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KB13108052,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB13108052X,"- Can be fit in right hand drive vehicles.
- Fittings supplied with unit."
KB13118055,- Can be fit in right hand drive vehicles
KB14038057,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1121998057"
KB14058058,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1121990356"
KB14058059,
KB14068060X,
KB14078061,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1121998061"
KB14088062,"- When vehicle is not equipped with the crankshaft pulley N87, request code P/N 1111008032
- Compressor SD5H09: ref.5074
- Can be fit in right hand drive vehicles."
KB14098064,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit."
KB14118067,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Kit designed to mount a Bock FK40 compressor and a 2nd original alternator.
- It is necessary Linning LA16.0333Y E-M-Clutch with plug."
KB14128068X,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- In order to install an additional alternator, it is required to get the special option P/N 1140008068"
KB15018069,"- ""E""=TM-UNICLA;
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KB15028070,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KB15028072,"- COMPRESSOR PULLEY LINNING LA16_0234Y
- Vehicle equipped with original option HK85
- Fixing for 3rd alternator reference Mercedes A 000 150 72 12"
KB15028073,
KB15038074,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Kit designed to mount a BOCK FK40 compressor and a 2nd original alternator
- It is necessary Linning LA16.0333Y E-M-Clutch with plug."
KB15068075,- Compressor fittings not supplied in the kit
KB15078076,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KB15118077,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KB16018078,"- Can be fit in right hand drive vehicles
- Kit designed to mount a Bock FK40 compressor and a TM31 compressor.
- It is necessary ""Linning LA160234Y""."
KB16018079,- Can be fit in right hand drive vehicles
KB16048081,"- Compressor fittings not supplied in the kit
- Suitable for front box AC"
KB16098082,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KB17028083,
KB17038084,"- The vehicle must be equipped with special option DAF: ""Thermoking Preparation or Generator preparation""
- Can be fit in right hand drive vehicles"
KB17038084-A,"- The vehicle must be equipped with special option DAF: ""Thermoking Preparation""
- Not suitable for vehicles with ""Generator Option""
- Can be fit in right hand drive vehicles"
KB17038084-B,"- The vehicle must be equipped with special option DAF: ""Thermoking Preparation""
- Not suitable for vehicles with ""Generator Option""
- Can be fit in right hand drive vehicles"
KB17118085,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KB17118086,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KB18028089,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000149"
KB18038090,"- Can be fit in right hand drive vehicles
- Vehicle must be equipped with special option Volvo PTEF-P1
- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1150000295"
KB18068091,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN Frigoblock"
KB18068092,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Suitable only for vehicles WITH optional power take off crankshaft pulley - PFMot"
KB18108093U,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KB19058095,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN Frigoblock"
KB20028096,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH THE N7C OPTION
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1121998096"
KB20028097,- Compressor fittings not supplied in the kit
KB20118103,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KB21098106,"- Compressor fittings not supplied in the kit
- Suitable for front box AC"
KB21108107,"- Compressor fittings not supplied in the kit
- Suitable for front box AC
- COMPATIBLE with automatic gearbox ALLISON"
KB22028110,"- RWD= Rear wheel drive
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KB22028111,"- RWD= Rear wheel drive
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped with the whole N63 option: original bracket + N62/N63 crankshaft pulley - A654 032 10 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KB22068112,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KB23068113,- Can be fit in right hand drive vehicles
KB23068114,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles."
KB23108115,"- Can't be fit in right hand drive vehicles.
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox"
KB23118116,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Chassis definition CLAC-CM
- Chassis mounted A/C
- Clutch references: LINNIG (LA16.0172) Ø180 LANG (KK73.1.36.N-St) Ø180"
KB23118116-A,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Chassis definition CLAC-CM
- Chassis mounted A/C
- Clutch references: LINNIG (LA16.0172) Ø180 LANG (KK73.1.36.N-St) Ø180"
KB24088117,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Suitable for MY2024 vehicles"
KB24088118,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Suitable for MY2024 vehicles"
KB25018120,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Suitable for MY2024 vehicles"
KB25018121,"- Can be fit in right hand drive vehicles
- THE ORIGINAL ACCESSORIES BELT IS KEPT
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Suitable for MY2024 vehicles"
KC05090001,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles."
KC05100002,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- Can be fit in right hand drive vehicles
- Only for vehicles with original N60 PTO option
- Only for vehicles with original dual compressor bracket"
KC05100003,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- Can be fit in right hand drive vehicles
- Only for vehicles with original N60 PTO option
- The original bracket for two compressors is included in the kit
- Crankshaft Pulley not included in the kit. The vehicle must be equipped with the original pulley Mercedes N60, A6110301003 for the 4-cylinder engine and A6120300503 for the 5-cylinder"
KC05100004,- Can be fit in right hand drive vehicles
KC05100005,- Can be fit in right hand drive vehicles
KC05100006,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles
- For compressor TM-08 and UP-90 it is essential to indicate the compressor in the order."
KC05100006-E,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles
- For compressor TM-08 and UP-90 it is essential to indicate the compressor in the order."
KC05100008,"- Engine mounted sideways
- Rear wheel drive
- Can be fit in right hand drive vehicles"
KC05100009,- Can be fit in right hand drive vehicles
KC05100010,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles
- RWD:Rear wheel drive"
KC05100011,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC05100012,"- ""E""=TM / QUE / UNICLA
- For SD5H14/SD5L14 and SD7H15/SD7L15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- To be mounted with special PTO option
- Can be fit in right hand drive vehicles"
KC05100013,- Can be fit in right hand drive vehicles
KC05100014,- Can be fit in right hand drive vehicles
KC05100015,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Applicable only when the power steering pump is located rear the engine (driven with an independent belt), not above the alternator
- Can be fit in right hand drive vehicles"
KC05100016,"- From chassis number ZCFA75CO102391603 (truck number 3298466).
- Can't be fit in right hand drive vehicles."
KC05100017,- Can't be fit in right hand drive vehicles.
KC05100018,- Can't be fit in right hand drive vehicles.
KC05100019,- Can be fit in right hand drive vehicles
KC05100020,- Can be fit in right hand drive vehicles
KC05100022,- Can be fit in right hand drive vehicles
KC05100023,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- To be mounted with special PTO option
- Can be fit in right hand drive vehicles"
KC05100024,- Can be fit in right hand drive vehicles
KC05100025,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- Can be fit in right hand drive vehicles.
- A 45º suction fitting is recommended on right hand drive vehicles."
KC05100026,"- Not to be used on 18 ton vehicles
- Can be fit in right hand drive vehicles"
KC05100027,"- Can be fit in right hand drive vehicles
- FWD:front wheel driven"
KC05100028,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles"
KC05100029,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- When the vehicle is not equipped with the a/c sump, the sump P/N 1155000029 must be ordered separately
- Can be fit in right hand drive vehicles"
KC05100031,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- When the vehicle is not equipped with the a/c sump, the sump P/N 1155000029 must be ordered separately
- Can be fit in right hand drive vehicles"
KC05100033,"- - ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- When the vehicle is not equipped with the a/c sump, the sump P/N 1155000029 must be ordered separately
- Can be fit in right hand drive vehicles"
KC05100035,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- When the vehicle is not equipped with the a/c sump, the sump P/N 1155000029 must be ordered separately
- Can be fit in right hand drive vehicles"
KC05100037,"- Applicable from chassis 152369000
- Brake exhauster camshaft driven
- Can be fit in right hand drive vehicles"
KC05100038,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC05100040,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box"
KC05100041,"- To install this kit it is essential to use the special tool code P/N 1149000092 or Ref.Ford 303-393.
- To be fitted in vehicles with original A/C option
- Alternator is shaft driven
- Can be fit in right hand drive vehicles"
KC05100044,- Can be fit in right hand drive vehicles
KC05100045,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles"
KC05100046,- Can be fit in right hand drive vehicles
KC05100049,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles"
KC05100051,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Vehicle must be equipped with original A/C compressor bracket
- Can be fit in right hand drive vehicles"
KC05100053,"- ""E""=TM QUE / UNICLA
- To be mounted with special PTO option
- Can be fit in right hand drive vehicles"
KC05100055,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Engine mounted sideways
- Can be fit in right hand drive vehicles"
KC05100056,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles"
KC05100057,- Can be fit in right hand drive vehicles
KC05100058,- Can be fit in right hand drive vehicles
KC05100059,- Can be fit in right hand drive vehicles
KC05100060,- Can be fit in right hand drive vehicles
KC05100061,- Can be fit in right hand drive vehicles
KC05100062,"- Vehicle must be eqquiped with original A/C system
- Can be fit in right hand drive vehicles"
KC05100064,"- ""E""=TM-UNICLA;""S""=SANDEN.
- ""S"" only for SD7H15 / SD7L15 .
- Requires crankshaft pulley w/ 3 grooves, RVI 5000691024, and fan spacer RVI 5010258230
- Can be fit in right hand drive vehicles"
KC05100065,"- ""E""=TM-UNICLA;""S""=SANDEN.
- ""S"" only for SD7H15 / SD7L15.
- Requires A/C option, RVI 18482 - one pulley, 3 grooves, RVI 05403, and one, 2, grooves, RVI 73410
- Can be fit in right hand drive vehicles"
KC05100066,- Can be fit in right hand drive vehicles
KC05100067,"- ""E""=TM-UNICLA;""S""=SANDEN.
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles"
KC05100068,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles"
KC06040074,"- Can be fit in right hand drive vehicles.
- Only for vehicles WITHOUT original option MAN 120FF"
KC06040075,- Can be fit in right hand drive vehicles
KC06060076,"- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111000076
- Can be fit in right hand drive vehicles"
KC06060077,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111000076
- Can be fit in right hand drive vehicles"
KC06070079,- Can be fit in right hand drive vehicles
KC06070081,"- ""E""=TM-UNICLA.
- FWD: Front wheel driven"
KC06070082,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Vehicle must be equipped with original (""C.M.F."") option.
- Can be fit in right hand drive vehicles"
KC06070083,- Can be fit in right hand drive vehicles
KC06090084,- Can be fit in right hand drive vehicles
KC06090085,- Can be fit in right hand drive vehicles
KC06100086,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles
- RWD:Rear wheel drive"
KC06100087,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- Can be fit in right hand drive vehicles"
KC06100088,- Can be fit in right hand drive vehicles
KC06100089,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles.
- Only for vehicles with original N63 PTO option."
KC06110090,"- ""E""=TM QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be mounted with or without the PTO option"
KC06110091,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Only in vehicles with cabin comfort, type ""C\"\"\"
KC06110092,"- Can be fit in right hand drive vehicles
- Use the special tool P/N 1149000092 to fit the kit"
KC06110093,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Can be fit in right hand drive vehicles"
KC06110094,"- ""E""=TM / QUE / UNICLA
- Replace transmision kit every 30.000Km. P/N 1125000094
- Can be fit in right hand drive vehicles"
KC06120095,"- ""E""=TM / QUE / UNICLA
- Must be equipped with Power take-off (PFMOT).
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC06120096,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Can be fit in right hand drive vehicles"
KC07010097,"- ""E""=TM ( QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC07010098,"- Can be fit in standard vehicles, without options
- For RHD vehicles you should order the P/N 1121000098.
- Water pipe must be Ref.: 7482241760"
KC07010099,"- Vehicle must be eqquiped with option RVI -1EZ02
- Water pipe must be Ref.: 7482241760.
- For RHD vehicles you should order the P/N 1121000098."
KC07020100,- Can be fit in right hand drive vehicles
KC07020101,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles"
KC07020102,"- The vehicle does not have to be equipped with the option take off 2AB.
- Can be fit in right hand drive vehicles"
KC07030103,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC07030104,- Can be fit in right hand drive vehicles
KC07030105,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles."
KC07040106,"- Can be fit in standard vehicles, without options
- Can be fit in right hand drive vehicles"
KC07040107,"- Vehicle must be equipped with option Volvo-APUL1
- Can be fit in right hand drive vehicles"
KC07040108,- Can be fit in right hand drive vehicles
KC07040109,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- For vehicles with hydraulic power steering, order the belt (not included in the kit):
KC07040109: P/N 1260601705
KC07040109E: P/N 1260601740"
KC07040110,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC07040111,"- Can't be fit in right hand drive vehicles.
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC07040112,"- Can't be fit in right hand drive vehicles.
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC07050114,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- To install this kit it is essential to use the special tool code P/N 1140000155"
KC07070115,"- ""E""=TM-UNICLA
- For TM and UP Ø119 only Poly-V 8K
- Use the special tool: P/N 1149000115 to fit the kit (ref. Toyota 09330-00021 and 09213-58013).
- Can be fit in right hand drive vehicles"
KC07070116,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Can be fit in right hand drive vehicles"
KC07080117,"- Use the special tool: P/N 1149000115 to fit the kit (ref. Toyota 09330-00021 and 09213-58013).
- Can be fit in right hand drive vehicles"
KC07090118,"- ""E""=TM / QUE / UNICLA
- It cannot be fit in vehicles with the original A/C located in the RIGHT upper part of the engine.
- For vehicles previous to 8/2010 request P/N 1290000118.
- Can be fit in right hand drive vehicles"
KC07100119,"- RWD= Rear wheel drive
- Engine mounted sideways
- Can be fit in right hand drive vehicles
- To be mounted without special PTO option"
KC08010120,"- ""E""=TM-UNICLA
- For TM and UP-UPF Ø119 only Poly-V 8K
- Use the special tool: P/N 1149000115 to fit the kit (ref. Toyota 09330-00021 and 09213-58013).
- Can be fit in right hand drive vehicles"
KC08010121,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- To install this kit it is essential to use the special tool code P/N 1149000092 or Ref.Ford 303-393.
- TM-08 Must be mounted version ""E""."
KC08020122,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles"
KC08020123,"- Not to be used on 18 ton vehicles.
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC08030124,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- For SD5H14 / SD5L14 and SD7H15 / SD7L15 Ø119 only Poly-V 7K-8K
- Can be fit with electrical power steering
- Can be fit in right hand drive vehicles.
- MUFFLER option recommended."
KC08030125,"- Can't be fit in right hand drive vehicles.
- Fittings not included in the kit"
KC08030126,"- ""E""=TM / QUE / UNICLA
- Must be equipped with Power take-off ""V66"".
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC08040127,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Vehicles must be equipped with the option ""CABADP"" information connector, Version ""CHAUFO"" free pulley Ø125 or Version ""CHOREC"" free pulley Ø76 + Belt ref. 82.00.821.813
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC08040128,"- TM-21 Clutch 1B Ø150 / 2B Ø149
- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC08040129,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC08040130,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox
- NOT SUITABLE FOR Euro VI-D vehicles"
KC08040131,"- Can't be fit in right hand drive vehicles
- No suitable for 220HP engine with automatic gear box
- Fittings not included in the kit
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC08040132,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KC08050133,"- Vehicle must be eqquiped with option RVI - 1EZ02
- Water pipe must be Ref.: 7482241760.
- Can be fit in right hand drive vehicles"
KC08050134,- Can be fit in right hand drive vehicles
KC08060135,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles."
KC08060136,- Can be fit in right hand drive vehicles
KC08070138,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles
- RWD:Rear wheel drive"
KC08090139,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC08090140,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC08100141,"- Only for vehicles with original N63 PTO option (Bracket compressor and crankshaft pulley).
- Can be fit in right hand drive vehicles."
KC08110142,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- Can be fit in right hand drive vehicles.
- To install this kit it is essential to use the special tool code P/N 1149000142
- For compressor TM-08/UP-90 ordered P/N 1128000142."
KC08110143,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KC08110144,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles."
KC08120145,"- Can be fit in right hand drive vehicles
- It can't be fit in normative Euro 5 vehicles"
KC09010146,- Can be fit in right hand drive vehicles
KC09020147,- Can be fit in right hand drive vehicles
KC09030148,"- Kit not suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Kit not suitable for the model 2018. Check SB18030033"
KC09030149,"- Can be fit in right hand drive vehicles.
- Only for vehicles with original option MAN 120FF.
- Fittings not included, see drawing."
KC09030150,"- ""E""=TM-UNICLA;""S""=SANDEN.
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles"
KC09030151,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles"
KC09030155,"- ""E""=TM / QUE / UNICLA
- To install this kit it is essential to use the special tool code P/N 1140000155
- Can be fit in right hand drive vehicles"
KC09030156,- Can be fit in right hand drive vehicles
KC09030157,- Can be fit in right hand drive vehicles
KC09040158,"- Can be fit in right hand drive vehicles
- Suitable for Automatic Gear Box"
KC09040159,"- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111000076
- Can be fit in right hand drive vehicles"
KC09050160,"- Kit not suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Kit not suitable for the model 2018. Check SB18030033"
KC09050161,"- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit."
KC09050162,"- Kit not suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles.
- Kit not suitable for QP25 compressor
- Kit not suitable for the model 2018. Check SB18030033"
KC09050163,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Vehicles must be equipped with the option ""CABADP"" information connector, Version ""CHAUFO"" free pulley Ø125 or Version ""CHOREC"" free pulley Ø76 + Belt ref. 82_00_821_ 813
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC09060164,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Not suitable for vehicles equipped with front pneumatic suspension"
KC09060165,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Not suitable for vehicles equipped with front pneumatic suspension"
KC09060166,"- The vehicle must be equipped with Mercedes-Benz MN9 option.
- Can be fit in right hand drive vehicles.
- Fittings not included, see drawing."
KC09060167,"- The vehicle must be equipped with Mercedes-Benz MN9 option.
- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit."
KC09060168,"- Tool Crankshaft Pulley not included. P/N 1152000168.
- Can be fit in right hand drive vehicles"
KC09070169,"- Can be fit in right hand drive vehicles.
- Only for vehicles without original option MAN 120FF.
- Fittings not included, see drawing."
KC09070170,"- Can be fit in right hand drive vehicles
- Only for vehicles with original option MAN 120FF."
KC09070171,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA;""S""=SANDEN (only for SD7H15)
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped with the N63 crankshaft pulley
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111200171
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171 (Intercooler)."
KC09070172,"THIS KIT IS ONLY COMPATIBLE WITH VEHICLES THAT HAVE THE ORIGINAL CRANKSHAFT PULLEY MERCEDES A6510300803 OR A6510300703
- RWD= Rear wheel drive
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles without original N63 PTO option.
- Can be fit in right hand drive vehicles."
KC09080173,"- Can be fit in right hand drive vehicles
- Only for vehicles with original N63 PTO option
- Version ""E"" no available for SANDEN"
KC09090174,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Only for vehicles equipped with the N63 crankshaft pulley
- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111200171.
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171."
KC09090175,"- Only for vehicles equipped with the N63 crankshaft pulley
- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111200171
- Short intercooler hose (in order to avoid interferences with the kit) not included. Order P/N 1170000171.
- Can be fit in right hand drive vehicles"
KC09090176,"- Kit not suitable for vehicles equipped with pneumatic suspension in the front axis.
- ""E""=TM-UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles.
- Kit not suitable for the model 2018. Check SB18030033"
KC09090177,"- Can be fit in right hand drive vehicles.
- Only for vehicles without original option MAN 120FF."
KC09090178,"- Can be fit in right hand drive vehicles
- It can't be fit in normative Euro 5 vehicles"
KC09090179,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KC09100180,"- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- Fittings supplied with refrigeration unit.
- Can be fit in right hand drive vehicles.
- Poly-V clutch not included, request P/N 1112000180."
KC09100181,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF"
KC09100182,"- Can be fit in right hand drive vehicles
- Only for vehicles without original option MAN 120FF"
KC09100183,"- Can be fit in right hand drive vehicles.
- Fittings not included, see drawing."
KC09110184,- Can be fit in right hand drive vehicles
KC09120185,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF
- IMPORTANT: Check in the Service Bulletin SB17110031 the suitability of the vehicle with our kits"
KC10010186,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit."
KC10010188,"- ""E""=TM-UNICLA
- Only for vehicles with 6 speeds gear manual box
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD"
KC10020189,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA"
KC10030190,- Can be fit in right hand drive vehicles
KC10040191,"- ""E""=TM-UNICLA
- Only for vehicles with 5 speeds gear manual box
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD"
KC10050192,"- Only for vehicles with original N63 PTO option.
- When the vehicle is not equipped with the N63 option order, P/N 1170000192.
- Can be fit in right hand drive vehicles."
KC10050193,"- Fittings supplied with refrigeration unit.
- Can't be fit in right hand drive vehicles.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC10050194,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Suitable on vehicles WITHOUT optional power take off - PFMot
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA"
KC10050195,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles"
KC10070197,"- ""E""=TM-UNICLA
- Only for vehicles with 6 speeds gear manual box
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD"
KC10070198,"- ""E""=TM-UNICLA
- Only for vehicles with 5 speeds gear manual box
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD"
KC10080199,"- The vehicle must be equipped with special engine bracket DAF P/N 1735015-00.
- Fittings supplied with refrigeration unit."
KC10080200,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles."
KC10090201,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Suitable on vehicles WITHOUT optional power take off - PFMot
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA"
KC10090202,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC10090203,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN (only for SD7H15).
- SD5H14-SD7H15 Ø119 only 7K-8K
- For vehicles with ECO (Start& Stop) option requested belt P/N 1262602307. Only kits with special clutch.
- For TM-15/UP-150/SD7H15 Recommended fittings, 90º.
- Can be fit in right hand drive vehicles.
- IMPORTANT. The kit with special clutch (option ""E"") is not suitable in vehicles with automatic gear box."
KC10090204,"- ""E""=TM / QUE / UNICLA
- For vehicles with ECO (Start& Stop) option requested belt P/N 1262602307. Only kits with special clutch.
- Can be fit in right hand drive vehicles.
- IMPORTANT. The kit with special clutch (option ""E"") is not suitable in vehicles with automatic gear box."
KC10100206,"- Can be fit in standard vehicles, without options
- Can be fit in right hand drive vehicles
- Water pipe must be Ref.: 7482241760
- Compressor fittings optional: P/N 1175000206 (CR2318), P/N 1176000206 (CR2323)"
KC10110207,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box"
KC10120211,"- Can be fit in right hand drive vehicles.
- Only for vehicles without original option MAN 120FF."
KC10120212,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- Can be fit in right hand drive vehicles"
KC10120213,"- Can be fit in standard vehicles, without options.
- Can be fit in right hand drive vehicles.
- Water pipe must be Ref.: 7482241760."
KC11030214,"- Fittings supplied with refrigeration unit.
- Can't be fit in right hand drive vehicles.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC11030215,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC11030216,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for 220HP engine with automatic gear box.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC11030217,"- Can't be fit in right hand drive vehicles
- No suitable for 220HP engine with automatic gear box
- Fittings not included in the kit
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC11030218,"- Can be fit in right hand drive vehicles.
- Fittings not included, see drawing."
KC11030219,"- Can't be fit in right hand drive vehicles.
- Fittings not included in the kit"
KC11040220,"- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles without original N63 PTO option.
- Can be fit in right hand drive vehicles."
KC11040222,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box"
KC11040223,- Can be fit in right hand drive vehicles
KC11050227,"- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles with option ECO (Start & Stop).
- Can be fit in right hand drive vehicles."
KC11050228,"- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles with option ECO (Start & Stop).
- Can be fit in right hand drive vehicles."
KC11050229,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension"
KC11050230,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KC11050231,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles.
- Only for vehicles without original N63 PTO option."
KC11050232,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Only for vehicles without original N63 PTO option."
KC11050236,- Can be fit in right hand drive vehicles
KC11060237,"- Can be fit in right hand drive vehicles.
- Kit not suitable for the model 2017. Check SB17020028"
KC11060238,"- Can be fit in right hand drive vehicles
- Fittings supplied with refrigeration unit
- VEHICLE'S VOLTAGE 12 V"
KC11070239,"- The vehicle must be equipped with Mercedes-Benz MN9 option.
- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit."
KC11070240,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Not suitable for vehicles equipped with front pneumatic suspension"
KC11070241,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Suspension type: FSCM or FPCM.
- Special option Front Traverse â€œFRIGOBLOCK""
- Not suitable for vehicles equipped with front pneumatic suspension"
KC11080242,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles
- Model 35S15 / 35C15 can also be equipped with the 2.3l engine"
KC11090243,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Suspension type: FSCM or FPCM.
- Special option Front Traverse â€œFRIGOBLOCK""
- Not suitable for vehicles equipped with front pneumatic suspension"
KC11090245,"- The vehicle must be equipped with special option DAF: AFRU462 / AFRU519 / AFRU520 and STD engine rubber mounts.
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC11100247,"- Can be fit in right hand drive vehicles.
- Only for vehicles with original option MAN 120FF."
KC11100248,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles."
KC11110250,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Suspension type: FSCM or FPCM.
- Special option Front Traverse â€œFRIGOBLOCK""
- Not suitable for vehicles equipped with front pneumatic suspension"
KC11110252,"- ""E""=TM / QUE / UNICLA
- RWD:Rear wheel drive
- Can be fit in right hand drive vehicles"
KC11120253,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- Can be fit in right hand drive vehicles
- Model 35C15 can also be equipped with the 3.0l engine
- IMPORTANT: This kit is not suitable for the Daily 2014 version"
KC11120254,"- ""E""=TM / QUE / UNICLA
- ""S"" only for SD7H15 / SD7L15
- RWD: Rear wheel drive
- Can be fit on AWD vehicles
- Can be fit on right hand drive vehicles"
KC11120255,- Can be fit in right hand drive vehicles
KC12010256,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Can be fit in right hand drive vehicles"
KC12010257,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- For TM and UP-UPF Ø119 only Poly-V 8K
- Can be fit in right hand drive vehicles"
KC12010258,"- RWD:Rear wheel drive
- Can be fit in right hand drive vehicles"
KC12010259,"- ""E""=TM / QUE
- RWD:Rear wheel drive
- Can be fit in right hand drive vehicles"
KC12010260,"- Vehicle must be eqquiped with power take off, Volvo option PTER-100
- Can be fit in right hand drive vehicles"
KC12010261,
KC12010262,"- Can be fit in right hand drive vehicles.
- Kit not suitable for the model 2017. Check SB17020028"
KC12020263,"- Not to be used on 18 ton vehicles
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC12020264,"- Can be fit in right hand drive vehicles.
- When vehicle is not equipped with the crankshaft pulley N63, request code P/N 1111200171.
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171 (Intercooler)."
KC12020265,- Can be fit in right hand drive vehicles
KC12030266,- Can be fit in right hand drive vehicles
KC12030267,- Can be fit in right hand drive vehicles
KC12040269,"- Can be fit in standard vehicles, without options
- Can be fit in right hand drive vehicles"
KC12050270,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit with electrical power steering
- Can be fit in right hand drive vehicles.
- Kit not suitable in vehicles with steel crankshaft pulley ref. 9810714580 / 126011 Check in the Service Bulletin SB15050026"
KC12050271,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop
- MUFFLER option recommended"
KC12050272,- Can be fit in right hand drive vehicles
KC12060274,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Not suitable for vehicles equipped with front pneumatic suspension"
KC12060275,"- ""E""=TM-UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles"
KC12060276,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit with electrical power steering
- Can be fit in right hand drive vehicles.
- Kit not suitable in vehicles with steel crankshaft pulley ref. 9810714580 / 126011 Check in the Service Bulletin SB15050026"
KC12060277,"- FWD= Front wheel drive
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC12060278,"- FWD= Front wheel drive
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC12060279,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Only for vehicles with original option MAN 331FL"
KC12060280,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Only for vehicles with original option MAN 331FL"
KC12060281,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Only for vehicles with original option MAN 331FL"
KC12060282,- Can be fit in right hand drive vehicles
KC12070283,"- The vehicle must be equipped with special engine bracket DAF P/N 1735015-00
- Fittings not included in the kit"
KC12070284,"- The vehicle must be equipped with special option DAF: AFRU462 / AFRU519 / AFRU520 and STD engine rubber mounts.
- Fittings supplied with refrigeration unit.
- Can be fit in right hand drive vehicles."
KC12070285,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Model 35C15 can also be equipped with the 3.0l engine
- IMPORTANT: This kit is not suitable for the Daily 2014 version"
KC12070286,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles"
KC12070287,- Can be fit in right hand drive vehicles
KC12090289,"- Can be fit in right hand drive vehicles
- Model 35C15 can also be equipped with the 3.0l engine"
KC12090290,"- Can be fit in right hand drive vehicles.
- Kit not suitable for the model 2017. Check SB17020028"
KC12090291,"- Only for compressor SD5H09 with special pulley Ø150
- Carrier Transicold compressor P/N 79-60649-00
- Poly-V clutch not included"
KC12090292,"- Only for compressor SD5H09 with special pulley Ø150
- Carrier Transicold compressor P/N 79-60649-00
- Poly-V clutch not included
- Can be fit with electrical power steering"
KC12100293,"- The vehicle must be equipped with special option DAF: AFRU462 / AFRU519 / AFRU520 and STD engine rubber mounts.
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC12100294,"- Can be fit in right hand drive vehicles
- Fittings supplied with refrigeration unit
- VEHICLE'S VOLTAGE 12 V"
KC12110295,"- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- See Fitting Instructions for details on the refer system ACC wire connection
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1150000295"
KC12110296,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles before year 2016"
KC12110297,- Can be fit in right hand drive vehicles
KC12120298,"- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC12120298Z,"- ""E""=TM / QUE / UNICLA
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC12120299,"- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
This kit is suitable only for vehicles after March 2014. For the rest of the vehicles, contact Oliva Torras Mount & Drive Kits"
KC12120300,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100300"
KC12120300Z,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100300"
KC12120301,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension"
KC12120302,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles before year 2016"
KC12120304,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles before year 2016"
KC13010305,"- Can be fit in right hand drive vehicles
- Fittings supplied with refrigeration unit
- VEHICLE'S VOLTAGE 12 V"
KC13020306,"- Not to be used on 18 ton vehicles
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC13020307,"- Can't be fit in right hand drive vehicles
- No suitable for 220HP engine with automatic gear box
- Fittings not included in the kit
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC13020308,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles before year 2016"
KC13020309,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit"
KC13020310,"- Can't be fit in right hand drive vehicles
- TM-21 Clutch 1B Ø150 / 2B Ø149
- Fittings not included in the kit"
KC13020311,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit"
KC13020312,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit"
KC13020313,- Can be fit in right hand drive vehicles
KC13020314,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC13020315,"- Not to be used on 18 ton vehicles
- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC13020316-D,- Can be fit on right hand drive vehicles
KC13020316-E,- Can be fit on right hand drive vehicles
KC13020316-F,- Can be fit on right hand drive vehicles
KC13030317,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15.
- Can be fit in right hand drive vehicles"
KC13030318,"- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- See Fitting Instructions for details on the refer system ACC wire connection
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1150000295"
KC13030319,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit in right hand drive vehicles
- Dacia recommend not to use STOSTA option in vehicles with a refrigeration system
THE AIR CONDITIONING COMPRESSOR MUST BE REMOVED
- MUFFLER option recommended"
KC13030320,"- ""E""=TM / QUE / UNICLA
- UNICLA: Clutch plate Ø120 not suitable.
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- Renault recommend not to use the STOSTA option in vehicles equipped with a refrigeration system
THE AIR CONDITIONING COMPRESSOR MUST BE REMOVED
- MUFFLER option recommended.
- Vehicles with CABADP adaptation require pre-wired connector P/N 1180000300"
KC13040322,"- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
This kit is suitable only for vehicles after March 2014. For the rest of the vehicles, contact Oliva Torras Mount & Drive Kits"
KC13040323,"- ""E""=TM / QUE / UNICLA
- Not recommended in vehicles with automatic gear box.
- Can be fit in right hand drive vehicles
- It canâ€™t be fit in vehicles whit Start & Stop"
KC13040324,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles."
KC13050326,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- To install this kit it is essential to use the special tool code P/N 1149000142"
KC13050327,"- The vehicle must be equipped with Mercedes-Benz MN9 option
- Can be fit in right hand drive vehicles"
KC13050328,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles
- Model 35C15 can also be equipped with the 2.3l engine"
KC13050329,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC
- The CG8 option must be removed, if present, in order to install the kit."
KC13050330,- Can be fit in right hand drive vehicles
KC13050331,- Can be fit in right hand drive vehicles
KC13050332,- Can be fit in right hand drive vehicles
KC13050333,- Can be fit in right hand drive vehicles.
KC13050334,"- The vehicle must be equipped with special engine bracket DAF P/N 1735015-00
- Fittings not included in the kit"
KC13060335,#¡VALOR!
KC13070336,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC13080337,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Only for vehicles with special option Front Traverse (IVECO ULM). Check SB18050035"
KC13080338,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only for vehicles with special option Front Traverse (IVECO ULM)"
KC13080339,- Can be fit in right hand drive vehicles
KC13080340,"- FWD: Front wheel drive
- Can be fit on right hand drive vehicles"
KC13080340-C,"- FWD: Front wheel driven
- Can be fit on right hand drive vehicles"
KC13090341,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gearbox
- To install this kit it is essential to use the special tool code P/N 1140000155"
KC13090342,"- Can be fit in right hand drive vehicles.
- Only for vehicles without original N63 PTO option."
KC13120343,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KC13120344,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KC14010345,- Can be fit in right hand drive vehicles
KC14010346,- Can be fit in right hand drive vehicles.
KC14020347,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KC14020348,"- Can be fit in right hand drive vehicles
- Not to be used on 18 or 19 ton vehicles"
KC14020349,"- Can be fit in right hand drive vehicles
- Not to be used on 18 or 19 ton vehicles"
KC14030350,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- For SD5H14/SD5L14 and SD7H15 Ø119 only Poly-V 6K-7K-8K
- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC
- The CG8 option must be removed, if present, in order to install the kit."
KC14030351,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KC14040352,"- Only for vehicles equipped with the original N7C option
- Can be fit in right hand drive vehicles
- For vehicles before 2022 see Service Bulletin SB23020059
P/N 1121998057"
KC14040354,
KC14040355,IT'S NECESSARY TO BUY SEPARATELY THE AUTOMATIC TENSIONER 1160000355
KC14040356,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH OPTION N7C"
KC14050357,"- Can be fit in right hand drive vehicles
- Kit not suitable for vehicles 6x2 with directional rear axle (TA-HYDRS)
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1140000358"
KC14050358,"- Can be fit in right hand drive vehicles
- Kit not suitable for vehicles 6x2 with directional rear axle (TA-HYDRS)
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1140000358"
KC14050359,"- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
For this kit is necessary the N7G/N7H/V1Y option"
KC14050360,"- Kit also suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
For this kit is necessary any of the following options: N7G, or N7H, or V1Y"
KC14050361,- Can be fit in right hand drive vehicles
KC14050362,- Can be fit in right hand drive vehicles
KC14050363,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14/SD5L14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles
- This kit is only suitable for vehicles with intercooler hose A9065285182
- For vehicles equipped with the N63 option: compressor bracket plus crankshaft pulley"
KC14060364,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- FOR VEHICLES EQUIPPED WITH OPTION N7C"
KC14060365,"- Can be fit in right hand drive vehicles
- Only for vehicles WITHOUT the original N7 options"
KC14060366,"- Can be fit in right hand drive vehicles
- Only for vehicles WITHOUT the original N7 options"
KC14070367,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100300"
KC14070368,- Can be fit in right hand drive vehicles
KC14070369,"- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -.
- Suitable on vehicles WITH optional power take off - PFMot
- When PFMot option is not present please select the power take off crankshaft pulley kit P/N 1111100369"
KC14070369Z,"- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option 8LN + wiring harness.
- Suitable on vehicles WITH optional power take off PFMot
- When PFMot option is not present please select the power take off crankshaft pulley kit P/N 1111100369"
KC14070370,"- ""E""=TM / QUE
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles"
KC14080372,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -."
KC14080373,"- ""E""=TM / QUE / UNICLA
- Not available for TM / UP-UPF Poly V 6K A Ø119
- ONLY FOR A/C COMPRESSOR ON THE RIGHT HAND SIDE (direction of motion), consult Service Bulletin
- Can be fit in right hand drive vehicles"
KC14080374,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KC14090375,"- Can be fit in right hand drive vehicles
- Only suitable for vehicles before year 2017"
KC14090376,"- Can be fit in right hand drive vehicles
- The kit is suitable for vehicles with D8K engine, equipped with pneumatic suspension in the front axis.
- See Fitting Instructions for details on the refer system ACC wire connection
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1150000295"
KC14090377,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398"
KC14090378,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -."
KC14120379,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
Suitable for vehicles WITH A/C from factory, but the A/C compressor must be removed"
KC14120380,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC14120381,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- VEHICLES MUST BE EQUIPPED WITH AIR CONDITIONING COMPRESSOR, BUT THE AIR CONDITIONING COMPRESSOR MUST BE REMOVED WHEN MOUNTED THE REFRIGERATION COMPRESSOR KIT"
KC14120382,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC14120383,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD5H14 / SD5L14.
- Can be fit in right hand drive vehicles."
KC14120384,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- IMPORTANT. The kit is not suitable for vehicles with automatic gear box."
KC14120385,"- Suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- The kit is not suitable for vehicles 4x4"
KC14120386,"- Suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- The kit is not suitable for vehicles 4x4"
KC15010387,"THIS KIT IS ONLY COMPATIBLE WITH VEHICLES THAT HAVE THE ORIGINAL CRANKSHAFT PULLEY MERCEDES LITENS A6510351612, A6510351812 OR A6510350912
- RWD= Rear wheel drive
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles without original N63 PTO option.
- Can be fit in right hand drive vehicles."
KC15020388,"- ""E""=TM / QUE / UNICLA
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -.
- Suitable on vehicles WITH optional power take off - PFMot
- When PFMot option is not present please select the power take off crankshaft pulley kit P/N 1111100369"
KC15050389,"- ""E""=TM / QUE / UNICLA
- Replace transmision kit every 30.000Km. P/N 1125000094
- Cannot be fit in right hand drive vehicles"
KC15050390,"- Can be fit in right hand drive vehicles
- Use tool to block the flywheel P/N 1149000412
- Important to check radiator pipe length, see SB24110072.
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" JI01 option (connector 15 ways C036L1A)"
KC15050390Z,"- Can be fit in right hand drive vehicles
- Use tool to block the flywheel P/N 1149000412
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option"
KC15060391,"- ""E""=TM / QUE / UNICLA
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" JI01 option (connector 15 ways C036L1A)"
KC15060392,"- No compatible Kit in vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
For this kit is necessary the N7G/N7H/V1Y option"
KC15060393,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles after january 2016"
KC15060393-B,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- ASK THE AFTERSALES DEPARTMENT FOR THE SUITABILITY OF THE KIT IN THE VEHICLE"
KC15060394,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles after year 2016"
KC15060395,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Only suitable for vehicles before year 2016"
KC15070396,- Can be fit in right hand drive vehicles
KC15070397,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- KIT NOT SUITABLE FOR VEHICLES WITH STTA OPTION (START/STOP AND REVERSIBLE ALTERNATOR 180A)
- Kit not suitable for the model 2018"
KC15070398,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Kit with two automatic tensioners
- Model 35S16 / 35C16 can also be equipped with the 2.3l engine"
KC15070398Z,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Kit with two automatic tensioners
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 2.3l engine"
KC15070399,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Kit with two automatic tensioners
- Recommended fittings 135º"
KC15070400,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 can also be equipped with the 3.0l engine"
KC15070400Z,"- UNICLA: Clutch drive plate Ø120 not suitable.
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 can also be equipped with the 3.0l engine"
KC15090402,- Can be fit in right hand drive vehicles
KC15090403,"- ""E""=TM-QP
- Can be fit in vehicles with DSG automatic gear box
- CANNOT be fit in right hand drive vehicles
- CANNOT be fit on all wheel drive vehicles AWD
- Not suitable for engine powers above 150Hp"
KC15090403Z,"- Can be fit in vehicles with DSG automatic gear box
- CANNOT be fit in right hand drive vehicles
- CANNOT be fit on all wheel drive vehicles AWD
- Not suitable for engine powers above 150Hp"
KC15100404,- Can be fit in right hand drive vehicles
KC15110405,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD
- Can be fit in vehicles with DSG automatic gear box
- KIT NOT SUITABLE FOR VW T6.1
- Itâ€™s possible to mount the kit on vehicles with AC. In this case the AC compressor must be removed in order to fit the kit and the refrigeration compressor."
KC15120407,- Can be fit in right hand drive vehicles
KC16060408,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN
- ""S"" only for SD7H15.
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles.
- Kit NOT suitable for MY 2019"
KC16070409,- Can be fit in right hand drive vehicles
KC16070410,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15 / SD7L15
- UNICLA: Clutch drive plate Ø120 not suitable.
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles"
KC16070411,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- KIT NOT SUITABLE FOR VEHICLES WITH STTA OPTION (START/STOP AND REVERSIBLE ALTERNATOR 180A)
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option"
KC16080412,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- Suitable for vehicles with automatic gear box.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- The kit is not suitable for vehicles 4x4
- Use tool to block the flywheel P/N 1149000412"
KC16080412Z,"- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- The kit is not suitable for vehicles 4x4
- Use tool to block the flywheel P/N 1149000412"
KC16090413,"- ""E""=TM / QUE / UNICLA; ""S""=SANDEN
- ""S"" only for SD7H15
- For SD5H14 and SD7H15 Ø119 only Poly-V 7K-8K
- Can be fit in right hand drive vehicles
- Itâ€™s possible to mount the kit on vehicles with AC, although the AC compressor will have to be removed.
In order to use SSMK 1183000415, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC16090414,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles
- For compressor TM-08/QP-08, order P/N 1129000414."
KC16090415,"- Cannot be fit in right hand drive vehicles
- Kit not suitable for the models 2018 Combo Life and Combo Cargo"
KC16090415D,"- Cannot be fit in right hand drive vehicles
In order to use SSMK 1183000415, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC16100416,"- Can be fit in right hand drive vehicles
- Itâ€™s possible to mount the kit on vehicles with AC, although the AC compressor must be removed in order to fit the kit and the refrigeration compressor. In those cases, the accessories belt must be exchanged (use original reference Fiat 6PK1526: FPT 55218885).
- NOT SUITABLE FOR Euro VI-D vehicles"
KC16100417,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- KIT NOT SUITABLE FOR VEHICLES WITH STTA OPTION (START/STOP AND REVERSIBLE ALTERNATOR 180A)"
KC16100418,- Can be fit in right hand drive vehicles
KC16110419,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC16110420,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC16120421,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Can be fit on all wheel drive vehicles AWD
- Can be fit in vehicles with DSG automatic gear box
- Itâ€™s possible to mount the kit on vehicles with AC. In this case the AC compressor must be removed in order to fit the kit and the refrigeration compressor."
KC16120422,"- ""E""=TM / QUE / UNICLA
- RWD: Rear wheel drive
- Can be fit on AWD vehicles
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- Not suitable for ECOBLUE HYBRID version
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC17010423,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option (check installation procedure)
- Not suitable for the automatic gearbox"
KC17010424,"- ""E""=TM / QUE / UNICLA
- RWD: Rear wheel drive
- Can be fit on AWD vehicles
- Can be fit in right hand drive vehicles
- For compressor TM-08/QP-08, order P/N 1129000414."
KC17010425,"- Can be fit in right hand drive vehicles.
- Fittings supplied with refrigeration unit.
- Only for vehicles with original option MAN 331FL"
KC17020426,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100300"
KC17020427,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles"
KC17020428,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles"
KC17030429,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles"
KC17030432,- To install this kit it is essential to use the special tool code P/N 1140000432
KC17050434,- Can be fit in right hand drive vehicles
KC17050435,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- The kit is not suitable for vehicles 4x4"
KC17060436,"- Can be fit in right hand drive vehicles
- Kit with independent belt for the refrigeration compressor
- Kit not suitable for the models 2018 Combo Life and Combo Cargo"
KC17060437,"- ""E""=TM / QUE / UNICLA;
- FWD= Front wheel drive
- Can be fit in right hand drive vehicles.
- VW RECOMMENDS TO USE THE CRANKSHAFT PULLEY 04L105251K or 04L105251P.
- When vehicle is not equipped with this crankshaft pulley, order the reference P/N 1111100437
- To disable START / STOP it is necessary to visit an official workshop. The KGF module with IS2 software is required to do this.
- According to the manufacturer, for the installation and running of an additional unit, the engine speed at idling, must not be below 1.040 rpm.
- The kit is suitable for vehicles 4x4
- Suitable for vehicles with automatic gear box
- MUFFLER option recommended P/N 1159000127
- NOT COMPATIBLE with alternator of 230A or higher"
KC17070438,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Kit with independent belt for the refrigeration compressor
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" JI01 option (connector 15 ways C036L1A)"
KC17070439,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Suitable for automatic gear box
- Not suitable for model N57"
KC17070440,"- ""E""=TM / QUE
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- In case of vehicles with AC, the AC compressor must be removed"
KC17080441,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- ONLY FOR A/C COMPRESSOR ON DRIVER SIDE, consult Service Bulletin"
KC17090442,"- Kit also suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
For this kit is necessary the N7G/N7H/V1Y option"
KC17110443,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Can be fit in vehicles with DSG automatic gear box
- Can be fit on all wheel drive vehicles AWD
- KIT NOT SUITABLE FOR ENGINES EURO 6D TEMP"
KC17110445,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Cannot be fit in vehicles with DSG automatic gear box
- Cannot be fit on all wheel drive vehicles AWD
- Vehicles with 6 speed manual gear box, select the kit P/N KC19990445
- KIT NOT SUITABLE FOR ENGINES EURO 6D TEMP"
KC17110446,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- ONLY FOR A/C COMPRESSOR ON PASSENGER SIDE, consult Service Bulletin"
KC17110447,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000074"
KC17110448,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles"
KC17110449,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000149"
KC17120450,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles"
KC18010451,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles
- AC compressor and refrigeration compressor must not work at the same time"
KC18010452,"- ""E""=TM / QUE / UNICLA
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option 8LM -."
KC18020453,"- ""E""=TM / QUE / UNICLA;
- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- THE BODYBUILDER RECOMMENDS TO USE THE CRANKSHAFT PULLEY 04L105251L or 04L105251R.
- When vehicle is not equipped with this crankshaft pulley, order the reference P/N 1111100453
- To disable START / STOP it is necessary to visit an official workshop. The KGF module with 631JD software is required to do this.
- According to the manufacturer, for the installation and running of an additional unit, the engine speed at idling, must not be below 1.040 rpm.
- Suitable for vehicles with automatic gear box
- NOT COMPATIBLE with alternator of 230A or higher"
KC18020454,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- The vehicle must be equipped with special option DAF-006785.
Attention, the option 006785 cannot be ordered when the truck is equipped with AS Tronic transmission."
KC18040455,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000149"
KC18040456,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000149"
KC18050459,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles."
KC18050460,"- Can be fit in right hand drive vehicles
- Only for vehicles WITHOUT original option MAN 120FF or 0P0GP"
KC18050461,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC18060462,"- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box."
KC18070463,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles."
KC18070464,"- Can be fit in right hand drive vehicles.
- Kit not suitable for QP25 compressor"
KC18070465,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles
- In case of a Euro 4, 5 o 5b+ vehicle, ask for the reference P/N 1128000465"
KC18070465-G,"- Kit suitable for both oversized and small oil sump
- ""E""=TM / QUE / UNICLA
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
Vehicles with Hi-Matic 8-speed automatic gearbox manufactured between October 2021 and February 2022, refer to Service Bulletin SB22050057
- In case of Euro 4, 5, 5b+, ask for part number (Not included) P/N 1128000465
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC18070465-H,"- Kit suitable for both oversized and small oil sump
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
Vehicles with Hi-Matic 8-speed automatic gearbox manufactured between October 2021 and February 2022, refer to Service Bulletin SB22050057
- In case of Euro 4, 5, 5b+, ask for part number (Not included) P/N 1128000465
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC18080467,"- ""E""=TM / QUE / UNICLA
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -."
KC18090468,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can't be fit on AWD vehicles
- Original accessories belt conserved/modified crossmember bar
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 2.3l engine
- Not suitable for MY2024 vehicles"
KC18090468-A,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can't be fit on AWD vehicles
- Original accessories belt conserved/modified crossmember bar
- Not suitable for MY2024 vehicles"
KC18100469,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Not suitable for front suspension QTOR."
KC18100469-B,"- Can be fit in right hand drive vehicles
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Not suitable for front suspension QTOR.
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 2.3l engine
- Not suitable for MY2024 vehicles"
KC18100470,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- KIT NOT SUITABLE FOR VEHICLES WITH STTA OPTION (START/STOP AND REVERSIBLE ALTERNATOR 180A)
- KIT SUITABLE ONLY FOR VEHICLES WITH AIR CONDITIONING COMPRESSOR nº 9810349980
NOT SUITABLE with vehicles equipped with shock absorber bar
url=#https://www.olivatorras.com/kits/show_doc/SB23050060%20PSA%20Protection%20Crash%20Bar%20PSA%201.6.pdf#/urlFor more information (SB23050060)#/mask
For these cases order kit P/N KC23040569"
KC18110471,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA;
- For SD5H14 and SD7H15 contact with After Sales Department
- Can be fit in right hand drive vehicles.
- Kit with automatic tensioner. Long maintenance intervals
- Only for vehicles equipped with the N63 crankshaft pulley
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111200171
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171 (Intercooler)."
KC18110472,"THIS KIT IS ONLY COMPATIBLE WITH VEHICLES THAT HAVE THE ORIGINAL CRANKSHAFT PULLEY MERCEDES A6510300803 OR A6510300703
- RWD= Rear wheel drive
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles without original N63 PTO option.
- For SD5H14 and SD7H15 contact with After Sales Department
- Kit with automatic tensioner. Long maintenance intervals
- Can be fit in right hand drive vehicles."
KC18110473,"THIS KIT IS ONLY COMPATIBLE WITH VEHICLES THAT HAVE THE ORIGINAL CRANKSHAFT PULLEY MERCEDES LITENS A6510351612, A6510351812 OR A6510350912
- RWD= Rear wheel drive
- Models 210 / 310 / 510 CDI, Engine 95CV (70kW) you must order P/N 1170000171.
- Only for vehicles without original N63 PTO option.
- For SD5H14 and SD7H15 contact with After Sales Department
- Kit with automatic tensioner. Long maintenance intervals
- Can be fit in right hand drive vehicles."
KC18120474,"- ""E""=TM / QUE / UNICLA;""S""=SANDEN (only for SD7H15)
- Can be fit in right hand drive vehicles."
KC18120475,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA;""S""=SANDEN (only for SD7H15)
- Can be fit in right hand drive vehicles.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC19010476,"- Can't be fit in right hand drive vehicles
- COMPATIBLE with automatic gearbox ALLISON
- NOT SUITABLE FOR Euro VI-D vehicles"
KC19010477,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit"
KC19020481,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
NOT SUITABLE with vehicles equipped with shock absorber bar
url=#https://www.olivatorras.com/kits/show_doc/SB22030055%20PSA%20Protection%20Crash%20Bar#/urlFor more information#/mask"
KC19030482,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles."
KC19030483,"- ""E""=TM / QUE / UNICLA
- Not available for TM / UP-UPF Poly V 6K A Ø119
- Can be fit in right hand drive vehicles
- ONLY FOR A/C COMPRESSOR ON LEFT HAND SIDE (direction of motion), consult Service Bulletin"
KC19040484,- Can be fit in right hand drive vehicles
KC19040485,- Can be fit in right hand drive vehicles
KC19040486,"- ""E""=TM / QUE
- Can be fit in right hand drive vehicles.
- Cannot be fit in vehicles with automatic gear box"
KC19050487,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles."
KC19060488,
KC19060489,- Can be fit in right hand drive vehicles
KC19060490,"- Can be fit in right hand drive vehicles
- When the vehicle is not equipped with the automatic tensioner Ref. 21983653 order, P/N 1160000490."
KC19070491,"- ""E""=TM / QUE
- Suitability for right hand drive vehicles
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option 8LM -.
- Use crankshaft pulley locking tool P/N 1149000300
- Water pump pulley tool not included in kit P/N 1149000491
- NOT SUITABLE for Euro 6d-full vehicles"
KC19070492,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option"
KC19090493,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- If the vehicle is equipped with the Start & Stop, IT IS MANDATORY to disable this option
- Deactivation kit available. P/N 1183000493
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC19090494,"- Water pipe must be Ref.: 7482241760.
- Can be fit in right hand drive vehicles"
KC19110495,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC19110496,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC19120497,"- ""E""=TM / QUE / UNICLA
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
Suitable for vehicles WITH A/C from factory, but the A/C compressor must be removed"
KC20010498,"- ""E""=TM / QUE / UNICLA
- RWD: Rear wheel drive
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- If the vehicle is equipped with the Start & Stop, IT IS MANDATORY to disable this option
- Deactivation kit available. P/N 1183000493
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC20050500,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC20060501,"- RWD= Rear wheel drive
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC20060501-A,"- RWD= Rear wheel drive
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC20070502,"- Can be fit in right hand drive vehicles.
- Only for vehicles with original option FRIGOBLOCK (MAN commercial code 0P0GH)"
KC20070503,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- ONLY FOR A/C COMPRESSOR ON DRIVER SIDE, consult Service Bulletin"
KC20070503-A,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- ONLY FOR A/C COMPRESSOR ON DRIVER SIDE, consult Service Bulletin"
KC20070504,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- ONLY FOR A/C COMPRESSOR ON PASSENGER SIDE, consult Service Bulletin"
KC20080505,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- To install this kit it is essential to use the special tool code P/N 1140000155
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC20080506,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box"
KC20080507,"- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -."
KC20080508,- Can be fit in right hand drive vehicles
KC20090510,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- For vehicles WITHOUT N62/N63 crankshaft pulley - A654 032 10 00
- Use crankshaft pulley locking tool P/N 1149000398
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC20120512,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Use crankshaft pulley locking tool 1149000398
- Not included in the kit:
Crankshaft pulley locking tool P/N 1149000398"
KC21020513,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC21020514,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)
- Not suitable for MY2024 vehicles
NOT SUITABLE for PSA engine. See Service Bulletin SB23060061"
KC21050517,"- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles
- Can be fit in vehicles with DSG automatic gear box
- Can be fit on all wheel drive vehicles AWD"
KC21070524,- Can be fit in right hand drive vehicles.
KC21080525,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- For vehicles WITHOUT N62/N63 crankshaft pulley - A654 030 91 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC21080526,"- Can be fit in right hand drive vehicles
- Only for vehicles WITH original option MAN 120FF or 0P0GP
- For vehicles not equipped with air conditioning, select also the crankshaft pulley P/N 1111000149"
KC21090527,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC21090528,"- Can't be fit in right hand drive vehicles
- Fittings not included in the kit
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC21090529,"- Can be fit in right hand drive vehicles.
- Only for vehicles with original option FRIGOBLOCK (MAN commercial code 0P0GH)
- To mount a compressor TM/QP 21 you must buy the manifold P/N 1170000004"
KC21090530,"- Can be fit in right hand drive vehicles
- Not to be used on 18 or 19 ton vehicles"
KC21090530-A,"- Can be fit in right hand drive vehicles
- Not to be used on 18 or 19 ton vehicles"
KC21090531,- Can be fit in right hand drive vehicles
KC21090532,"- Kit not suitable for vehicles equipped with pneumatic suspension in the front axis.
- ""E""=TM-UNICLA
- Can be fit in right hand drive vehicles.
- Not suitable for alternators over 130 Ah."
KC21110533,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped WITH the N62/N63 crankshaft pulley - A654 030 91 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC21110535,"- ""E""=TM / QUE / UNICLA;
- RWD= TracciÃ³n trasera
- Compatible en vehÃ­culos con el volante a la derecha."
KC21110536,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles."
KC22010537,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- Suitable for vehicles with automatic gear box.
- IMPORTANT Check if you have 1 or 2 automatic tensioners.
If you have 1 tensioner, buy bracket P/N 1131000412
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- The kit is not suitable for vehicles 4x4
- Use tool to block the flywheel P/N 1149000412"
KC22010538,"- Can be fit in right hand drive vehicles
- Factory option 2NC is recommended in order to disable Start/Stop of the vehicle.
In order to use SSMK 1183000415, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC22020540,"- Kit also suitable for vehicles equipped with pneumatic suspension in the front axis.
- Can be fit in right hand drive vehicles
- IMPORTANT: Check in the Service Bulletin SB15030025 the suitability of the vehicle with our kits
For this kit is necessary any of the following options: N7G, or N7H, or V1Y"
KC22020541,"- ""E""=TM / QUE / UNICLA
- PTO Suitable for Automatic Gear Box
- Suitable for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -."
KC22020542,"- Can be fit in right hand drive vehicles
- Fittings not included in the kit
- This kit is not suitable for vehicles with the option N7."
KC22020543,
KC22030544,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Reference J533005727 original ISUZU"
KC22030546,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the whole N63 option: original bracket + N62/N63 crankshaft pulley - A654 032 10 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC22030547,"- ""E""=TM-QP
- Can be fit in vehicles with DSG automatic gear box
- Can be fit in right hand drive vehicles
- This kit is only suitable for the original Volskwagen Crankshaft pulley 04L105251F"
KC22030549,"- ""E""=TM-QP
- FWD= Front wheel drive
- Can be fit in vehicles with DSG automatic gear box
- Can be fit in right hand drive vehicles
- This kit is only suitable for the original Volskwagen Crankshaft pulley 04L105251F"
KC22060551,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option"
KC22070552,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Suitable only for vehicles WITH optional power take off crankshaft pulley - PFMot"
KC22070553,"- Can be fit in right hand drive vehicles
- Kit not suitable for vehicles 6x2 with directional rear axle (TA-HYDRS)
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1140000358"
KC22100555,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the whole N63 option: original bracket + N62/N63 crankshaft pulley - A654 032 10 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC22100556,"- ""E""=TM / QUE /
- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box.
- If the vehicle is equipped with the Start & Stop system, this function must be disabled by installing the corresponding kit listed below."
KC22110557,"- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- The kit is suitable for vehicles with DTi8 engine, equipped with pneumatic suspension in the front axis.
- See Fitting Instructions for details on the refer system ACC wire connection
- For vehicles not equipped with air conditioning, select also the idler pulley bracket ass'y P/N 1150000295"
KC23010558,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox up to 2024.
- Not suitable for MY2024 vehicles with ZF Automatic Transmission.
- NOT COMPATIBLE with ALLISON automatic gearbox"
KC23010559,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
If you have the AAM module, It is necessary to visit an official workshop.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PWTKE
- When PWTKE option is not present, select the kit P/N 1111100559"
KC23010559-A,"- FWD= Front wheel drive
- Suitability for right hand drive vehicles
- Suitability for automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100559"
KC23010559-B,"- FWD= Front wheel drive
- Suitability for right hand drive vehicles
- Suitability for automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA o CABADP -.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PFMot
- When PFMot option is not present, select the kit P/N 1111100559"
KC23010560,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC"
KC23010561,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Not suitable for vehicles equipped with WABCO ABS PUMP"
KC23010562,"- Can be fit in right hand drive vehicles
- Suitable on vehicles WITH optional mPTO NA7"
KC23020563,- Can be fit in right hand drive vehicles
KC23020563-A,"- Kit suitable for both oversized and small oil sump
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
Vehicles with Hi-Matic 8-speed automatic gearbox manufactured between October 2021 and February 2022, refer to Service Bulletin SB22050057
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC23030564,- Can be fit in right hand drive vehicles
KC23030566,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- Kit with automatic tensioner. Long maintenance intervals
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC23030567,"- RWD= Rear wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- For vehicles WITHOUT N62/N63 crankshaft pulley - A654 032 10 00
- Kit with automatic tensioner. Long maintenance intervals
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KC23030568,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC23040570,"- Can be fit in right hand drive vehicles
- Only for vehicles WITHOUT the original N7 options"
KC23040570-A,"- Can be fit in right hand drive vehicles
- Only for vehicles WITHOUT the original N7 options"
KC23040571,"- Can be fit in right hand drive vehicles.
- Fittings not included in the kit
- Not suitable for vehicles equipped with front pneumatic suspension
- Not suitable for vehicles equipped with WABCO ABS PUMP"
KC23050572,- Can be fit in right hand drive vehicles
KC23050572-B,- Can be fit in right hand drive vehicles
KC23070573,"High Performance Kit, refer to Service Bulletin SB23100063
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes
- Can be fit in right hand drive vehicles
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- Can be fit on AWD vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC23070573-A,"High Performance Kit, refer to Service Bulletin SB23100063
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- Can be fit on AWD vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC23070573-B,"High Performance Kit, refer to Service Bulletin SB23100063
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- Can be fit on AWD vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
url=#https://www.olivatorras.com/kits/info_eines.php?id_prod=20406&type=eines#/urlFor more information#/mask"
KC23070574,"- High Performance Kit
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KC23070575,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- Can't be fit in right-hand drive vehicles
- NOT SUITABLE with OEM auxiliary heating system 7VF / 7VL
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC23070575-A,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can't be fit in right-hand drive vehicles
- Suitable for the automatic gear box.
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC23070575-C,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- Can't be fit in right-hand drive vehicles
- NOT SUITABLE with OEM auxiliary heating system.
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC23100577,"High Performance Kit, refer to Service Bulletin SB23100063
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- Can be fit in right hand drive vehicles
- Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Kit with two automatic tensioners
- Model 35S16 / 35C16 can also be equipped with the 2.3l engine"
KC23110579,"- CANNOT be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Use crankshaft pulley locking tool not included in the kit: P/N 1149007027
- Not suitable for right-hand drive"
KC23110580,"- Compatible with right-hand drive vehicles
- Only for vehicles equipped WITH the full OTOKAR option"
KC23110581,"- RWD= Rear wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
If you have the AAM module, It is necessary to visit an official workshop."
KC24010582,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Kit with two automatic tensioners
- Model 35S16 / 35C16 can also be equipped with the 2.3l engine"
KC24020583,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA -.
- Suitable on vehicles WITHOUT A/C
- PWTKE option is NOT requiered."
KC24020584,"- RWD= Rear Wheel drive
- ""E""=TM / QUE / UNICLA"
KC24040586,"- Compatible with right-hand drive vehicles
- Only for vehicles equipped WITH the full OTOKAR option"
KC24040587,"High Performance Kit, refer to Service Bulletin
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)
NOT SUITABLE for PSA engine. See Service Bulletin SB23060061"
KC24050588,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- Suitable for vehicles with automatic gear box.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- The kit is not suitable for vehicles 4x4
- Use tool to block the flywheel P/N 1149000412"
KC24050588-A,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles.
- Suitable for vehicles with automatic gear box.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option
- The kit is not suitable for vehicles 4x4
- Use tool to block the flywheel P/N 1149000412"
KC24060590,"- ""E""=TM / QUE / UNICLA
- Can't be fit in right-hand drive vehicles.
- Suitable for the automatic gearbox
- In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC24060590-B,"- ""E""=TM / QUE / UNICLA
- Can't be fit in right-hand drive vehicles.
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC24060591,"- ""E""=TM / QUE / UNICLA
- PTO Suitable for Automatic Gear Box
- Suitable for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -.
- Use crankshaft pulley locking tool P/N 1149000300
- Water pump pulley tool not included in kit P/N 1149000491"
KC24070594,"- KIT NOT SUITABLE FOR OVERSIZED OIL SUMP IVECO OPTION. Ref. 72617 (SB20100050)
- ""S"" only for SD7H15 / SD7L15
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine"
KC24070594-A,"- ""S"" only for SD7H15 / SD7L1
- In the case of UNICLA, please ask Oliva Torras team
- Can be fit in right hand drive vehicles
- In case of a Euro 4, 5 o 5b+ vehicle, ask for the reference P/N 1128000465"
KC24080598,"High Performance Kit
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- ""E""=TM / QUE / UNICLA
- Can't be fit in right-hand drive vehicles.
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC24080598-A,"High Performance Kit
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- ""E""=TM / QUE / UNICLA
- Can't be fit in right-hand drive vehicles.
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC25010606,"- Can be fit in right hand drive vehicles
- Vehicles 136hp, 160hp, 180hp with Hi-Matic 8-speed automatic gearbox, order P/N 1150008086
- On vehicles with Automatic Transmission Hi-Matic, recommended to use crankshaft pulley locking tool P/N 1149000398
- Can't be fit on AWD vehicles
- Original accessories belt conserved/modified crossmember bar
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 2.3l engine"
KC25020607,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- Not suitable for ECOBLUE HYBRID version
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC25020608,"- ""E""=TM / QUE / UNICLA
- RWD: Rear wheel drive
- Can be fit on AWD vehicles
- Can be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- Not suitable for ECOBLUE HYBRID version
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)"
KC25020609,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- Can't be fit in right-hand drive vehicles
- NOT SUITABLE with OEM auxiliary heating system 7VF / 7VF
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC25020609-A,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- Can't be fit in right-hand drive vehicles
- NOT SUITABLE with OEM auxiliary heating system.
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC25020609-B,"- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- Can't be fit in right-hand drive vehicles
- NOT SUITABLE with OEM auxiliary heating system 7VF / 7VF
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC25020610,"- ""E""=TM / QUE / UNICLA;
- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Suitable for automatic gear box
- Only suitable for electric steering pump"
KC25020611,"SUITABLE only with right-hand drive vehicles
- ""E""=TM / QUE / UNICLA
- Suitable for the automatic gearbox
- In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KC25020612,"Long Maintenance Kit
- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
- Suitable on vehicles WITH optional power take off crankshaft pulley - PWTKE
- When PWTKE option is not present, select the kit P/N 1111100559"
KC25060618,"SUITABLE only with right-hand drive vehicles
- ""E""=TM / QUE / UNICLA
- FWD: Front wheel drive
- Compatible on vehicles with all-wheel drive AWD
- NOT SUITABLE with OEM auxiliary heating system.
- Suitable for the automatic gear box.
- Coolant Ciscuit tip refer to Service Bulletin SB24100071
To install this kit it is essential to use the special tool code:
- P/N 1149000575 (FOR MANUAL GEARBOX)
- P/N 1150000575 (FOR AUTOMATIC GEARBOX)"
KC25070619,"Long Maintenance Kit
- ""E""=TM / QUE
- Can be fit on AWD vehicles
- Can be fit in right hand drive vehicles
- UNICLA: Clutch drive plate Ø120 not suitable.
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- Kit suitable for both oversized and small oil sump
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
- Suitable for MY2024 vehicles"
KC25070620,"High Performance Kit & Long Maintenance
- Kit suitable for both oversized and small oil sump
- ""E""=TM / QUE
- Can be fit in right hand drive vehicles
- Vehicles equipped with QTOR bar - Buy manifold P/N 1170000465
- UNICLA: Clutch drive plate Ø120 not suitable.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
Vehicles with Hi-Matic 8-speed automatic gearbox manufactured between October 2021 and February 2022, refer to Service Bulletin SB22050057
- (Recommended) A/C belt mounting tool not included in kit P/N 1161000465
- Suitable for MY2024 vehicles"
KC25070621,"Long Maintenance Kit
- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
If you have the AAM module, It is necessary to visit an official workshop."
KC25080622,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Reference J533005727 original ISUZU
- The cab must be lowered using the original ISUZU tool Part No. J533005845B
- For vehicles WITHOUT A/C order part number P/N 1150000622"
KC25080623,"- High Performance Kit
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- The cab must be lowered using the original ISUZU tool Part No. J533005845B
- For vehicles WITHOUT A/C order part number P/N 1150000622"
KC25080624,"High Performance Kit
- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Kit with two automatic tensioners
- Recommended fittings 135º
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 2.3l engine"
KC25090625,"High Performance Kit
- Kit specially designed to optimize the functionality of the refrigeration unit in urban environments and high temperatures, where the vehicle makes multiple deliveries on short routes.
- RWD= Rear wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
If you have the AAM module, It is necessary to visit an official workshop."
KC25100626,- Compatible with right-hand drive vehicles
KC25100629,- Can be fit in right hand drive vehicles.
KC26010630,"- FWD= Front wheel drive
- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles."
KC26020631,- Compatible with right-hand drive vehicles
KF22070900,"- Suitable for Towing Hook PSA code 98 296 445 80
- Suitable only for L2-L3 chassis"
KF22090901,"- Suitable for Towing Hook PSA code 98 296 445 80
- Suitable only for L2-L3 chassis"
KF23050904,"- Can be fit in right hand drive vehicles.
- Suitable for vehicles with Manual and Automatic Transmission.
- Suitable for L1 - L2 chassis only."
KG13049001,- Can be fit in right hand drive vehicles.
KG13049002,"THIS KIT IS ONLY COMPATIBLE WITH VEHICLES THAT HAVE THE ORIGINAL CRANKSHAFT PULLEY MERCEDES: A6510300803, A6510300703, A6510351612, A6510350912
- THIS KIT IS COMPATIBLE ONLY WITH VEHICLES WITH INTERCOOLER HOSE A9065285182
- Only for vehicles without original N63 PTO option.
- Can be fit in right hand drive vehicles.
- Suitable for vehicles with Manual Gear box or Automatic Transmission"
KG13049003,"- Kit not suitable for vehicles with Start/Stop
- N63 option is not necessary, although it does not imply any incompatibility.
- This kit is only compatible with vehicles that have the original crankshaft pulley Mercedes: A6420300603
- Can be fit in right hand drive vehicles.
- To install this kit it is essential to use the tool to remove generator pulley P/N 1140009003
- The kit is suitable for vehicles 4x4
- For vehicles with fan model A0002007323, order P/N 1117000238. Read Service Bulletin SB19060041."
KG13069005,UNDER REQUEST
KG13089007,- Can be fit in right hand drive vehicles
KG15069010,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox"
KG15079011,"- RWD= Rear wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA"
KG15079012,"- Can be fit in right hand drive vehicles
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 can also be equipped with the 2.3l engine"
KG15099013,"- Suitable for vehicles with manual gear box or 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 can also be equipped with the 3.0l engine"
KG16029014,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- To install this kit it is essential to use the special tool code P/N 1140000155
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG16029015,"- Can be fit in right hand drive vehicles
- It is essential to use the supplied centring tool. Check Service Bulletin SB17050029
- To install this kit it is essential to use the special tool code P/N 1140009015"
KG16029016,"- Model 35S15 / 35C15 can also be equipped with the 3.0l engineÃ§
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic."
KG16039017,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- To install this kit it is essential to use the special tool code P/N 1140000155 and the bracket P/N 1128000114
- Kit only compatible with the crankshaft pulley ref. 504017415. If the vehicle is not equipped with this pulley, order P/N 1111209017
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG16129019,"- Can be fit in right hand drive vehicles.
- Kit not suitable for the model 2017."
KG17049020,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC"
KG17049020-B,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with automatic gear box DUONIC"
KG17059021,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- To install this kit it is essential to use the special tool code P/N 1149000300"
KG17109022,"- RWD: Rear wheel drive
- Can be fit on AWD vehicles
- Can be fit in right hand drive vehicles
- To install this kit it is essential to use the special tool code P/N 1149000422"
KG18059024,"- Can be fit in right hand drive vehicles
- Use tool to block the flywheel P/N 1149000412
- The kit is not suitable for vehicles 4x4
In order to use SSMK 183000514, the vehicle must be equipped from factory with Conversion interface Box"" JI01 option (connector 15 ways C036L1A)"
KG18109025,"- Kit suitable for both oversized and small oil sump
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 / 40C16 / 50C16 can also be equipped with the 3.0l engine
Vehicles with Hi-Matic 8-speed automatic gearbox manufactured between October 2021 and February 2022, refer to Service Bulletin SB22050058
- In case of a Euro 4, 5 o 5b+ vehicle, ask for the reference P/N 1129009025"
KG18109026,"- FWD= Front wheel drive
- Can be fit in right hand drive vehicles."
KG20019029,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- To install this kit it is essential to use the special tool code P/N 1149000300"
KG20029030,"- Can be fit in right hand drive vehicles
- Suitable for front suspension QTOR.
- Can be fit on AWD vehicles
- Model 35S16 / 35C16 can also be equipped with the 2.3l engine"
KG20069031,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box"
KG20069032,"- Can't be fit in right hand drive vehicles
- Compatible with ZF automatic gearbox
- NOT COMPATIBLE with ALLISON automatic gearbox"
KG20099033,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box"
KG20109034,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KG20109034-A,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit."
KG21069036,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG22039037,"- FWD= Front wheel drive
- Can be fit in right hand drive vehicles.
- Only for vehicles equipped WITH the N62/N63 crankshaft pulley - A654 030 91 00
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
COMING SOON"
KG22069038,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KG23119039,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below."
KG24079040,"- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG24079040-A,"- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG24079040-B,"- Can be fit in right hand drive vehicles
In order to use SSMK 1183000514, the vehicle must be equipped from factory with Conversion interface Box"" 081 option (connector 15 ways C036L1A)"
KG25099041,"- RWD= Rear wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with a Start & Stop system, the idle speed must be increased by installing the corresponding kit listed below.
If you have the AAM module, It is necessary to visit an official workshop."
KG26039043,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles"
KH14127001,"- 15 cc: P1DCN2015XA40C03N HPI
- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Can be fit in right hand drive vehicles
- Suitable on vehicles WITHOUT optional power take off - PFMot
- Requires high idle - CABADP - when the vehicle is equipped with the Start & Stop option - STOSTA
- Clutch 0903740-3017 KEB"
KH15017002,"- 15 cc: P1DCN2015XA40C03N HPI
- 12 cc: P1DCN2012XA40C03N HPI
- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Clutch 0903740-3017 KEB"
KH15017003,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- It is required to purchase the fan channeler IVECO ref. 5802725496.
- Mandatory increase of engine idle speed to 1150 rpm. Operation to be done in an official Iveco Dealer.
- IPH hydraulic pump neither included in the kit nor available in Oliva Torras catalogue"
KH16017005,"- 8 cc: P1DCN2008CA40C03N HPI
- ""E""=TM / QUE / UNICLA
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop - STOSTA - it requires high idle - available with factory option RALENT or CABADP -.
- Clutch 0903740-3017 KEB"
KH17067006,"- Can be fit in right hand drive vehicles
- The kit is not suitable for vehicles 4x4
- Clutch 0903740-3017 KEB"
KH17077007,"- 15 cc: P1DCN2015XA40C03N HPI
- 12 cc: P1DCN2012XA40C03N HPI
- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Clutch 0903740-3017 KEB"
KH17087008,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Suitable for automatic gear box
- Clutch 0903740-3017 KEB"
KH17087009,"- Can be fit in right hand drive vehicles
- Suitable for automatic gear box"
KH17127010,"- Use the special tool: P/N 1149000115 to fit the kit (ref. Toyota 09330-00021 and 09213-58013).
- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19037011,"- Can be fit in right hand drive vehicles.
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option (check installation procedure)
- Not suitable for the automatic gearbox
- The kit is not suitable for vehicles 4x4
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19067012,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19067013,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Suitable for automatic gear box
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19067013-C,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Suitable for automatic gear box
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19107014,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Use crankshaft pulley locking tool 1149000398
- Not included in the kit:
Crankshaft pulley locking tool P/N 1149000398
Pump clutch P/N 1112007024
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH19107015,"- Suitable for MY2024 vehicles
- Model 35S15 / 35C15 can also be equipped with the 3.0l engine
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic.
- In case of Euro 4, 5, 5b+, ask for part number (Not included) P/N 1140008120
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16,6cc (For other displacement consult) P/N 1197161000"
KH19117016,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH20017017,"- Can be fit in right hand drive vehicles
- Suitable for vehicles with 8-Speed Automatic Transmission Hi-Matic. Use crankshaft pulley locking tool P/N 1149000398
- Can be fit on AWD vehicles
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16,6cc (For other displacement consult) P/N 1197161000"
KH20087018,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Use tool to block the flywheel P/N 1149000412
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,5cc (For other displacement consult) P/N 1197121000
- The kit is not suitable for vehicles 4x4
- If the vehicle is equipped with the Start & Stop, it is necessary to disable this option"
KH20107019,"- RWD= Rear wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc P/N 1197121000"
KH21017020,"- FWD: Front wheel drive
- Can be fit in right hand drive vehicles
- Not suitable for ECOBLUE HYBRID version
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH21087022,"- FWD: Front wheel drive
- Suitable with right hand drive vehicles
- Suitable for the automatic gear box.
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121100"
KH21087022-B,"- FWD: Front wheel drive
- Can't be fit in right hand drive vehicles
- Suitable for the automatic gear box.
- Not suitable for ECOBLUE HYBRID version
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121100"
KH21087023,"- FWD= Front wheel drive
- According to bodybuilder indications, the power take off is not suitable for the automatic gear box.
- Suitability for right hand drive vehicles
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option RALENT o CABADP -.
- Kit with automatic tensioner
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH21097024,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH21117025,"- Can be fit in right hand drive vehicles
- Suitable for vehicles equipped with automatic gear box
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16cc (For other displacement consult) P/N 1197162000"
KH22117026,"- FWD= Front wheel drive
- Can be fit in right hand drive vehicles.
- Suitable with AWD / 4X4
- Only for vehicles equipped with the N62/N63 crankshaft pulley - A654 032 10 00
- When vehicle is not equipped with the crankshaft pulley N63, request the crankshaft pulley P/N 1111100500
- To disable START / STOP it is necessary to visit an official workshop.
- For vehicles version Van, the factory option EK1 is required for the electric connections of the refrigeration unit.
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH23077027,"- Can be fit in right hand drive vehicles
- Suitable for vehicles 4x2 and 4x4
- Use crankshaft pulley locking tool not included in the kit: P/N 1149007027
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH23117028,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA -.
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH24057030,"- ""E""=TM / QUE / UNICLA
- Can be fit in right hand drive vehicles
- Suitable for automatic gear box
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16 cc (For other displacement consult) P/N 1197161000"
KH24067032,"- RWD= Rear Wheel drive
- Can't be fit in right hand drive vehicles.
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16cc (For other displacement consult) P/N 1197161000"
KH24087033,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH24087033-A,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH25017034,"- FWD= Front wheel drive
- Suitable for right hand drive vehicles
- Suitable for the automatic gearbox
- Kit with automatic tensioner. Long maintenance intervals
- If the vehicle is equipped with the Start & Stop, it requires high idle - available with factory option WIADA o CABADP -.
- Not included in the kit:
Pump clutch P/N 1112007021
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121000"
KH25107036,"- FWD: Front wheel drive
- Suitable with right hand drive vehicles
- Suitable for the automatic gear box.
To install this kit it is essential to use the special tool code:
- P/N 1149000422 (FOR MANUAL GEARBOX)
- P/N 1150000422 (FOR AUTOMATIC GEARBOX)
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 12,7cc (For other displacement consult) P/N 1197121100"
KH25127038,"- Can be fit in right hand drive vehicles
- Not included in the kit:
Pump clutch P/N 1112007022
Hydraulic pump 16cc P/N 1197161000
Hydraulic pump 19cc P/N 1197191000"
Kits T6_old original sump oil,"The following available kits for the VW T5 are also suitable for vehicles VW T6 equipped with the original sump oil Ref: 03L 103 603H:
KC10010188
KC10040191
KC10070197
KC10070198"
"""

_CACHE = None

def get_system_prompt() -> str:
    global _CACHE
    if _CACHE is None:
        _CACHE = (
            _PROMPT_V10
            + "\n\n---\n\n"
            + "## BASE DE DATOS\n\n```csv\n" + _BD_SEL + "\n```\n\n"
            + "## NOTAS TÉCNICAS\n\n```csv\n" + _BD_NOTES + "\n```\n"
        )
    return _CACHE

def _client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

def chat(messages: list) -> str:
    # system como lista con cache_control — sube limite a 1M tokens
    r = _client().messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": get_system_prompt(),
            "cache_control": {"type": "ephemeral"}
        }],
        messages=messages,
    )
    return r.content[0].text

def chat_with_image(messages: list, image_data: bytes, media_type: str = "image/jpeg") -> str:
    b64 = base64.standard_b64encode(image_data).decode("utf-8")
    msgs = list(messages)
    txt = msgs[-1]["content"] if msgs else ""
    msgs[-1] = {"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
        {"type": "text", "text": txt}
    ]}
    r = _client().messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": get_system_prompt(),
            "cache_control": {"type": "ephemeral"}
        }],
        messages=msgs,
    )
    return r.content[0].text
