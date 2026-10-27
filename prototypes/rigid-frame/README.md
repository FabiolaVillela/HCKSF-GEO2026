# Calculadora de pórticos 3D

Motor independiente en Python para integrarlo desde otro archivo o interfaz. Requiere Python 3.10+, NumPy y, para el nuevo flujo de importación e interfaz, ezdxf y Streamlit (`python3 -m pip install -r requirements.txt`).

## Ejecución

```bash
python3 -m domecalc /ruta/modelo.dxf --output resultados
python3 -m unittest discover -s tests -v
```

## Integración

```python
from domecalc import Material, Section, read_dxf, analyze, export

model = read_dxf('/ruta/modelo.dxf', tolerance=1e-6)
model.pin_base()  # Restringe ux, uy, uz en todos los nodos a la cota mínima.
result = analyze(model, Material(), Section.circular(.1016, .003175))
export(result, 'resultados')
```

También se puede construir `Model(nodes, elements, supports)` sin DXF. Coordenadas en metros; elementos `(i, j, capa)`; numeración desde cero. `supports` es un diccionario `{nodo: (GDL, ...)}`, con GDL 0..5 = ux,uy,uz,rx,ry,rz. Todos los movimientos prescritos son cero. `analyze` acepta `nodal_loads={nodo: [Fx,Fy,Fz,Mx,My,Mz]}`, `gravity=(0,0,-9.80665)` y `stations=11`. Los apoyos se pueden cambiar sin modificar el motor; las liberaciones entre barras aún no están implementadas.

## Modelo inicial y alcance

- Acero: E=200 GPa, nu=0.30, densidad=7850 kg/m³.
- Tubo circular: diámetro exterior 101.6 mm, espesor geométrico 3.175 mm. Sin reducción de espesor de diseño, corrosión ni propiedades de catálogo.
- Elementos Euler–Bernoulli rectos, prismáticos, 12 GDL, uniones rígidas, pequeñas deformaciones, elasticidad lineal. No considera deformación por cortante.
- Peso propio uniforme por longitud real de cada barra, convertido en cargas nodales consistentes que incluyen momentos. Sin peso de conexiones, cubierta ni accesorios.
- Los 32 nodos inferiores del DXF de ejemplo están articulados en las tres traslaciones; las rotaciones permanecen libres.
- No comprueba resistencia, soldaduras, estabilidad geométrica, pandeo, plasticidad, vibración ni cumplimiento normativo. Requiere validación independiente antes de emplearse para diseño.

## Importación con el lector inicial

Solo DXF ASCII con entidades LINE en ENTITIES. Rechaza otros tipos en lugar de omitirlos silenciosamente. Lee INSUNITS (pulgadas, pies, mm, cm, m); `--scale` permite especificar metros por unidad. No transforma bloques ni divide cruces interiores. Une extremos por distancia euclidiana dentro de 1e-6 m por defecto, tomando como representante el primero leído. Rechaza barras duplicadas y nulas. Las capas se conservan como grupos; esta versión aplica una única sección y material a todas las barras.

## Resultados y signos

`results.json` contiene nodos, restricciones, desplazamientos, reacciones, barras, ejes locales, acciones de extremo y fuerzas en 11 estaciones por barra. `nodes.csv` y `forces.csv` permiten usar los datos en hojas de cálculo. `report.md` contiene el resumen. SI: m, N, N·m, rad.

Eje x local: i → j. Se elige una referencia Z global (Y si la barra es casi vertical), y = referencia × x normalizado; z = x × y. La matriz `local_axes_rows` transforma vectores globales a locales. No reproduce necesariamente los ejes automáticos de otros programas.

`end_actions_local` contiene las acciones nodales sobre el elemento, ordenadas `[Fx,Fy,Fz,Mx,My,Mz]` en i y j. No confundirlas con fuerzas de sección. `N_Vy_Vz_T_My_Mz` contiene acciones sobre la cara positiva x del corte: N positivo es tracción. Con carga distribuida local w y distancia s, F(s)=-f_i-w*s; M(s)=-m_i+(s,0,0)×f_i+(s²/2,0,0)×w. Las estaciones son muestras, no una búsqueda de máximos exactos.

