"""Utilization figures by assembly progress, for the calculation report ("memoria de cálculo").

For each requested % of progress (default 50, 67, 83, 95, 100) the first stage that reaches it is
solved and checked with `aisc.check_result` (preliminary ANSI/AISC 360-22 LRFD, 1.4D). Two views
are drawn as SVG — plan (top) and elevation (side) — with only the installed bars, coloured with
the usual utilization key (cyan → blue → black up to 1.0, yellow → orange → red above 1.0), and the
supports marked. `figures_html` wraps everything in a self-contained HTML document (summary,
conclusion, table, figures with PNG/SVG download buttons) in English or Spanish.
"""
from __future__ import annotations

from html import escape
import math

from .aisc import BASIS, check_result
from .assembly import solve_stage, stage_plan, validate_geometry
from .design_materials import design_material

DEFAULT_MILESTONES = (50, 67, 83, 95, 100)
LANGUAGES = ('en', 'es')

# Same absolute scale as the simulator's AISC view (aisc-view.js, PR #25): a continuous ramp up to 1.0
# and a deliberate break above 1.0 so that any exceedance stands out.
UTILIZATION_STOPS = [(0.0, '#00ffff'), (0.5, '#00aaff'), (0.75, '#0000ff'), (1.0, '#000000')]
EXCEEDANCE_STOPS = [(1.0, '#ffff00'), (1.1, '#ff9900'), (1.25, '#ff0000')]
UNCHECKED = '#737373'
# Key swatches (value, label) drawn like the usual "Utilization / Key" legend.
KEY = [(0.0, '0.0'), (0.25, ''), (0.5, ''), (0.75, '0.75'), (0.875, ''), (1.0, '1.0'),
       (1.0 + 1e-9, '1.0+'), (1.05, ''), (1.1, '1.1'), (1.175, ''), (1.25, '1.25')]

