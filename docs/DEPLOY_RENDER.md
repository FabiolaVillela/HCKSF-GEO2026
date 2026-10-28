# Publicar el simulador HTML en Render

El simulador (`simulador.html`) necesita el servidor de Python (`src/domestage/server.py`): todos los cálculos se hacen ahí. Por eso no se puede publicar como página estática (GitHub Pages) ni en Streamlit Community Cloud, que solo ejecuta `src/domestage/app.py`. [Render](https://render.com) ejecuta el servidor como *Web Service*.

## Archivos de despliegue

| Archivo | Para qué |
| --- | --- |
| `render.yaml` | Blueprint de Render: servicio web `domestage-plus`, plan gratuito, rama `main`, despliegue automático en cada push. |
| `.python-version` | Versión de Python (`3.12`; Render usa el último parche 3.12). |
| `requirements.txt` | Dependencias (las mismas que en local). |

Comando de arranque que usa Render:

```bash
PYTHONPATH=src python -m domestage.server --host 0.0.0.0 --port $PORT
```

Render define `PORT`. `--host 0.0.0.0` permite que el proxy de Render llegue al servidor. **En local no cambia nada**: sin opciones, el servidor sigue escuchando solo en `127.0.0.1:8503`. También acepta las variables de entorno `HOST` y `PORT`.

## Pasos (una sola vez)

1. Entra en <https://dashboard.render.com> e inicia sesión con tu cuenta de GitHub.
2. **New → Blueprint**.
3. Conecta el repositorio `FabiolaVillela/HCKSF-GEO2026` (si es la primera vez, Render pide permiso para leer tus repositorios).
4. Render detecta `render.yaml`. Revisa que el servicio sea `domestage-plus`, rama `main`, plan *Free*, y pulsa **Apply**.
5. Espera a que termine el primer *build* (instala `requirements.txt`, unos minutos). Cuando el estado sea **Live**, abre la URL que muestra Render (por ejemplo `https://domestage-plus.onrender.com`).

Después, cada merge en `main` vuelve a desplegar el servicio automáticamente.

### Alternativa sin Blueprint

**New → Web Service**, conecta el repositorio y usa:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `PYTHONPATH=src python -m domestage.server --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path | `/` |

## Antes de publicar: tenlo en cuenta

- **Sin contraseña:** cualquiera con la URL puede usar el simulador y subir DXF. El servidor no guarda archivos en disco (solo calcula y responde), pero si el modelo o los resultados son confidenciales, conviene agregar autenticación antes de compartir la URL.
- **Plan gratuito:** el servicio se suspende tras un tiempo sin visitas; la primera visita después tarda en despertar. La memoria y la CPU son limitadas: con el QuickDome y conexiones empotradas, calcular todas las etapas (gráficas, reporte, figuras, precálculo) tarda varios segundos más que en local.
- **Límites del motor:** 500 nodos, 5000 barras y DXF de hasta 20 MB.
- Los resultados son preliminares (ver `docs/AISC.md`); el simulador no es una aprobación de diseño.

## Comprobar en local que el comando de Render funciona

```bash
PORT=8600 PYTHONPATH=src .venv/bin/python -m domestage.server
```

Abre `http://127.0.0.1:8600`. (Usar `--host 0.0.0.0` en tu equipo lo haría visible en la red local; no hace falta para probar.)
