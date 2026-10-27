# Análisis de Montaje Etapa por Etapa para Domos de Acero

Prototipo para hackathon que muestra cómo cambian las fuerzas y la estabilidad de un domo de acero a medida que se instalan sus barras.

> **Aviso:** es un prototipo demostrativo. No sirve para autorizar un montaje real.

## 1. Problema

En una empresa que diseña y fabrica domos de acero, hay que asegurar que la estructura sea estable durante la construcción, no solo terminada. Un domo puede tener más de 2,000 barras. La idea es analizar la estructura cada vez que se instalan una o varias barras (el usuario define cada cuántas).

## 2. Objetivo del hackathon

Demostrar, con un domo pequeño de ejemplo, cómo evolucionan estas cantidades en cada etapa de instalación:
- Fuerza axial y esfuerzo en las barras.
- Desplazamientos de los nodos.
- Reacciones en los apoyos.
- Estabilidad (detectar si la estructura activa es un mecanismo).

El enfoque está en que el cálculo funcione y se pueda explicar, no en tener un producto completo.

## 3. Modelo de cálculo

- **Armadura articulada 3D:** las barras transmiten solo fuerza axial. Cada nodo tiene 3 grados de libertad (x, y, z).
- **Cargas:**
  - Peso propio acumulado de las barras ya instaladas.
  - Carga de instalación (por ejemplo, el peso de una persona) en el nodo o barra asignado a cada etapa.
- **Etapas:** se parte del primer anillo ya instalado y se activan barras por etapa (1, 3 o N, según defina el usuario).
- **Solución:** en cada etapa se resuelve un equilibrio nuevo solo con las barras activas. Las barras no instaladas no aportan peso ni rigidez.
- **Estabilidad:** si la matriz de rigidez es singular o casi singular, la etapa se marca como "inestable" en lugar de fallar.
- **Indicador de pandeo (opcional):** relación entre la fuerza de compresión y la carga de Euler, `Pcr = π²EI/L²`.

## 4. Entradas (plantilla de Excel fija)

| Hoja | Columnas |
|---|---|
| Nodos | ID, x, y, z |
| Barras | ID, nodo i, nodo j, perfil, **etapa de instalación** |
| Perfiles | nombre, área, inercia (opcional), módulo E, densidad o peso por metro |
| Apoyos | nodo, restricciones (x, y, z) |
| Cargas | etapa, nodo de aplicación, magnitud de la carga de instalación |
| Criterios | esfuerzo admisible o fluencia |

Además, un caso de validación: una armadura simple con solución manual o, si existe, un domo analizado en SAP2000 o RISA.

## 5. Salidas

- Vista 3D del domo coloreada por esfuerzo o utilización.
- Slider para recorrer las etapas.
- Gráfica de fuerza máxima contra etapa.
- Tabla de resultados por barra y por etapa, con exportación a Excel.
- Indicación clara de las etapas inestables.

## 6. Tecnología propuesta

- Python con NumPy y SciPy (`scipy.sparse`).
- Pandas y openpyxl para leer y escribir Excel.
- Plotly para la vista 3D.
- Streamlit como interfaz.

## 7. Viabilidad

- **Memoria:** no es problema. Un domo de 2,000 barras tiene unos 3,000 grados de libertad y una matriz dispersa de pocos MB.
- **Tiempo:** cada etapa se resuelve en milisegundos. Cientos o miles de etapas toman segundos o pocos minutos.
- **La dificultad real es la física:** mecanismos durante el montaje, y la diferencia entre una armadura y las conexiones reales.

## 8. Plan (4–5 horas)

| Hora | Tarea |
|---|---|
| 0:00–0:30 | Plantilla de Excel y script que genera un domo de ejemplo (unas 60 barras) |
| 0:30–1:30 | Solver de armadura 3D, apoyos, fuerzas axiales y reacciones. Validar con caso manual |
| 1:30–2:15 | Bucle por etapas, peso propio acumulado, carga de instalación y detección de inestabilidad |
| 2:15–3:30 | Interfaz Streamlit con carga de Excel, slider y vista 3D |
| 3:30–4:15 | Gráfica por etapa, tabla y exportación |
| 4:15–5:00 | Pulido, demo y lista de limitaciones |

## 9. Fuera de alcance

- Importación desde CAD.
- Edición libre del modelo.
- Múltiples normas y combinaciones de carga.
- Momentos, flexión local, pandeo con revisión normativa y capacidad de conexiones.
- Fricción real, apuntalamientos, grúas o cables temporales.
- Historia física detallada del montaje y análisis no lineal (P-Δ).
- Interfaz pulida.

## 10. Limitaciones

- La armadura articulada es conservadora: puede declarar inestable algo que en la realidad aguanta gracias a conexiones rígidas.
- Resolver cada etapa desde cero es una aproximación del proceso real.
- Los resultados no son una aprobación de seguridad.

## 11. Después del hackathon

1. Elementos de viga (marco) con 6 grados de libertad por nodo.
2. Pandeo y revisión según norma (AISC u otra).
3. Importación CAD o DXF.
4. Análisis P-Δ y apuntalamientos temporales.
5. Optimización de la secuencia de montaje.
