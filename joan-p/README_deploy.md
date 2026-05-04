# README · Selector de Kits — Deployment Guide

## Archivos del repositorio

| Archivo | Descripción |
|---|---|
| `app.py` | Front-end Streamlit |
| `selector.py` | Lógica de negocio — carga BD + prompt + llama a Claude |
| `bbdd_kits_v8.xlsx` | Base de datos de kits (v8) |
| `prompt_selector_kits_v10.md` | Prompt del asistente (v10) |
| `requirements.txt` | Dependencias Python |
| `logo.jpg` | Logo Oliva Torras |
| `.streamlit/config.toml` | Configuración de tema Streamlit |

---

## Cómo actualizar la BD o el prompt en el futuro

1. Sube el nuevo `.xlsx` o `.md` al repositorio (sustituye el archivo anterior).
2. Edita `selector.py` y cambia las constantes en la sección `Paths`:
   ```python
   EXCEL_PATH  = BASE_DIR / "bbdd_kits_vX.xlsx"   # ← nuevo nombre
   PROMPT_PATH = BASE_DIR / "prompt_selector_kits_vXX.md"  # ← nuevo nombre
   ```
3. Haz commit y push — Streamlit Cloud redespliega automáticamente.

---

## Variables de entorno requeridas en Streamlit Cloud

| Variable | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu clave de API de Anthropic |

Para configurarla: **Streamlit Cloud → tu app → Settings → Secrets**

```toml
# .streamlit/secrets.toml  (NO subir al repo — usar Secrets en la UI)
ANTHROPIC_API_KEY = "sk-ant-..."
```

---

## Modelo utilizado

`claude-sonnet-4-20250514` (Claude Sonnet 4 — última versión estable)

---

## Instalación local (desarrollo)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```