TEXT = {
    'doc_title': {'en': 'Structure utilization by assembly progress', 'es': 'Utilización de la estructura por avance de armado'},
    'figure_title': {'en': 'Dome assembly {pct}%', 'es': 'Armado Domo {pct}%'},
    'plan': {'en': 'Plan', 'es': 'Planta'},
    'elevation': {'en': 'Elevation', 'es': 'Elevación'},
    'key_title': {'en': 'Utilization', 'es': 'Utilización'},
    'key': {'en': 'Key', 'es': 'Clave'},
    'unchecked': {'en': 'not checked', 'es': 'sin revisar'},
    'supports': {'en': 'supports', 'es': 'apoyos'},
    'no_solution': {'en': 'No equilibrium at this stage (mechanism): utilization not available.',
                    'es': 'Sin equilibrio en esta etapa (mecanismo): utilización no disponible.'},
    'model': {'en': 'Model', 'es': 'Modelo'},
    'material': {'en': 'Material grade', 'es': 'Grado de material'},
    'profile': {'en': 'Profile', 'es': 'Perfil'},
    'connections': {'en': 'Connections / supports', 'es': 'Conexiones / apoyos'},
    'bars_per_stage': {'en': 'Bars per stage', 'es': 'Barras por etapa'},
    'basis': {'en': 'Design basis', 'es': 'Bases de diseño'},
    'basis_text': {'en': 'ANSI/AISC 360-22 LRFD · 1.4D (self-weight of installed bars) · t = 0.93 t nominal · K = 1 · L = node-to-node · An = Ag · U = 1 · first-order, independent stage',
                   'es': 'ANSI/AISC 360-22 LRFD · 1.4D (peso propio de las barras instaladas) · t = 0.93 t nominal · K = 1 · L = entre nodos · An = Ag · U = 1 · primer orden, etapa independiente'},
    'table': {'en': ['Progress (%)', 'Stage', 'Installed bars', 'Max utilization', 'Governing bar', 'Governing check', 'Status'],
              'es': ['Avance (%)', 'Etapa', 'Barras instaladas', 'Utilización máx.', 'Barra que rige', 'Revisión que rige', 'Estado']},
    'status_ok': {'en': 'All ≤ 1.0', 'es': 'Todas ≤ 1.0'},
    'status_exceeds': {'en': 'Exceeds 1.0', 'es': 'Excede 1.0'},
    'status_none': {'en': 'No solution', 'es': 'Sin solución'},
    'conclusion_ok': {'en': 'For the self-weight of the installed bars (1.4D), the preliminary AISC 360-22 utilizations of all bars — ratio between required strength and design strength — are lower than 1.0 at every assembly progress shown (maximum {umax}).',
                      'es': 'Para el peso propio de las barras instaladas (1.4D), las utilizaciones preliminares AISC 360-22 de todas las barras, relación entre la resistencia requerida y la resistencia de diseño, son menores a 1.0 en todos los avances mostrados (máxima {umax}).'},
    'conclusion_exceeds': {'en': 'At {pcts}% progress some bars exceed a utilization of 1.0 (maximum {umax}); they must be reviewed.',
                           'es': 'En los avances de {pcts}% algunas barras exceden una utilización de 1.0 (máxima {umax}); deben revisarse.'},
    'conclusion_unsolved': {'en': 'At {pcts}% progress the stage has no equilibrium (mechanism), so it is not verified.',
                            'es': 'En los avances de {pcts}% la etapa no tiene equilibrio (mecanismo), por lo que no se verifica.'},
    'scope': {'en': 'Preliminary member checks only (axial, flexure and H1 interaction). Shear, torsion, connections and Chapter C stability are not checked. Not a design approval.',
              'es': 'Solo revisiones preliminares de elementos (axial, flexión e interacción H1). No se revisan cortante, torsión, conexiones ni la estabilidad del capítulo C. No es una aprobación de diseño.'},
    'download_png': {'en': 'Download PNG', 'es': 'Descargar PNG'},
    'download_svg': {'en': 'Download SVG', 'es': 'Descargar SVG'},
    'connection': {'empotrada': {'en': 'rigid', 'es': 'empotradas'}, 'articulada': {'en': 'pinned', 'es': 'articuladas'}},
    'support': {'empotrado': {'en': 'fixed', 'es': 'empotrados'}, 'articulado': {'en': 'pinned', 'es': 'articulados'}},
    'need_grade': {'en': 'Select a steel material grade to build the utilization figures.',
                   'es': 'Selecciona un grado de material de acero para generar las figuras de utilización.'},
    'need_no_installer': {'en': 'Utilization figures need the installer load set to 0 (1.4D, dead load only).',
                          'es': 'Las figuras de utilización requieren la carga del instalador en 0 (1.4D, solo carga muerta).'},
    'bad_milestones': {'en': 'Progress milestones must be 1 to 12 numbers between 0 and 100.',
                       'es': 'Los avances deben ser de 1 a 12 números entre 0 y 100.'},
}


def utilization_color(u):
    """Hex colour for a utilization ratio; identical to utilizationColor() in aisc-view.js."""
    if u is None or not math.isfinite(u) or u < 0:
        return UNCHECKED
    stops = UTILIZATION_STOPS if u <= 1 else EXCEEDANCE_STOPS
    if u >= stops[-1][0]:
        return stops[-1][1]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if u <= b:
            t = (u - a) / (b - a)
            # floor(x + 0.5) reproduces JavaScript's Math.round (Python's round() rounds half to even).
            return '#' + ''.join(f'{math.floor(int(ca[k:k + 2], 16) * (1 - t) + int(cb[k:k + 2], 16) * t + 0.5):02x}'
                                 for k in (1, 3, 5))
    return stops[0][1]


def _parse_milestones(milestones, language):
    values = DEFAULT_MILESTONES if milestones in (None, '', []) else milestones
    if isinstance(values, str):
        values = [v for v in values.replace(';', ',').split(',') if v.strip()]
    try:
        values = sorted({float(v) for v in values})
    except (TypeError, ValueError):
        raise ValueError(TEXT['bad_milestones'][language]) from None
    if not 1 <= len(values) <= 12 or any(not 0 < v <= 100 for v in values):
        raise ValueError(TEXT['bad_milestones'][language])
    return values


