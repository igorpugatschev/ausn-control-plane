"""Рендер system.html: офлайн-просмотрщик с проекциями и drill-down в код-части."""

from __future__ import annotations

import json

HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
 body {{ margin: 0; font: 14px/1.4 Calibri, Arial, sans-serif; background: #f4f6fa; color: #001030; }}
 header {{ padding: 10px 18px; background: #001030; color: #fff; }}
 header b {{ font-size: 15px; }}
 header label {{ margin-left: 18px; font-size: 13px; color: #c9d6ec; }}
 button {{ margin-left: 12px; font: inherit; font-size: 13px; padding: 2px 10px; cursor: pointer;
           border: 1px solid #9fc0ff; background: #e4eeff; color: #0047b3; border-radius: 6px; }}
 button[hidden] {{ display: none; }}
 #legend {{ padding: 6px 18px; background: #e4eeff; color: #0047b3; font-size: 12px; }}
 #chart {{ width: 100vw; height: calc(100vh - 78px); }}
</style></head>
<body>
<header><b id="title-line">{title}</b> · сервисов {services} · связей {edges}
  <label><input type="radio" name="mode" value="services" checked> Сервисы</label>
  <label><input type="radio" name="mode" value="containers"> Контейнеры</label>
  <button id="back" hidden>← Назад к сервисам</button>
</header>
<div id="legend">сплошная линия — подтверждённая связь · пунктир — неразрешённая ·
  клик по сервису открывает его код-уровень (если части собраны: <code>--parts</code>)</div>
<div id="chart"></div>
<script src="{vendor}"></script>
<script src="{parts_rel}/index.js" onerror="window.__PARTS_LOAD_FAILED=true"></script>
<script id="graph-data" type="application/json">{data}</script>
<script>
const doc = JSON.parse(document.getElementById('graph-data').textContent);
const PARTS_REL = {parts_rel_literal};
const partsIndex = (window.SYSTEM_PARTS_INDEX || {{ services: {{}} }}).services || {{}};

function serviceNodes() {{
  return doc.nodes.map(n => ({{ data: {{ id: n.id, label: n.title, kind: n.kind, info: n.role || n.note || '' }} }}));
}}
function containerNodes() {{
  const nodes = serviceNodes(), edges = [];
  doc.nodes.forEach(n => {{
    (n.deploy || []).forEach(d => {{
      const cid = n.id + '::' + d.container + ':' + d.port;
      nodes.push({{ data: {{ id: cid, label: d.container + ' :' + d.port, kind: 'container',
        info: 'деплой-единица ' + n.title }} }});
      edges.push({{ data: {{ id: cid, source: n.id, target: cid, label: 'deploy', type: 'deploy',
        confidence: 'resolved' }} }});
    }});
  }});
  return {{ nodes: nodes, edges: edges }};
}}
function elements(mode) {{
  const base = mode === 'containers' ? containerNodes() : {{ nodes: serviceNodes(), edges: [] }};
  const ids = new Set(base.nodes.map(n => n.data.id));
  const links = doc.edges
    .filter(e => ids.has(e.from) && ids.has(e.to))
    .map(e => ({{ data: {{ id: e.from + '->' + e.to + ':' + e.label, source: e.from, target: e.to,
        label: e.label || e.type, type: e.type, confidence: e.confidence, info: (e.evidence || '') }} }}));
  return [...base.nodes, ...base.edges, ...links];
}}
function partElements(part) {{
  const nodes = part.nodes.map(n => ({{ data: {{ id: n.id, label: n.label, kind: 'file',
    info: (n.path || '') + ' · символов: ' + (n.symbols || 0) }} }}));
  const edges = part.edges.map(e => ({{ data: {{ id: e.source + '->' + e.target, source: e.source,
    target: e.target, label: String(e.calls), type: 'calls', confidence: 'resolved',
    info: (e.examples || []).join('\\n') }} }}));
  return [...nodes, ...edges];
}}
const cy = cytoscape({{
  container: document.getElementById('chart'), elements: elements('services'),
  style: [
    {{ selector: 'node', style: {{ label: 'data(label)', 'font-size': 12, color: '#001030',
        'background-color': '#0060f0', width: 34, height: 34, 'text-valign': 'bottom', 'text-margin-y': 4 }} }},
    {{ selector: 'node[kind = "infra"]', style: {{ 'background-color': '#5a6b85', shape: 'round-rectangle' }} }},
    {{ selector: 'node[kind = "external"]', style: {{ 'background-color': '#12a150', shape: 'hexagon' }} }},
    {{ selector: 'node[kind = "container"]', style: {{ 'background-color': '#9fc0ff', width: 20, height: 20 }} }},
    {{ selector: 'node[kind = "file"]', style: {{ 'background-color': '#0047b3', width: 18, height: 18,
        'font-size': 10 }} }},
    {{ selector: 'edge', style: {{ width: 1.5, 'line-color': '#5a6b85', 'target-arrow-shape': 'triangle',
        'target-arrow-color': '#5a6b85', 'curve-style': 'bezier', 'font-size': 10, color: '#5a6b85' }} }},
    {{ selector: 'edge[confidence = "unresolved"]', style: {{ 'line-style': 'dashed' }} }},
    {{ selector: 'edge[type = "kafka"]', style: {{ 'line-color': '#0060f0', 'target-arrow-color': '#0060f0' }} }}
  ],
  layout: {{ name: 'cose', animate: false }}
}});

function redraw(elements, label) {{
  cy.elements().remove();
  cy.add(elements);
  cy.layout({{ name: 'cose', animate: false }}).run();
  document.getElementById('title-line').textContent = label;
}}
function loadPart(serviceId, done) {{
  if (window.SYSTEM_PARTS && window.SYSTEM_PARTS[serviceId]) return done(true);
  const script = document.createElement('script');
  script.src = PARTS_REL + '/' + serviceId + '.js';
  script.onload = () => done(true);
  script.onerror = () => done(false);
  document.head.appendChild(script);
}}
cy.on('tap', 'node', evt => {{
  const id = evt.target.id();
  const meta = partsIndex[id];
  if (!meta || meta.missing) {{
    document.getElementById('legend').textContent =
      'Код-уровень для ' + id + ' не собран. Запустите: tools/codemap/generate.py --system --parts';
    return;
  }}
  loadPart(id, ok => {{
    if (!ok) {{
      document.getElementById('legend').textContent = 'Файл части не найден: ' +
        PARTS_REL + '/' + id + '.js — соберите части (--parts)';
      return;
    }}
    const part = window.SYSTEM_PARTS[id];
    redraw(partElements(part), id + ' — файлов ' + part.nodes.length + ', связей ' + part.edges.length);
    document.getElementById('back').hidden = false;
  }});
}});
document.getElementById('back').addEventListener('click', () => {{
  const mode = document.querySelector('input[name=mode]:checked').value;
  redraw(elements(mode), doc.title);
  document.getElementById('back').hidden = true;
}});
document.querySelectorAll('input[name=mode]').forEach(input => input.addEventListener('change', () => {{
  redraw(elements(input.value), doc.title);
  document.getElementById('back').hidden = true;
}}));
</script>
</body></html>"""


def render_system_html(
    document: dict,
    vendor_rel: str = "vendor/cytoscape.min.js",
    parts_rel: str = "../.local/system-graph/parts",
) -> str:
    """Собрать автономный HTML (без внешних ссылок и без fetch — работает по file://)."""
    return HTML.format(
        title=document["title"],
        services=document["stats"]["by_kind"]["service"],
        edges=document["stats"]["edges"],
        vendor=vendor_rel,
        parts_rel=parts_rel,
        parts_rel_literal=json.dumps(parts_rel),
        data=json.dumps(document, ensure_ascii=False),
    )
