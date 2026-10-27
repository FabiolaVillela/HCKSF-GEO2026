# Verificación preliminar de miembros — ANSI/AISC 360-22, LRFD

## Estado y alcance

Esta implementación verifica resistencia de **miembros HSS circulares de acero** con demandas elásticas de primer orden. No es una comprobación integral AISC ni una aprobación de diseño: no se comprueban los requisitos de estabilidad del capítulo C, cortante/torsión y sus interacciones G/H3, conexiones J/K, soldaduras, bloque de cortante, fatiga, flechas admisibles ni estabilidad de montaje. El verde significa únicamente utilización ≤1 en las revisiones incluidas.

Se parte del commit remoto `081b8b650ad1b0481eac4a3db49a6a81dac9f301` y se incorpora antes de publicar el commit `e0526c09edcbaa40810bd50567aa01584d87f54e` (retira las marcas xfail de dos pruebas del solver ya implementado), posterior a la revisión inicial de `b25fe0f671403cac1689901727249855f7469a08`. Se conserva la interfaz bilingüe, los colores graduados de fuerzas, gráficas de progreso, importación DXF y CSV de apoyos. La rama es `feature/aisc-member-checks`; no se integra automáticamente a main.

## Criterios autorizados

- Demandas exclusivamente de peso propio: combinación **1.4D**, factor aplicado una sola vez en el postproceso. Esta combinación es un criterio de carga proporcionado para esta herramienta, no una combinación generada por AISC 360.
- Espesor de resistencia `t = 0.93 t_nominal`. Las propiedades de resistencia A, I, S, Z, r y D/t se calculan con ese espesor. Se conserva el peso y la rigidez nominal que ya usa el motor; no se vuelve a analizar con una sección más delgada.
- `Ky = Kz = 1`. Se adopta **L entre nodos del elemento en ambos planos** y `Lc = KL` para cada etapa. Esto no demuestra que los nodos sean arriostramientos efectivos: puede ser inadecuado en etapas incompletas o con traslación lateral.
- Sección sin perforaciones: `An=Ag`. Transferencia a toda la sección: `U=1`, confirmado expresamente por el usuario para esta revisión preliminar. `Ae,tension = U An = Ag`. No se verifica la conexión que permitiría dicha transferencia.
- Primer orden: sin P-Delta, P-delta, imperfecciones, cargas nocionales, reducción de rigideces ni análisis de pandeo global. Una utilización ≤1 no acredita los requisitos del capítulo C.
- No se incrementan momentos con factores B1/B2 ni se presenta el análisis como segundo orden.
- El módulo rechaza resultados que contienen carga de instalador distinta de cero. El simulador HTML ya no la incluye. El dashboard legado conserva ese control: para verificar una etapa con carga de instalador debe fijarse en cero, sin cambiar sus cálculos anteriores.

## Materiales

Se requiere seleccionar un grado; **no hay un grado predeterminado**. El catálogo de resistencias es independiente del catálogo elástico existente. Se conservan E=200 GPa para acero y E=69 GPa para aluminio, ν y densidad actuales del proyecto.

| Identificación | Fy (MPa) | Fu (MPa) | Uso |
|---|---:|---:|---|
| ASTM A500/A500M-21 Grado B | 315 | 400 | HSS circulares, resistencias mínimas SI |
| ASTM A500/A500M-21 Grado C | 345 | 425 | HSS circulares, resistencias mínimas SI |
| 6061-T4 extruido, Hydro 2019 | 110 | 180 | Solo identificación del material; AISC deshabilitado |
| 6061-T6 extruido, Hydro 2019 | 240 | 260 | Solo identificación del material; AISC deshabilitado |
| Personalizado | dato obligatorio | dato obligatorio | Requiere fuente/certificado, 0 < Fy ≤ Fu |

Se identifica **la edición 2021 de A500**, porque las resistencias de tubos redondos de ediciones anteriores pueden diferir. Se usan los valores mínimos SI publicados, no conversiones exactas de los valores redondeados en ksi. El catálogo no afirma la existencia/disponibilidad de un producto ni sustituye su certificado. Para el aluminio, aleación y temple corresponden a material extruido sin reducción por soldadura; requiere una norma de aluminio y un módulo de diseño independiente.