def build_figures(geometry, config=None, design=None, milestones=None, language='en'):
    """Data for each milestone: stage, utilization per bar, maxima. Raises ValueError on bad input."""
    if language not in LANGUAGES:
        raise ValueError(f'Language must be one of {LANGUAGES}.')
    config, design = dict(config or {}), dict(design or {})
    if config.get('material', 'Acero') != 'Acero' or not design.get('grade'):
        raise ValueError(TEXT['need_grade'][language])
    if config.get('worker_kg', 0):
        raise ValueError(TEXT['need_no_installer'][language])
    grade = design_material('Acero', design)
    nodes, bars, supports = validate_geometry(geometry)
    plan = stage_plan(geometry, config.get('bars_per_step', 2))
    targets = _parse_milestones(milestones, language)
    figures, seen = [], set()
    for target in targets:
        info = next((s for s in plan if s['progress_pct'] >= target - 1e-9), plan[-1])
        if info['stage'] in seen:
            continue
        seen.add(info['stage'])
        result = solve_stage(geometry, config, info['stage'])
        utilization, max_u, governing = {}, None, None
        if result['status'] == 'stable':
            checked = check_result(result, design)
            utilization = {m['id']: m['utilization'] for m in checked['members']}
            max_u, governing = checked['max_utilization'], checked.get('governing')
        figures.append(dict(target_pct=target, stage=info['stage'], progress_pct=info['progress_pct'],
                            active_bar_ids=list(info['active_bar_ids']), status=result['status'],
                            utilization=utilization, max_utilization=max_u, governing=governing))
    return dict(nodes=nodes, bars={b['id']: b for b in bars}, supports=supports, figures=figures,
                grade=grade, config=config, language=language)


def _view_svg(data, figure, view, language):
    """One panel (plan or elevation) as an SVG string."""
    W, H, pad, key_w = 560, 440, 24, 92
    nodes, bars = data['nodes'], data['bars']
    pick = (lambda p: (p[0], p[1])) if view == 'plan' else (lambda p: (p[0], p[2]))
    pts = [pick(p) for p in nodes.values()]  # fit the whole model so every stage uses the same frame
    xmin, xmax = min(p[0] for p in pts), max(p[0] for p in pts)
    ymin, ymax = min(p[1] for p in pts), max(p[1] for p in pts)
    scale = min((W - key_w - 2 * pad) / max(xmax - xmin, 1e-9), (H - 2 * pad - 24) / max(ymax - ymin, 1e-9))
    ox = pad + ((W - key_w - 2 * pad) - (xmax - xmin) * scale) / 2
    oy = H - pad - ((H - 2 * pad - 24) - (ymax - ymin) * scale) / 2

    def xy(nid):
        x, y = pick(nodes[nid])
        return ox + (x - xmin) * scale, oy - (y - ymin) * scale

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="Arial, Helvetica, sans-serif">',
           f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="#FFFFFF" stroke="#9CA3AF"/>',
           f'<text x="{pad}" y="{pad + 4}" font-size="13" font-weight="700" fill="#0B2265">{escape(TEXT[view][language])}</text>']
    if figure['status'] != 'stable':
        out.append(f'<text x="{(W - key_w) / 2}" y="{H / 2}" font-size="12" text-anchor="middle" fill="#B91C1C">'
                   f'{escape(TEXT["no_solution"][language])}</text>')
    active = [bars[b] for b in figure['active_bar_ids']]
    if view == 'elevation':  # draw far bars first so near ones stay on top
        active.sort(key=lambda b: -(nodes[b['i']][1] + nodes[b['j']][1]))
    for b in active:
        (x1, y1), (x2, y2) = xy(b['i']), xy(b['j'])
        u = figure['utilization'].get(b['id'])
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{utilization_color(u)}" '
                   f'stroke-width="1.7" stroke-linecap="round"><title>#{b["id"]} U={u if u is None else round(u, 3)}</title></line>')
    installed = {n for b in active for n in (b['i'], b['j'])}
    for nid in data['supports']:
        if nid in installed:
            x, y = xy(nid)
            out.append(f'<rect x="{x - 3:.1f}" y="{y - 3:.1f}" width="6" height="6" fill="#6B7280"/>')
    # key, top right
    kx, ky = W - key_w + 6, pad - 6
    out.append(f'<text x="{kx}" y="{ky + 8}" font-size="10" font-weight="700">{escape(TEXT["key_title"][language])}</text>')
    sw, sh = 26, 13
    for i, (value, label) in enumerate(KEY):
        gap = 4 if value > 1 else 0  # small gap marks the break above 1.0, as in the reference key
        out.append(f'<rect x="{kx + 50}" y="{ky + 16 + i * sh + gap}" width="{sw}" height="{sh}" fill="{utilization_color(value)}"/>')
        if label:
            out.append(f'<text x="{kx + 44}" y="{ky + 16 + i * sh + gap + 10}" font-size="9" text-anchor="end">{label}</text>')
    gy = ky + 16 + len(KEY) * sh + 12
    out.append(f'<rect x="{kx + 50}" y="{gy}" width="{sw}" height="{sh}" fill="{UNCHECKED}"/>'
               f'<text x="{kx + 44}" y="{gy + 10}" font-size="9" text-anchor="end">{escape(TEXT["unchecked"][language])}</text>')
    out.append(f'<rect x="{kx + 59}" y="{gy + sh + 9}" width="7" height="7" fill="#6B7280"/>'
               f'<text x="{kx + 44}" y="{gy + sh + 16}" font-size="9" text-anchor="end">{escape(TEXT["supports"][language])}</text>')
    out.append('</svg>')
    return ''.join(out)


