# Pitch Deck & Guion de Presentación: DomeStage · Geometrica Hackathon 2026

## 🎯 Concepto y Propuesta de Valor

**"Un domo de acero es una de las estructuras más resistentes del mundo una vez cerrado... pero durante su construcción está incompleto, vulnerable y propenso a mecanismos de colapso si no se analiza etapa por etapa."**

**DomeStage** es el primer simulador estructural interactivo a 60 FPS en el navegador que calcula el equilibrio elástico real, la estabilidad cinemática, las reacciones en apoyos y la verificación normativa ANSI/AISC 360-22 LRFD en cada paso del montaje (2 barras por etapa), directamente desde el archivo CAD/DXF de ingeniería.

---

## ⏱️ Estructura de la Presentación (Pitch de 5 Minutos)

| Tiempo | Diapositiva / Bloque | Mensaje Central | Demostración / GIF |
|---|---|---|---|
| **0:00 - 0:45** | **1. El Reto Oculto del Montaje** | Los domos se diseñan para su estado final. Durante el montaje no hay efecto membrana cerrado: el domo es un voladizo en el espacio. Un error de secuencia causa colapso o peligro para las cuadrillas. | *Imagen o esquema de domo incompleto en voladizo*. |
| **0:45 - 1:45** | **2. La Solución: DomeStage** | Pasamos de cálculos estáticos de días en software pesado a simulación dinámica en tiempo real en el navegador. Progresión real de 2 barras por etapa, paleta oficial Geometrica y carga directa desde DXF. | **GIF 1: Montaje Progresivo 60 FPS**. |
| **1:45 - 2:45** | **3. Física Real: Deformada y Reacciones** | No es una animación CAD vacía: hay una matriz de rigidez elástica tridimensional (pórticos rígidos 6 GDL) resolviendo el peso propio en cada paso. Visualización de flechas amplificadas y reacciones radiales/tangenciales. | **GIF 2: Deformada Amplificada y Vectores de Reacción**. |
| **2:45 - 3:45** | **4. Inteligencia de Seguridad: Mecanismos y Gráficas** | Detección matemática instantánea de mecanismos e inestabilidades. Gráficas de envolvente (fuerza axial y deflexión vs % de avance) para saber con precisión quirúrgica en qué etapa la estructura sufre más. | **GIF 3: Gráficas de Progreso y Detección de Inestabilidades**. |
| **3:45 - 4:30** | **5. Normativa AISC 360-22 y Reporte Ejecutivo** | Verificación LRFD de miembros HSS circulares ($1.4D$, $0.93t$, interacción $H1\text{-}1a/b$). Generación con 1 clic del reporte ejecutivo bilingüe en Excel con la memoria de cálculo de todo el montaje. | **GIF 4: Verificación AISC e Informe Excel**. |
| **4:30 - 5:00** | **6. Impacto en el Negocio & Conclusión** | Reducción drástica del riesgo en campo para cuadrillas y grúas, optimización de secuencias de montaje y ahorro masivo de horas de ingeniería. | *Diapositiva de cierre con llamada a la acción*. |

---

## 🎬 Detalle de los GIFs Integrados

### GIF 1: Recorrido Dinámico del Montaje Completo (0% a 100% · QuickDome Ø40 m)
- **Archivos**:
  - Vista Isométrica nivelada: `docs/gifs/domestage_app_demo.gif` (Montaje continuo de 0 a 100% sin saltos bruscos a AISC, con rotación 360° nivelada en el eje vertical Z).
  - Vista en Planta: `docs/gifs/domestage_plan_view_100pct.gif` (Vista cenital pura mostrando el cierre concéntrico de los anillos hasta el ápice y rotación en plano).
- **Qué muestra**: La estructura levantándose dinámicamente desde el anillo perimetral hasta el cierre del domo al 100%.
- **Detalle visual**:
  - Contorno magenta destacando las 2 barras recién instaladas en cada paso.
  - Gradiente elástico en tiempo real: azul para tracción, rojo para compresión, amarillo para esfuerzo nulo.
  - El slider y la barra de progreso avanzando coordinadamente a 60 FPS con precomputación instantánea.
- **Impacto para el juez**: Demuestra velocidad de cálculo, interactividad fluida y fidelidad geométrica a la secuencia real de ensamble.

### GIF 2: Deformada Amplificada y Vectores de Reacción
- **Qué muestra**:
  - Activación del switch *Show Amplified Nodal Deflection* y el slider multiplicador ($10\times$ a $100\times$) mostrando la flexión real de la cúpula bajo su propio peso.
  - Activación de *Show Support Reaction Vectors*, desplegando los conos 3D de empuje en la cimentación en coordenadas globales y cilíndricas (empuje radial hacia afuera y tangencial).
- **Impacto para el juez**: Evidencia que detrás del render hay un solver matricial de elementos finitos calculando desplazamientos reales milimétricos.

### GIF 3: Gráficas de Evolución y Detección de Mecanismos
- **Qué muestra**:
  - Panel inferior de gráficas SVG con las curvas de evolución de axiales máximos y deflexión máxima contra porcentaje de avance.
  - La línea verde punteada del slider moviéndose en sincronía con la gráfica.
  - Al simular una etapa inestable, el banner cambia a rojo alertando *"MECANISMO DETECTADO / UNSTABLE"* y la gráfica marca triángulos rojos de alerta.
- **Impacto para el juez**: Muestra que la herramienta previene colapsos antes de enviar a las cuadrillas a montar en campo.

### GIF 4: Verificación Normativa AISC 360-22 LRFD y Exportación Excel
- **Qué muestra**:
  - Selección del grado de acero (`ASTM A500 Grado C`) y activación de *Show AISC utilization*.
  - Las barras cambian a verde ($U \le 1.0$) o rojo ($U > 1.0$).
  - Inspección al hacer clic en una barra para ver la ecuación gobernante de interacción ($H1\text{-}1a / H1\text{-}1b$) y esbeltez $KL/r$.
  - Clic en *Export results report (Excel)* mostrando la descarga del archivo `.xlsx` listo para firma de ingeniería.
- **Impacto para el juez**: Lleva el proyecto de ser un simple visor a ser una herramienta de ingeniería estructural certificable para producción.

---

## 💡 Mensajes Clave para el Jurado (Elevator Pitch)
1. **"No asumimos que la estructura es estable: lo demostramos matemáticamente en cada barra instalada."**
2. **"Diseñado con el ADN de Geometrica:** precisión milimétrica, tubos HSS, paleta corporativa y foco en la seguridad de los instaladores."
3. **"100% web, 0 instalación:** corre en cualquier laptop de un ingeniero en obra o en las oficinas centrales."