Como referencia conceptual para interpretar componentes: [convención de fuerzas internas de CSI](https://docs.csiamerica.com/help-files/sap/Output/Frame_Element_Internal_Forces_Output_Conventions.htm). Las convenciones específicas de esta calculadora son las descritas arriba.

## Validación realizada

Pruebas analíticas de voladizo bajo peso propio en cuatro orientaciones, viga biempotrada con carga distribuida, carga axial, torsión y rechazo de un modelo sin apoyos. El domo se ejecutó con 149 nodos y 412 barras. El reporte registra el equilibrio global de fuerzas y momentos, y el condicionamiento de la matriz escalada; un mecanismo o matriz excesivamente mal condicionada detiene el análisis.

## Uso dentro de HCKSF-GEO2026

Este aporte está aislado en `prototypes/rigid-frame/`. Añade un modelo de pórtico con 6 GDL por nodo. El contrato `src/domestage/schema.py` y el solver de armaduras de 3 GDL del equipo permanecen independientes. No implementa etapas de construcción ni reemplaza `solve_truss`. La detección de mecanismos aquí lanza `ValueError`; para integrarlo al flujo del equipo se necesitará un adaptador que devuelva `stable=False` y una decisión conjunta sobre el contrato de rotaciones y momentos.

Desde la raíz del repositorio:

```bash
cd prototypes/rigid-frame
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 demo.py
```

Abrir `output/demo/visor.html` con Chrome, Firefox, Safari o Edge. Es un archivo autocontenido que funciona sin servidor y sin instalar Codex. El ejemplo es una geometría sintética de 49 nodos y 128 barras; no se incluyen DXF ni datos del domo original.

Para tu DXF:

```bash
python3 -m domecalc /ruta/modelo.dxf --output output/mi-domo --viewer
```

El visor se genera de los resultados de cada ejecución. Permite giro libre arrastrando, zoom con rueda/pellizco/control, desplazamiento con Mayús + arrastre y selección con clic o lista accesible. Al seleccionar una barra muestra axial en i, centro y j en kN. Al seleccionar un apoyo muestra reacciones globales en kN y momentos en kN·m. Las reacciones son del nodo de apoyo, no de una barra individual. Las flechas de reacción comparten escala visual; las longitudes geométricas están en metros.

Para integrarlo desde Python:

```python
from domecalc.viewer import export_viewer
export_viewer(result, 'output/visor.html')
```

`domecalc/viewer-template.html` es la plantilla autónoma que consume el exportador; `viewer-fragment.html` conserva la fuente editable del visor. El archivo autónomo incluye sus estilos, controles y almacenamiento local de la vista. Al cambiar la fuente del visor hay que sincronizar también su plantilla autónoma. El visor ahora calcula el centro y escala iniciales a partir de los límites de cada geometría.

Para colaborar, sigue `../../CONTRIBUTING.md`: ramas propias, pull requests hacia `main` y coordinación antes de cambiar módulos del equipo. Las mejoras de este prototipo pueden hacerse dentro de esta carpeta. No se asigna una licencia al código del repositorio; esa decisión corresponde al equipo.

## Nuevo flujo: importar, configurar y analizar

```bash
cd prototypes/rigid-frame
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Abre la dirección local que muestra Streamlit. El archivo seleccionado se procesa en el servidor donde ejecutes la aplicación; una ejecución local no envía el DXF a GitHub. El flujo es:

1. Subir un DXF, confirmar sus unidades y elegir tolerancia de unión de extremos. Opcionalmente filtrar por capas.
2. Revisar nodos, barras, componentes conectados, extremos libres, duplicados y barras nulas. Los errores bloquean el análisis; el diagnóstico puede descargarse como JSON.
3. Elegir acero o aluminio, uno de siete tubos circulares HSS del catálogo y conexiones articuladas o empotradas entre todas las barras.
4. Confirmar los nodos de apoyo —se proponen los de cota mínima— y definir apoyos articulados o empotrados por separado.
5. Ejecutar el análisis y consultar el visor; descargar HTML o ZIP con reporte, JSON y CSV. Cambiar el DXF o la configuración invalida la vista de los resultados previos.

**Compatibilidad DXF del nuevo flujo:** ASCII y binario leídos por ezdxf; LINE, POLYLINE 2D/3D y LWPOLYLINE con segmentos rectos; bloques INSERT con sus transformaciones y repeticiones. Solo se analiza el espacio modelo. Las anotaciones se omiten y registran. Arcos, círculos, splines, superficies, mallas y referencias externas no se convierten automáticamente en barras: el diagnóstico pide convertirlas en CAD o excluir sus capas. Un archivo DXF arbitrario puede revisarse, pero no toda entidad CAD representa un elemento estructural recto. El lector antiguo `read_dxf` y el CLI conservan su alcance LINE; este flujo usa `domecalc.importer.inspect_dxf`.

Las uniones se determinan por extremos a distancia menor o igual a la tolerancia en metros, usando coordenadas de un extremo representante. No se subdividen cruces ni se unen automáticamente extremos con el interior de otra barra. La continuidad geométrica no garantiza estabilidad: se comprueba después con la rigidez del modelo. Se bloquean los componentes desconectados para evitar analizar accidentalmente dibujos ajenos a la estructura; deben corregirse o filtrarse en CAD.

**Materiales nominales:** acero E=200 GPa, ν=0.30, ρ=7850 kg/m³; aluminio E=69 GPa, ν=0.33, ρ=2700 kg/m³. Son aproximaciones elásticas, no una selección de grado, aleación o temple ni una verificación de resistencia. Como referencia de los órdenes de magnitud de E y densidad: [MIT, tabla 9.1](https://ocw.mit.edu/ans7870/resources/woodson/textbook/emd_part3.pdf). El catálogo usa dimensiones nominales geométricas, sin tolerancias ni reducción de espesor, y no acredita disponibilidad comercial para cada material.

**Modelos de conexión:** empotradas usa el pórtico Euler–Bernoulli existente y peso propio distribuido consistente. Articuladas usa una armadura espacial con 3 GDL/nodo, axial únicamente y peso propio repartido a nodos. En esta idealización axial los momentos, torsión y cortantes son cero; no se verifica flexión local por peso propio entre nodos. Las rotaciones del resultado se rellenan con cero para compatibilidad del exportador, no son giros calculados. `workflow.run_analysis` devuelve `stable=False` y un mensaje ante mecanismos. Las uniones rígidas de las barras y las restricciones de apoyo son decisiones independientes.

Esta interfaz admite archivos de hasta 20 MB y análisis de hasta 500 nodos porque los motores actuales usan matrices densas. No es una limitación del formato DXF. El visor encuadra automáticamente los límites de la geometría importada y muestra material, perfil, conexiones y tipo de apoyo seleccionados.

Referencias de implementación: [ezdxf, lectura de archivos](https://ezdxf.readthedocs.io/en/stable/usage_for_beginners.html), [polilíneas y segmentos curvos](https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html), [Streamlit, carga de archivos](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader).

Pruebas del nuevo flujo:

```bash
python3 -m unittest discover -s tests -v
# Opcional para pruebas de interfaz:
python3 -m pip install pytest
python3 -m pytest tests -q
```

La interfaz ofrece `examples/demo-dome.dxf` para probar la importación con una geometría sintética. El DXF original del usuario sigue fuera del repositorio.

Validación del nuevo aporte: 19 pruebas del prototipo aprobadas, incluidas las pruebas del flujo de interfaz con AppTest. Con las pruebas originales del repositorio: 21 aprobadas y 2 xfail esperados del solver de armaduras aún pendiente. Se verificó también en Chrome la carga del ejemplo, elección de aluminio, análisis articulado, consulta de axial y descarga de resultados; el DXF original conserva 149 nodos y 412 barras y se resolvió con las cuatro combinaciones de material y conexión.