def _fmt(v, n=3):
    return '—' if v is None else f'{v:.{n}f}'


def figures_html(data, model_name=''):
    """Self-contained HTML document with the summary, conclusion, table and figures."""
    lang, cfg, g = data['language'], data['config'], data['grade']
    t = lambda key: TEXT[key][lang]
    figs = data['figures']
    pct = lambda f: f'{f["progress_pct"]:g}'
    exceeding = [f for f in figs if f['max_utilization'] is not None and f['max_utilization'] > 1]
    unsolved = [f for f in figs if f['status'] != 'stable']
    solved = [f['max_utilization'] for f in figs if f['max_utilization'] is not None]
    umax = _fmt(max(solved)) if solved else '—'
    conclusion = []
    if exceeding:
        conclusion.append(t('conclusion_exceeds').format(pcts=', '.join(pct(f) for f in exceeding), umax=umax))
    elif solved:
        conclusion.append(t('conclusion_ok').format(umax=umax))
    if unsolved:
        conclusion.append(t('conclusion_unsolved').format(pcts=', '.join(pct(f) for f in unsolved)))
    grade_label = g['label'] if lang == 'en' else g['label'].replace(' Grade ', ' Grado ')
    rows = []
    for f in figs:
        gov = f['governing'] or {}
        status = t('status_none') if f['status'] != 'stable' else (t('status_exceeds') if (f['max_utilization'] or 0) > 1 else t('status_ok'))
        rows.append('<tr>' + ''.join(f'<td>{escape(str(v))}</td>' for v in (
            pct(f), f['stage'], len(f['active_bar_ids']), _fmt(f['max_utilization']),
            gov.get('member_id', '—'), gov.get('equation', '—'), status)) + '</tr>')
    sections = []
    for n, f in enumerate(figs):
        title = t('figure_title').format(pct=f'{f["target_pct"]:g}')
        sections.append(
            f'<section class="fig"><h2>{escape(title)}</h2><div class="panels">'
            f'<figure id="f{n}p">{_view_svg(data, f, "plan", lang)}</figure>'
            f'<figure id="f{n}e">{_view_svg(data, f, "elevation", lang)}</figure></div>'
            f'<p class="meta">{escape(TEXT["table"][lang][1])} {f["stage"]} · {pct(f)}% · {len(f["active_bar_ids"])} {escape(TEXT["table"][lang][2].lower())} · '
            f'{escape(TEXT["table"][lang][3])}: {_fmt(f["max_utilization"])}</p>'
            f'<p class="dl"><button data-fig="f{n}" data-name="{escape(title)}" data-kind="png">{t("download_png")}</button> '
            f'<button data-fig="f{n}" data-name="{escape(title)}" data-kind="svg">{t("download_svg")}</button></p></section>')
    conn = TEXT['connection'].get(cfg.get('connection', 'empotrada'), {}).get(lang, cfg.get('connection'))
    sup = TEXT['support'].get(cfg.get('support', 'empotrado'), {}).get(lang, cfg.get('support'))
    summary = ''.join(f'<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>' for k, v in (
        (t('model'), model_name or '—'), (t('material'), f'{grade_label} (Fy = {g["Fy_MPa"]:g} MPa, Fu = {g["Fu_MPa"]:g} MPa)'),
        (t('profile'), cfg.get('profile', '—')), (t('connections'), f'{conn} / {sup}'),
        (t('bars_per_stage'), cfg.get('bars_per_step', 2)), (t('basis'), t('basis_text'))))
    script = """
document.querySelectorAll('button[data-fig]').forEach(btn=>btn.addEventListener('click',()=>{
  const svgs=[...document.querySelectorAll('#'+btn.dataset.fig+'p svg, #'+btn.dataset.fig+'e svg')];
  const w=svgs.reduce((s,v)=>s+v.viewBox.baseVal.width,0)+10,h=Math.max(...svgs.map(v=>v.viewBox.baseVal.height));
  let x=0,inner='';for(const v of svgs){inner+='<g transform="translate('+x+',0)">'+v.innerHTML+'</g>';x+=v.viewBox.baseVal.width+10;}
  const svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+w+' '+h+'" width="'+w+'" height="'+h+'" font-family="Arial, Helvetica, sans-serif"><rect width="100%" height="100%" fill="#fff"/>'+inner+'</svg>';
  const name=btn.dataset.name.replace(/[^\\w%-]+/g,'_');
  const save=(blob,ext)=>{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name+'.'+ext;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
  if(btn.dataset.kind==='svg'){save(new Blob([svg],{type:'image/svg+xml'}),'svg');return;}
  const img=new Image(),k=2;img.onload=()=>{const c=document.createElement('canvas');c.width=w*k;c.height=h*k;const g=c.getContext('2d');g.scale(k,k);g.drawImage(img,0,0);c.toBlob(b=>save(b,'png'),'image/png');};
  img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}));"""
    return (f'<!DOCTYPE html><html lang="{lang}"><head><meta charset="utf-8"><title>{escape(t("doc_title"))}</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1"><style>'
            'body{font-family:Arial,Helvetica,sans-serif;color:#111;max-width:1200px;margin:24px auto;padding:0 16px}'
            'h1{font-weight:400;font-size:28px;margin:0 0 12px}h2{font-weight:400;font-size:24px;margin:28px 0 10px}'
            'table{border-collapse:collapse;margin:10px 0;font-size:13px}th,td{border:1px solid #D1D5DB;padding:5px 8px;text-align:left}'
            'th{background:#F3F4F6}.panels{display:flex;flex-wrap:wrap;gap:10px}figure{margin:0}.meta{font-size:12px;color:#4B5563}'
            '.scope{font-size:12px;color:#6B7280}.dl button{font-size:12px;padding:4px 10px;cursor:pointer}'
            '@media print{.dl{display:none}.fig{break-inside:avoid}}</style></head><body>'
            f'<h1>{escape(t("doc_title"))}</h1><table>{summary}</table>'
            + ''.join(f'<p>{escape(c)}</p>' for c in conclusion)
            + f'<p class="scope">{escape(t("scope"))}</p>'
            f'<table><tr>{"".join(f"<th>{escape(h)}</th>" for h in TEXT["table"][lang])}</tr>{"".join(rows)}</table>'
            + ''.join(sections) + f'<script>{script}</script></body></html>')
