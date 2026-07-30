#!/usr/bin/env python3
import os
import sys
import json
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_JSON_PATH = os.path.join(BASE_DIR, "graph.json")
DATA_GRAPH_PATH = os.path.join(BASE_DIR, "data", "graph.json")
OUTPUT_HTML_PATH = os.path.join(BASE_DIR, "graph_viewer.html")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cerebro Knowledge Graph Explorer</title>
  <!-- Load vis-network with fallback -->
  <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.2/standalone/umd/vis-network.min.js" 
          onerror="this.onerror=null;this.src='https://unpkg.com/vis-network/standalone/umd/vis-network.min.js';"></script>
  <style>
    :root {
      --bg-color: #0f172a;
      --panel-bg: rgba(30, 41, 59, 0.92);
      --border-color: #334155;
      --text-color: #f8fafc;
      --muted-color: #94a3b8;
      --accent-color: #3b82f6;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-color);
      color: var(--text-color);
    }

    body {
      display: flex;
      flex-direction: column;
    }

    header {
      background: var(--panel-bg);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-color);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
      height: 60px;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand h1 {
      font-size: 1.2rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      background: linear-gradient(135deg, #60a5fa, #a855f7);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .stats-badge {
      font-size: 0.8rem;
      background: #1e293b;
      padding: 4px 10px;
      border-radius: 9999px;
      border: 1px solid var(--border-color);
      color: var(--muted-color);
    }

    .controls {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    input[type="text"] {
      background: #1e293b;
      border: 1px solid var(--border-color);
      color: var(--text-color);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      width: 220px;
      outline: none;
      transition: border-color 0.2s;
    }

    input[type="text"]:focus {
      border-color: var(--accent-color);
    }

    select {
      background: #1e293b;
      border: 1px solid var(--border-color);
      color: var(--text-color);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
      cursor: pointer;
    }

    .btn {
      background: #2563eb;
      color: white;
      border: none;
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn:hover {
      background: #1d4ed8;
    }

    #main-container {
      position: relative;
      width: 100%;
      height: calc(100vh - 60px);
      display: flex;
      flex: 1;
    }

    #mynetwork {
      width: 100%;
      height: 100%;
      background-color: var(--bg-color);
    }

    #detail-panel {
      width: 340px;
      background: var(--panel-bg);
      backdrop-filter: blur(12px);
      border-left: 1px solid var(--border-color);
      padding: 24px;
      overflow-y: auto;
      display: none;
      flex-direction: column;
      gap: 16px;
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      z-index: 5;
      box-shadow: -4px 0 24px rgba(0, 0, 0, 0.4);
    }

    #detail-panel.active {
      display: flex;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .panel-title {
      font-size: 1.1rem;
      font-weight: 600;
      line-height: 1.4;
    }

    .close-btn {
      background: none;
      border: none;
      color: var(--muted-color);
      font-size: 1.25rem;
      cursor: pointer;
    }

    .close-btn:hover {
      color: var(--text-color);
    }

    .category-tag {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 6px;
    }

    .category-Projects { background: #1e3a8a; color: #93c5fd; }
    .category-Areas { background: #064e3b; color: #6ee7b7; }
    .category-Resources { background: #78350f; color: #fde68a; }
    .category-Archives { background: #374151; color: #d1d5db; }

    .detail-section {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .detail-label {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted-color);
    }

    .detail-value {
      font-size: 0.88rem;
      line-height: 1.5;
      color: #e2e8f0;
    }

    .tags-container {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .tag-pill {
      background: #1e293b;
      border: 1px solid var(--border-color);
      color: #cbd5e1;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
    }

    .legend {
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--panel-bg);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border-color);
      padding: 10px 16px;
      border-radius: 12px;
      display: flex;
      gap: 16px;
      align-items: center;
      z-index: 5;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      color: var(--muted-color);
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <h1>🧠 Cerebro Network Explorer</h1>
      <span class="stats-badge" id="stats-badge">Loading...</span>
    </div>
    <div class="controls">
      <input type="text" id="search-input" placeholder="Search title or tag..." oninput="filterGraph()">
      <select id="category-filter" onchange="filterGraph()">
        <option value="ALL">All Categories</option>
        <option value="Projects">Projects</option>
        <option value="Areas">Areas</option>
        <option value="Resources">Resources</option>
        <option value="Archives">Archives</option>
      </select>
      <button class="btn" onclick="resetView()">Reset Fit</button>
    </div>
  </header>

  <div id="main-container">
    <div id="mynetwork"></div>

    <div id="detail-panel">
      <div class="panel-header">
        <div>
          <div class="panel-title" id="panel-title">Note Title</div>
          <span class="category-tag" id="panel-category">Category</span>
        </div>
        <button class="close-btn" onclick="closePanel()">&times;</button>
      </div>

      <div class="detail-section">
        <span class="detail-label">Summary</span>
        <p class="detail-value" id="panel-summary">-</p>
      </div>

      <div class="detail-section">
        <span class="detail-label">Tags</span>
        <div class="tags-container" id="panel-tags"></div>
      </div>

      <div class="detail-section">
        <span class="detail-label">Source Info</span>
        <p class="detail-value" id="panel-source">-</p>
      </div>

      <div class="detail-section">
        <span class="detail-label">Timestamp</span>
        <p class="detail-value" id="panel-timestamp">-</p>
      </div>

      <div class="detail-section">
        <span class="detail-label">File Location</span>
        <p class="detail-value" style="font-family: monospace; font-size: 0.8rem;" id="panel-filepath">-</p>
      </div>
    </div>

    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div> Projects</div>
      <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div> Areas</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f59e0b"></div> Resources</div>
      <div class="legend-item"><div class="legend-dot" style="background:#6b7280"></div> Archives</div>
    </div>
  </div>

  <script>
    window.addEventListener('DOMContentLoaded', function() {
      if (typeof vis === 'undefined') {
        alert("vis-network library failed to load from CDN. Please check your internet connection.");
        return;
      }

      const rawGraphData = GRAPH_DATA_PLACEHOLDER;

      const categoryColors = {
        "Projects": { background: "#3b82f6", border: "#1d4ed8", highlight: "#60a5fa" },
        "Areas": { background: "#10b981", border: "#047857", highlight: "#34d399" },
        "Resources": { background: "#f59e0b", border: "#b45309", highlight: "#fbbf24" },
        "Archives": { background: "#6b7280", border: "#374151", highlight: "#9ca3af" }
      };

      // Calculate node degrees (connections)
      const degrees = {};
      rawGraphData.edges.forEach(e => {
        degrees[e.source] = (degrees[e.source] || 0) + 1;
        degrees[e.target] = (degrees[e.target] || 0) + 1;
      });

      const nodesArray = rawGraphData.nodes.map(n => {
        const colors = categoryColors[n.category] || categoryColors["Resources"];
        const deg = degrees[n.id] || 0;
        const size = 18 + Math.min(deg * 4, 24);

        return {
          id: n.id,
          label: n.title.length > 28 ? n.title.substring(0, 26) + '...' : n.title,
          title: `<b>${n.title}</b><br><i>Category: ${n.category}</i><br>${n.summary}`,
          shape: 'dot',
          size: size,
          color: {
            background: colors.background,
            border: colors.border,
            highlight: { background: colors.highlight, border: "#ffffff" }
          },
          font: { color: "#f8fafc", size: 13, face: "sans-serif" },
          meta: n
        };
      });

      const edgesArray = rawGraphData.edges.map(e => ({
        from: e.source,
        to: e.target,
        arrows: 'to',
        color: { color: "#475569", highlight: "#94a3b8", opacity: 0.7 },
        width: 1.8,
        smooth: { type: 'continuous' }
      }));

      const nodesDataSet = new vis.DataSet(nodesArray);
      const edgesDataSet = new vis.DataSet(edgesArray);

      const container = document.getElementById('mynetwork');
      const data = { nodes: nodesDataSet, edges: edgesDataSet };

      const options = {
        nodes: {
          borderWidth: 2,
          shadow: true
        },
        edges: {
          shadow: false
        },
        physics: {
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -50,
            centralGravity: 0.01,
            springLength: 100,
            springConstant: 0.08
          },
          maxVelocity: 50,
          minVelocity: 0.1,
          stabilization: { iterations: 150 }
        },
        interaction: {
          hover: true,
          tooltipDelay: 150,
          zoomView: true,
          dragView: true
        }
      };

      window.network = new vis.Network(container, data, options);
      window.nodesDataSet = nodesDataSet;
      window.edgesDataSet = edgesDataSet;
      window.allNodesArray = nodesArray;
      window.allEdgesArray = edgesArray;

      document.getElementById('stats-badge').innerText = `${nodesArray.length} Nodes • ${edgesArray.length} Edges`;

      window.network.once("stabilizationIterationsDone", function() {
        window.network.fit();
      });

      setTimeout(function() {
        window.network.fit();
      }, 400);

      window.network.on("selectNode", function (params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const nodeObj = nodesDataSet.get(nodeId);
          if (nodeObj && nodeObj.meta) {
            showPanel(nodeObj.meta);
          }
        }
      });

      window.network.on("deselectNode", function () {
        closePanel();
      });
    });

    function showPanel(meta) {
      document.getElementById('panel-title').innerText = meta.title || "Untitled Note";
      
      const catEl = document.getElementById('panel-category');
      catEl.innerText = meta.category || "Unassigned";
      catEl.className = `category-tag category-${meta.category || 'Resources'}`;

      document.getElementById('panel-summary').innerText = meta.summary || "No summary available.";
      
      const tagsContainer = document.getElementById('panel-tags');
      tagsContainer.innerHTML = '';
      if (meta.tags && meta.tags.length > 0) {
        meta.tags.forEach(t => {
          const pill = document.createElement('span');
          pill.className = 'tag-pill';
          pill.innerText = t;
          tagsContainer.appendChild(pill);
        });
      } else {
        tagsContainer.innerHTML = '<span class="detail-value" style="color:var(--muted-color)">No tags</span>';
      }

      document.getElementById('panel-source').innerText = `${meta.source_type || 'N/A'} (${meta.source_value || 'N/A'})`;
      document.getElementById('panel-timestamp').innerText = meta.timestamp || 'N/A';
      document.getElementById('panel-filepath').innerText = meta.filepath || 'N/A';

      document.getElementById('detail-panel').classList.add('active');
    }

    function closePanel() {
      document.getElementById('detail-panel').classList.remove('active');
    }

    function resetView() {
      if (window.network) {
        window.network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
      }
    }

    function filterGraph() {
      const searchTerm = document.getElementById('search-input').value.toLowerCase();
      const selectedCategory = document.getElementById('category-filter').value;

      const filteredNodes = window.allNodesArray.filter(n => {
        const matchesSearch = !searchTerm || 
          n.meta.title.toLowerCase().includes(searchTerm) || 
          (n.meta.tags && n.meta.tags.some(t => t.toLowerCase().includes(searchTerm))) ||
          n.meta.summary.toLowerCase().includes(searchTerm);

        const matchesCategory = selectedCategory === "ALL" || n.meta.category === selectedCategory;

        return matchesSearch && matchesCategory;
      });

      const filteredIds = new Set(filteredNodes.map(n => n.id));
      window.nodesDataSet.clear();
      window.nodesDataSet.add(filteredNodes);

      const filteredEdges = window.allEdgesArray.filter(e => filteredIds.has(e.from) && filteredIds.has(e.to));
      window.edgesDataSet.clear();
      window.edgesDataSet.add(filteredEdges);
    }
  </script>
</body>
</html>
"""

def main():
    print("Preparing Cerebro Graph Viewer...")

    graph_data_file = None
    if os.path.exists(GRAPH_JSON_PATH):
        graph_data_file = GRAPH_JSON_PATH
    elif os.path.exists(DATA_GRAPH_PATH):
        graph_data_file = DATA_GRAPH_PATH
    else:
        print("graph.json not found. Running build_graph.py...")
        import subprocess
        python_exe = sys.executable
        res = subprocess.run([python_exe, "build_graph.py"], cwd=BASE_DIR)
        if res.returncode == 0 and os.path.exists(GRAPH_JSON_PATH):
            graph_data_file = GRAPH_JSON_PATH

    if not graph_data_file or not os.path.exists(graph_data_file):
        print(f"Error: Could not locate or build graph.json.", file=sys.stderr)
        sys.exit(1)

    with open(graph_data_file, "r", encoding="utf-8") as f:
        graph_json_str = f.read()

    html_content = HTML_TEMPLATE.replace("GRAPH_DATA_PLACEHOLDER", graph_json_str)

    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Interactive graph viewer generated at: {OUTPUT_HTML_PATH}")
    
    html_uri = os.path.abspath(OUTPUT_HTML_PATH)
    print(f"Opening browser at: file:///{html_uri.replace('\\\\', '/')}")
    webbrowser.open(f"file:///{html_uri}")

if __name__ == "__main__":
    main()
