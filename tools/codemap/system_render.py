"""Рендер system.html: офлайн-страница с проекциями «Сервисы» и «Контейнеры»."""

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
 #legend {{ padding: 6px 18px; background: #e4eeff; color: #0047b3; font-size: 12px; }}
 #chart {{ width: 100vw; height: calc(100vh - 78px); }}
</style></head>
<body>
<header><b>{title}</b> · сервисов {services} · рёбер {edges}
  <label><input type="radio" name="mode" value="services" checked> Сервисы</label>
  <label><input type="radio" name="mode" value="containers"> Контейнеры</label>
</header>
<div id="legend">сплошная линия — подтверждённое ребро · пунктир — неразрешённое (нет консьюмера и т.п.) ·
  наведите курсор на узел/ребро для подсказки</div>
<div id="chart"></div>
<script src="{vendor}"></script>
<script id="graph-data" type="application/json">{data}</script>
<script>
const doc = JSON.parse(document.getElementById('graph-data').textContent);
function serviceNodes() {{
  return doc.nodes.map(n => ({{ data: {{ id: n.id, label: n.title, kind: n.kind, info: n.role || n.note || '' }} }}));
}}
function containerNodes() {{
  const nodes = serviceNodes(), edges = [];
  doc.nodes.forEach(n => {{
    (n.deploy || []).forEach(d => {{
      const cid = n.id + '::' + d.container + ':' + d.port;
      nodes.push({{ data: {{ id: cid, label: d.container + ' :' + d.port, kind: 'container', info: 'деплой-единица ' + n.title }} }});
      edges.push({{ data: {{ id: cid, source: n.id, target: cid, label: 'deploy', type: 'deploy', confidence: 'resolved' }} }});
    }});
  }});
  return {{ nodes: nodes, edges: edges }};
}}
function elements(mode) {{
  const base = mode === 'containers' ? containerNodes() : {{ nodes: serviceNodes(), edges: [] }};
  const ids = new Set(base.nodes.map(n => n.data.id));
  const links = doc.edges
    .filter(e => ids.has(e.from) && ids.has(e.to))
    .map(e => ({{ data: {{ id: e.from + '->' + e.to + ':' + e.label,
        source: e.from, target: e.to, label: e.label || e.type, type: e.type,
        confidence: e.confidence, info: (e.evidence || '') }} }}));
  return [...base.nodes, ...base.edges, ...links];
}}
const cy = cytoscape({{
  container: document.getElementById('chart'), elements: elements('services'),
  style: [
    {{ selector: 'node', style: {{ label: 'data(label)', 'font-size': 12, color: '#001030',
        'background-color': '#0060f0', width: 34, height: 34,
        'text-valign': 'bottom', 'text-margin-y': 4 }} }},
    {{ selector: 'node[kind = "infra"]', style: {{ 'background-color': '#5a6b85', shape: 'round-rectangle' }} }},
    {{ selector: 'node[kind = "external"]', style: {{ 'background-color': '#12a150', shape: 'hexagon' }} }},
    {{ selector: 'node[kind = "container"]', style: {{ 'background-color': '#9fc0ff', width: 20, height: 20 }} }},
    {{ selector: 'edge', style: {{ width: 1.5, 'line-color': '#5a6b85', 'target-arrow-shape': 'triangle',
        'target-arrow-color': '#5a6b85', 'curve-style': 'bezier', 'font-size': 10, color: '#5a6b85' }} }},
    {{ selector: 'edge[confidence = "unresolved"]', style: {{ 'line-style': 'dashed' }} }},
    {{ selector: 'edge[type = "kafka"]', style: {{ 'line-color': '#0060f0', 'target-arrow-color': '#0060f0' }} }}
  ],
  layout: {{ name: 'cose', animate: false }}
}});
cy.on('mouseover', 'node, edge', evt => evt.target.style('border-width', 3));
cy.on('mouseout', 'node, edge', evt => evt.target.removeStyle('border-width'));
cy.elements().forEach(el => {{ if (el.data('info')) el.tooltip = el.data('info'); }});
document.querySelectorAll('input[name=mode]').forEach(input => input.addEventListener('change', () => {{
  cy.elements().remove();
  cy.add(elements(input.value));
  cy.layout({{ name: 'cose', animate: false }}).run();
}}));
</script>
</body></html>"""


def render_system_html(document: dict, vendor_rel: str = "vendor/cytoscape.min.js") -> str:
    """Собрать автономный HTML (без внешних ссылок)."""
    return HTML.format(
        title=document["title"],
        services=document["stats"]["by_kind"]["service"],
        edges=document["stats"]["edges"],
        vendor=vendor_rel,
        data=json.dumps(document, ensure_ascii=False),
    )
