# Despliegue — Selector de Kits v7 (Claude-driven)

## Ficheros necesarios en el repo (carpeta joan-p/)

```
joan-p/
├── app.py                      ← NUEVO (sustituye el anterior)
├── selector.py                 ← NUEVO (solo filtrado Python)
├── prompt_selector_kits_v7.md  ← NUEVO (prompt que Claude lee en runtime)
├── bbdd_kits_v6.xlsx           ← BD existente (sin cambios)
├── logo.jpg                    ← existente (sin cambios)
└── requirements.txt            ← ver abajo
```

## requirements.txt

```
streamlit>=1.32.0
anthropic>=0.25.0
pandas>=2.0.0
openpyxl>=3.1.0
```

## Cambio de arquitectura

| Antes | Ahora |
|---|---|
| selector.py controla el flujo (next_question / apply_answer) | selector.py solo prefiltra la BD (filter_candidates) |
| Claude solo formatea el resultado final | Claude gestiona TODO el flujo de selección |
| Lógica hardcodeada en Python | Lógica en prompt v7 (editable sin tocar código) |
| Sin soporte de imágenes/fichas técnicas | Soporta imágenes de fichas técnicas |

## Cómo funciona

1. Usuario escribe (o adjunta imagen de ficha técnica)
2. `update_context()` detecta kit_type + brand + model del texto
3. `filter_candidates()` prefiltra la BD → max ~400 filas
4. El JSON filtrado se pasa a Claude como contexto en el system prompt
5. Claude aplica el prompt v7 y responde con la siguiente pregunta o resultado final
6. El contexto se actualiza con cada turno

## Variables de entorno

```
ANTHROPIC_API_KEY = sk-ant-...
```

## Notas importantes

- El fichero `prompt_selector_kits_v7.md` debe estar en la misma carpeta que `app.py`
- La BD `bbdd_kits_v6.xlsx` debe estar en la misma carpeta que `selector.py`
- Para actualizar el prompt: editar `prompt_selector_kits_v7.md` y hacer push — sin tocar código
