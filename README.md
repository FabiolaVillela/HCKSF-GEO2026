# DomeStage · análisis de montaje de domos

Simulador de estructuras 3D que incorpora barras por etapas y calcula fuerzas internas, reacciones y desplazamientos con el motor de armaduras o pórticos del proyecto.

## Simulador conectado al motor estructural

El visor de montaje ahora calcula el equilibrio de cada etapa usando las barras instaladas, su peso propio y una carga nodal de instalador. Para abrir el simulador con su servidor de cálculo, desde la raíz del repositorio:

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=src python3 -m domestage.server --port 8503
```

Abrir `http://127.0.0.1:8503`. `simulador.html` necesita ese servidor; abrirlo directamente como archivo o servirlo con un servidor estático no ejecuta el motor.

La interfaz Streamlit también usa el mismo adaptador:

```bash
python3 -m streamlit run src/domestage/app.py
```

### Qué se calcula en cada etapa

- Se conservan las barras inicialmente instaladas (etapa 0); las demás se ordenan por secuencia del modelo y se agrupan de 1 a 4 por etapa. Para DXF, se propone una secuencia por altura media; se debe revisar frente al plan real de montaje.
- Solo las barras activas aportan peso y rigidez. Los nodos que pertenecen exclusivamente a barras futuras se excluyen de la matriz.
- Conexiones articuladas: armadura espacial axial de 3 GDL/nodo, peso propio repartido entre extremos. Empotradas: pórtico espacial de 6 GDL/nodo, peso propio distribuido consistente.
- Un solo instalador y sus herramientas se aplican verticalmente en el nodo j de la última barra nueva. La carga se desplaza con la etapa, no se acumula ni se multiplica por las barras del grupo. Etapa 0 sin instalador.
- Los apoyos y sus restricciones se configuran por separado. Se proponen los nodos de cota mínima al importar y se pueden modificar.
- Las fuerzas axiales, reacciones, desplazamientos y momentos proceden del motor existente. Los colores axiales representan el centro de cada barra; los máximos consideran las estaciones muestreadas. Una etapa con mecanismo no muestra valores de fuerza ni reacciones ficticias.
- Cada cambio de geometría, material, perfil, conexión, apoyo, carga o agrupación invalida los resultados previos. La caché del motor usa el contenido completo de esos parámetros y la etapa.
- La reproducción espera cada cálculo y se detiene en una etapa sin solución. Se puede seguir inspeccionando manualmente las siguientes etapas. El historial contiene únicamente resultados calculados; las demás etapas figuran como pendientes.

### Componentes de integración

`src/domestage/assembly.py` adapta la geometría al motor existente en `prototypes/rigid-frame/domecalc`, mantiene los identificadores originales y entrega resultados de etapa. `server.py` sirve solo el simulador, su script y los endpoints de cálculo/importación en localhost. La interfaz HTML y Streamlit usan ese mismo adaptador. El contrato `schema.py` y las firmas de los módulos pendientes de otros integrantes se mantienen.

API local: `GET /api/catalog`, `GET /api/demo`, `POST /api/plan`, `POST /api/stage` (JSON) y `POST /api/import` (bytes DXF; `units` y `tolerance` en la URL). El resultado indica `status=stable`, `unstable`, `empty` o `error`; las fuerzas se reportan solo cuando se obtuvo equilibrio. El JSON de etapa incluye configuración, geometría, barras activas, cargas, axiales, reacciones y desplazamientos. Los IDs de claves del diccionario `forces` son cadenas JSON; los IDs en listas siguen siendo enteros.

### Límites físicos

Es un equilibrio elástico lineal independiente sobre la geometría de referencia de cada etapa. No simula activación de barras sobre una forma deformada, deformaciones o tensiones residuales acumuladas, pandeo, resistencia, segundo orden, grúas ni apuntalamientos. “Equilibrio calculado” no constituye una comprobación de capacidad ni de seguridad del montaje. En armadura axial no se calcula flexión local de barras por su propio peso; las rotaciones exportadas son ceros de compatibilidad, no giros calculados.

La importación valida conectividad, duplicados, longitudes nulas y unidades; no divide cruces interiores ni convierte curvas en barras. Sigue limitada a 500 nodos, 5000 barras y archivos de hasta 20 MB. Material y perfil son uniformes y nominales.

### Validación

```bash
python3 -m pytest tests prototypes/rigid-frame/tests -q
```

Se añaden verificaciones de etapas agrupadas, exclusión de nodos futuros, mecanismos intermedios y recuperación al completar un trípode, equilibrio de reacciones, carga única del instalador frente a solución manual, coincidencia de la etapa final con el solver directo, invalidación por cambios de geometría/material/apoyos y navegación del dashboard. El solver original `solve_truss` del equipo sigue pendiente y conserva sus dos pruebas xfail; el simulador de montaje utiliza el motor implementado en el prototipo a través del adaptador.

## Colaboración

Consulta `CONTRIBUTING.md` para el reparto de módulos y el contrato de datos. Trabaja en una rama y abre un pull request; las firmas compartidas y `schema.py` requieren coordinación con el equipo.