Fuentes del catálogo: [Steel Tube Institute, tabla A500 de 2022](https://steeltubeinstitute.org/wp-content/uploads/2022/08/STI_Webinar_Dos_and_Donts_HSS_1Slide.pdf), [STI, revisión de ASTM A500](https://steeltubeinstitute.org/resources/astm-a500/), [Hydro, Alloy 6061, 2019](https://www.hydro.com/globalassets/01-products--services/extruded-profiles/americas/ena-resources/alloy-data-sheets/hydro_2019_data_sheet_6061.pdf).

## Unidades y demandas

Internamente: longitud m, fuerzas N, momentos N·m, esfuerzos Pa. La interfaz convierte fuerzas a kN, momentos a kN·m, espesores a mm y resistencias a MPa.

`assembly.solve_stage` conserva por elemento `length_m`, `local_axes_rows`, acciones de extremos y estaciones `N_Vy_Vz_T_My_Mz`. N positivo es tensión. Los momentos My y Mz actúan sobre los ejes **locales** de cada miembro; el eje local x va de i a j. No se confunden con Rx/Ry/Rz de apoyos ni con componentes radiales. AISC suele denominar x/y a los dos ejes de flexión de la sección; en este motor corresponden a y/z.

En cada posición se utilizan N, My y Mz concurrentes del mismo miembro y de la misma etapa. Los valores originales del JSON, fuerzas gráficas, desplazamientos y reacciones no se mayoran ni se modifican. `forces` solo contiene axial central y **no** se usa como fuente única de la revisión.

## Propiedades geométricas, B4

Para diámetro exterior D e interior d=D-2t:

```
A = π(D²-d²)/4
Iy = Iz = I = π(D⁴-d⁴)/64
S = 2I/D
Z = (D³-d³)/6
ry = rz = sqrt(I/A)
λ = D/t
```

Referencias: B4.1 y tablas B4.1a/B4.1b (clasificación), B4.2 (espesor de diseño), B4.3 (áreas). El factor 0.93 corresponde aquí al alcance A500 y al criterio autorizado; no se aplica una regla genérica a un catálogo A1085/A1065 inexistente en este módulo.

## Tensión, D2

```
φt Pn,yield = 0.90 Fy Ag                   D2-1
φt Pn,rupture = 0.75 Fu Ae,tension         D2-2
Pt = min(φt Pn,yield, φt Pn,rupture)
Ae,tension = U An = Ag                    criterio U=1, sin perforaciones
```

Se reporta el estado límite que determina Pt. No se omite ruptura solo por no tener perforaciones.

## Compresión, E2, E3 y E7.2

```
Lc = KL = L
Fe = π² E / (Lc/r)²                       E3-4
Fn = 0.658^(Fy/Fe) Fy, si Fy/Fe ≤ 2.25     E3-2
Fn = 0.877 Fe, si Fy/Fe > 2.25             E3-3
Ae,c = Ag, si D/t ≤ 0.11 E/Fy              E7-6
Ae,c = min(Ag, [0.038 E/(Fy(D/t)) + 2/3]Ag) E7-7
Pc = 0.90 Fn Ae,c                         E3-1 / E7-1
```

E7-7 se utiliza solo para `0.11 E/Fy < D/t < 0.45 E/Fy`. No se extrapola para secciones más esbeltas. KL/r>200 genera una advertencia sobre el límite preferido de E2; no se oculta el resultado ni se convierte esa recomendación en una resistencia adicional. Para tubos circulares de este alcance se comprueba pandeo flexional en ambos planos con el mismo r y L; no hay un estado de pandeo lateral-torsional de flexión aplicable.

## Flexión, F1 y F8

```
Mp = Fy Z                                 F8-1
Compacta:     Mn = Mp, λ ≤ 0.07 E/Fy
No compacta:  Mn = min(Mp, [0.021 E/λ + Fy] S), λ ≤ 0.31 E/Fy   F8-2
Esbelta:      Mn = min(Mp, [0.33 E/λ] S)                        F8-3/F8-4
Mc = 0.90 Mn
```

F8 solo se aplica para `D/t < 0.45 E/Fy`. Incluye fluencia y pandeo local. El pandeo lateral-torsional no aplica a estos HSS circulares; por ello no se inventan Lb o Cb. Esto no elimina la necesidad de verificar estabilidad global.

## Interacción, H1.1 y H1.2

En cada posición, con las demandas multiplicadas por 1.4:

```
p = |Nu| / Pc     si Nu < 0 (compresión)
p = Nu / Pt       si Nu ≥ 0 (tensión)
m = |My,u|/Mc + |Mz,u|/Mc
H1-1a: H = p + (8/9)m       si p ≥ 0.2
H1-1b: H = p/2 + m          si p < 0.2
```

H1.2 remite también a H1-1a/b para flexotensión. No se sustituye por una única división de demanda entre resistencia ni por una suma lineal de tensión más flexión en todos los casos.

En el límite p=0.2 se incluye conservadoramente el límite lateral de las dos ramas de H1 si es mayor, identificado como `boundary envelope`, para evitar perder un máximo cuando las expresiones no coinciden.

Se usa conservadoramente la suma de los dos términos de flexión sobre los ejes locales fijos, sin rotar la sección circular hacia el momento resultante para reducir el cociente. La utilización de la posición es `max(p, m, H)`: las comprobaciones independientes evitan que una tensión o compresión pura pequeña se reporte erróneamente con la mitad de su cociente debido a H1-1b. Se informan la ecuación, el estado límite, la posición y las acciones concurrentes que gobiernan.

## Máximos dentro del miembro y entre etapas

El motor actual aplica peso uniforme y cargas nodales: las acciones a lo largo de cada barra son, como máximo, cuadráticas. Se reconstruyen polinomios usando tres estaciones del motor y **se verifica su coincidencia con todas las estaciones**. Se prueban extremos, estaciones originales, ceros de N/My/Mz, transiciones `p=0.2` y extremos de las expresiones cuadráticas en cada intervalo de signos. Así se identifican máximos entre las 11 estaciones originales, sin mezclar un N de un punto con un M de otro. Si las muestras no corresponden al modelo polinomial, el miembro se marca no disponible en lugar de inventar una distribución.

Por etapa se obtiene el máximo entre las barras instaladas de **esa etapa**. Las barras futuras no participan. Una etapa inestable no tiene utilización cero: su utilización es nula/no disponible. Si hay miembros fuera del alcance, el reporte indica `incomplete` y el máximo corresponde solo a los miembros evaluados. El historial no es una combinación de carga: conserva el resultado separado de cada etapa.

## Ejemplos manuales

### HSS 4 pulgadas × 1/8 pulgada, A500-21 C, L=2 m

```
D = 101.6 mm; t_nom = 3.175 mm; t = 2.95275 mm
Fy = 345 MPa; Fu = 425 MPa; E = 200000 MPa
Ag = 915.085205 mm²
I = 1,114,116.084 mm⁴
S = 21,931.419 mm³; Z = 28,742.618 mm³
r = 34.892690 mm; KL/r = 57.318596; D/t = 34.408602
Fe = 600.812086 MPa; Fn = 271.294043 MPa
Pt,yield = 284.133956 kN
Pt,rupture = 291.683409 kN
Pt = 284.133956 kN (D2-1)
Pc = 223.431449 kN (E3-2)
Mc = 8.924583 kN·m (compacta, F8-1)
```

### Interacción con demanda concurrente 1.4D

Si las acciones **sin mayorar** en una posición son N=-100 kN, My=2 kN·m, Mz=1 kN·m:

```
Nu=-140 kN; My,u=2.8 kN·m; Mz,u=1.4 kN·m
p=140/223.431449=0.62659
m=4.2/8.924583=0.47061
H=p+(8/9)m=1.04491 > 1        H1.1/H1-1a, flexocompresión
```

Para N=+10 kN, My=2 kN·m, Mz=1 kN·m:

```
p=14/284.133956=0.04927 < 0.2
H=p/2+m=0.49525                H1.2/H1-1b, flexotensión
```

Para tensión pura de +250 kN sin mayorar: Nu=350 kN y utilización=350/284.133956=1.23181, gobernada por D2-1. En todos los ejemplos las fuerzas originales permanecen sin modificar.

### Máximo entre estaciones

Para una demanda de flexión `My(x)=Mc/1.4 × [1.2-(x/L-0.37)²]`, sin axial, la utilización máxima es 1.2 en x/L=0.37. El algoritmo la encuentra aunque las muestras estén separadas en 0.1L. Es un caso sintético de prueba, no una carga añadida al producto.

## Arquitectura y uso

- `design_materials.py`: catálogo de resistencias y validación de grado/fuente.
- `aisc.py`: cálculo puro a partir de resultados, resistencias, extremos críticos y resumen por etapa.
- `design_dashboard.py`: controles opcionales del dashboard Streamlit.
- `static/aisc-view.js`: vista HTML opcional, solicitudes y caché por modelo/configuración/grado/etapa. Las preferencias de vista no alteran `config()` del análisis.
- `server.py`: GET `/api/design-materials`, POST `/api/aisc` y `/api/aisc/progress`; se conservan los endpoints originales.

Desde una copia de la rama:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m domestage.server --port 8506
# Abrir http://127.0.0.1:8506/
# Alternativa: streamlit run src/domestage/app.py
```

Selecciona material, **grado real del producto** y perfil. Activa la casilla AISC (apagada inicialmente). Selecciona una barra para consultar demanda mayorada, capacidades, ecuación y posición, junto a las fuerzas originales. Desactiva la casilla para recuperar los colores de fuerzas. “Verificar todas las etapas” calcula un historial independiente por etapa; “Exportar reporte AISC” descarga los parámetros, fuentes, limitaciones, resultados de las etapas revisadas y el resultado original de la etapa seleccionada. La geometría privada no se incluye en el repositorio.

```bash
python -m pytest -q tests prototypes/rigid-frame/tests
node --test tests/*.cjs
```

## Referencias normativas y técnicas

- American Institute of Steel Construction, **ANSI/AISC 360-22, Specification for Structural Steel Buildings**, August 1, 2022: B4, D2/D3, E2/E3/E7.2, F1/F8, H1.1/H1.2. [Publicación AISC](https://vpn2.modernsteel.com/publications/steel-standards/aisc-360/), [especificación AISC](https://vpn2.modernsteel.com/globalassets/product-files-not-searched/publications/standards/a360-22w.pdf). Las referencias de ecuaciones corresponden a la edición 2022; no a borradores posteriores.
- [STI, selección de miembros y aplicación de E7.2](https://steeltubeinstitute.org/hollow-structural-sections/hss-member-selection-tools/).
- Fuentes de resistencias de materiales enlazadas en la tabla del catálogo. No se distribuye el texto íntegro de la especificación.
