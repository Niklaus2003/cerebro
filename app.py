import os
import sys
import glob
import json
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
try:
    if hasattr(st, "secrets"):
        for key in ["GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            if key in st.secrets and st.secrets[key]:
                os.environ[key] = str(st.secrets[key])
except Exception:
    pass

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(BASE_DIR, "graph.json")
DATA_GRAPH_FILE = os.path.join(BASE_DIR, "data", "graph.json")
WIKI_DIR = os.path.join(BASE_DIR, "wiki")
RAW_DIR = os.path.join(BASE_DIR, "raw")
GRAPH_COMPONENT_PATH = os.path.join(BASE_DIR, "graph_component")
CATEGORIES = ["Projects", "Areas", "Resources", "Archives"]

# Register native custom Streamlit component for Graph Network
graph_component = components.declare_component("graph_network", path=GRAPH_COMPONENT_PATH)

# Try importing backend modules
try:
    from ask import ask, load_wiki_notes
    ASK_AVAILABLE = True
except ImportError:
    ASK_AVAILABLE = False

try:
    from capture import save_capture, scrape_url
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False

try:
    from groq import Groq
    from classify import process_file as classify_process_file, ensure_wiki_dirs
    CLASSIFY_AVAILABLE = True
except ImportError:
    CLASSIFY_AVAILABLE = False

try:
    import link
    LINK_AVAILABLE = True
except ImportError:
    LINK_AVAILABLE = False

try:
    import build_graph
    BUILD_GRAPH_AVAILABLE = True
except ImportError:
    BUILD_GRAPH_AVAILABLE = False


# Page Configuration
st.set_page_config(
    page_title="Cerebro — AI Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Modern Dark Aesthetic CSS
st.markdown("""
<style>
    /* Main Theme & Background */
    .stApp {
        background-color: #0A0D12;
        color: #E2E8F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Header Gradient Banner */
    .header-container {
        padding: 1.2rem 1.8rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(12px);
    }
    .header-title {
        background: linear-gradient(90deg, #00E5FF 0%, #3B82F6 50%, #00E676 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 4px;
        margin-bottom: 0;
    }

    /* Cards & Container Glassmorphism */
    .glass-card {
        background: rgba(18, 24, 38, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 22px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        transition: all 0.2s ease-in-out;
    }
    .glass-card:hover {
        border-color: rgba(0, 229, 255, 0.3);
        transform: translateY(-2px);
    }

    /* Metric Display */
    .metric-val {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .metric-lbl {
        font-size: 11px;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 1px;
    }

    /* PARA Category Color Badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.3px;
    }
    .badge-projects { background: rgba(255, 82, 82, 0.15); color: #FF5252; border: 1px solid rgba(255, 82, 82, 0.4); }
    .badge-areas { background: rgba(0, 229, 255, 0.15); color: #00E5FF; border: 1px solid rgba(0, 229, 255, 0.4); }
    .badge-resources { background: rgba(0, 230, 118, 0.15); color: #00E676; border: 1px solid rgba(0, 230, 118, 0.4); }
    .badge-archives { background: rgba(160, 174, 192, 0.15); color: #A0AEC0; border: 1px solid rgba(160, 174, 192, 0.4); }

    /* Custom Streamlit Element Styles & Button Alignments */
    div.stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00E5FF 0%, #1F6FEB 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.25) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(0, 229, 255, 0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* Alignment Fix for Inputs & Selectboxes */
    .stSelectbox, .stTextInput, .stNumberInput {
        margin-bottom: 0px !important;
    }

    /* Tab Custom Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 22px;
        background-color: #121826;
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #94A3B8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
        border-color: #00E5FF !important;
        color: #00E5FF !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

CATEGORY_COLORS = {
    "Projects": "#FF5252",
    "Areas": "#00E5FF",
    "Resources": "#00E676",
    "Archives": "#A0AEC0"
}

@st.cache_data
def load_graph_data():
    """Loads graph.json from root or data/ directory."""
    target_path = GRAPH_FILE if os.path.exists(GRAPH_FILE) else DATA_GRAPH_FILE
    if not os.path.exists(target_path):
        return {"nodes": [], "edges": [], "stats": {}}
    
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading graph data: {e}")
        return {"nodes": [], "edges": [], "stats": {}}

def process_and_rebuild_vault(source_type, source_value, content):
    """
    Executes the full pipeline:
    1. Capture -> raw/
    2. LLM Classify -> wiki/{category}/{filename}.md
    3. Link Engine -> bidirectional markdown links
    4. Graph Builder -> graph.json
    """
    load_graph_data.clear()
    if not CAPTURE_AVAILABLE:
        st.error("Capture module unavailable.")
        return False

    with st.spinner("1/4 Capturing raw resource..."):
        raw_path = save_capture(source_type=source_type, source_value=source_value, content=content)

    with st.spinner("2/4 Classifying note via LLM into PARA architecture..."):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            st.error("GROQ_API_KEY missing in .env")
            return False
        client = Groq(api_key=api_key)
        ensure_wiki_dirs()
        classify_process_file(client, raw_path)

    with st.spinner("3/4 Computing vector embeddings & semantic links..."):
        if LINK_AVAILABLE:
            try:
                link.main()
            except Exception as e:
                print(f"Linking warning: {e}")

    with st.spinner("4/4 Rebuilding knowledge graph..."):
        if BUILD_GRAPH_AVAILABLE:
            try:
                build_graph.main()
            except Exception as e:
                print(f"Graph build warning: {e}")

    return True

def render_vis_graph(nodes, edges, selected_category="All", search_term="", physics_enabled=True, currently_selected_id=None):
    """
    Renders interactive vis-network visualizer using custom Streamlit component IPC.
    Returns the clicked node ID when user clicks a node directly on the visual graph canvas!
    """
    filtered_node_ids = set()
    vis_nodes = []
    
    for n in nodes:
        cat = n.get("category", "Resources")
        title = n.get("title", n.get("id"))
        summary = n.get("summary", "")
        tags = n.get("tags", [])
        
        if selected_category != "All" and cat != selected_category:
            continue
            
        if search_term and search_term.lower() not in title.lower() and search_term.lower() not in summary.lower():
            continue

        filtered_node_ids.add(n["id"])
        color = CATEGORY_COLORS.get(cat, "#00E676")
        
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        clean_tooltip_text = f"[{cat}] {title}\n\nSummary: {summary if summary else 'No summary'}\nTags: {tags_str}"

        is_selected = (n["id"] == currently_selected_id)

        vis_nodes.append({
            "id": n["id"],
            "label": title if len(title) <= 22 else title[:19] + "...",
            "title": clean_tooltip_text,
            "color": {
                "background": color if is_selected else color + "2B",
                "border": "#FFFFFF" if is_selected else color,
                "highlight": {
                    "background": color,
                    "border": "#FFFFFF"
                },
                "hover": {
                    "background": color + "66",
                    "border": color
                }
            },
            "shape": "dot",
            "size": 32 if is_selected else 19,
            "font": {"color": "#FFFFFF" if is_selected else "#E2E8F0", "size": 14 if is_selected else 12, "face": "sans-serif"}
        })

    vis_edges = []
    for e in edges:
        if e["source"] in filtered_node_ids and e["target"] in filtered_node_ids:
            vis_edges.append({
                "from": e["source"],
                "to": e["target"],
                "color": {"color": "rgba(255, 255, 255, 0.15)", "highlight": "#00E5FF"},
                "width": 1.5,
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}}
            })

    reset_token = st.session_state.get("graph_reset_token", 0)

    # Invoke custom component with selectedId and resetToken
    component_value = graph_component(
        nodes=vis_nodes,
        edges=vis_edges,
        physics=physics_enabled,
        selectedId=currently_selected_id,
        resetToken=reset_token,
        default=None,
        key="native_graph_network_component"
    )
    return component_value

def main():
    # Inject auto-select JavaScript for text inputs so clicking into query bar selects previous text for instant overwrite
    components.html("""
    <script>
    (function() {
        function attachAutoSelect() {
            try {
                var doc = window.parent.document;
                var inputs = doc.querySelectorAll('input[type="text"], textarea');
                inputs.forEach(function(input) {
                    if (!input.dataset.autoselectAttached) {
                        input.dataset.autoselectAttached = "true";
                        input.addEventListener('focus', function() {
                            this.select();
                        });
                        input.addEventListener('click', function() {
                            this.select();
                        });
                    }
                });
            } catch(e) {}
        }
        attachAutoSelect();
        setInterval(attachAutoSelect, 600);
    })();
    </script>
    """, height=0, width=0)

    # Top Header Banner
    st.markdown("""
    <div class="header-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 class="header-title">Cerebro — AI Second Brain</h1>
                <p class="header-subtitle">Automated Knowledge Ingestion, PARA Classification, Graph Visualization & RAG Search</p>
            </div>
            <div>
                <span class="badge badge-areas">V1.5 Active</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Load Graph Data
    graph_data = load_graph_data()
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # Initialize Active Node ID state if missing
    if "active_node_id" not in st.session_state and nodes:
        st.session_state["active_node_id"] = nodes[0]["id"]

    # Compute PARA Statistics
    cat_counts = {cat: 0 for cat in CATEGORIES}
    for n in nodes:
        c = n.get("category", "Resources")
        if c in cat_counts:
            cat_counts[c] += 1

    # Top Metric Bar
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f'<div class="glass-card"><div class="metric-lbl">Total Notes</div><div class="metric-val" style="color:#00E5FF;">{len(nodes)}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="glass-card"><div class="metric-lbl">Projects</div><div class="metric-val" style="color:#FF5252;">{cat_counts["Projects"]}</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="glass-card"><div class="metric-lbl">Areas</div><div class="metric-val" style="color:#00E5FF;">{cat_counts["Areas"]}</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="glass-card"><div class="metric-lbl">Resources</div><div class="metric-val" style="color:#00E676;">{cat_counts["Resources"]}</div></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="glass-card"><div class="metric-lbl">Archives</div><div class="metric-val" style="color:#A0AEC0;">{cat_counts["Archives"]}</div></div>', unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Sidebar Controls & Key Status
    st.sidebar.markdown("## 🧠 **Cerebro System**")
    
    def trigger_graph_refresh():
        try:
            from build_graph import build_graph
            build_graph()
        except Exception as err:
            st.sidebar.error(f"Rebuild failed: {err}")
        st.session_state.pop("graph_data_cache", None)
        st.session_state["graph_reset_token"] = st.session_state.get("graph_reset_token", 0) + 1
        st.toast("Knowledge Graph refreshed and reset to center!")

    if st.sidebar.button("🔄 Refresh Graph", key="sidebar_refresh_btn", type="primary", use_container_width=True):
        trigger_graph_refresh()
        st.rerun()

    st.sidebar.markdown("---")

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if gemini_key and not gemini_key.startswith("your_"):
        st.sidebar.success("⚡ Gemini API Active (High Token RAG)")
    elif groq_key and not groq_key.startswith("your_"):
        st.sidebar.info("⚡ Groq API Active (Fast PARA LLM)")
    else:
        st.sidebar.warning("⚠️ Missing API Keys in .env")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Network Graph Stats")
    st.sidebar.markdown(f"• **Nodes (Pages):** `{len(nodes)}`")
    st.sidebar.markdown(f"• **Edges (Links):** `{len(edges)}`")
    if "stats" in graph_data and "generated_at" in graph_data["stats"]:
        st.sidebar.markdown(f"• **Last Built:** `{graph_data['stats']['generated_at'][:19]}`")

    # Main Tabs
    tab_graph, tab_ask, tab_upload, tab_vault = st.tabs([
        "🕸️ **Knowledge Graph Explorer**",
        "🤖 **Ask Cerebro (RAG)**",
        "📥 **Capture & Upload Resource**",
        "📁 **Note Vault Browser**"
    ])

    # =========================================================================
    # TAB 1: KNOWLEDGE GRAPH EXPLORER (With Auto-Sync Right Node Inspector)
    # =========================================================================
    with tab_graph:
        col_graph, col_inspector = st.columns([7, 5], gap="medium")

        if not nodes:
            st.info("No nodes in vault. Add resources using the Upload tab!")
        else:
            # Build node dictionary mappings for dropdown selectbox
            node_titles = {f"[{n.get('category')}] {n.get('title')} ({n.get('id')[:8]})": n for n in nodes}
            label_to_id = {label: n["id"] for label, n in node_titles.items()}
            id_to_label = {n["id"]: label for label, n in node_titles.items()}

            # Synchronize active node ID with component value if clicked on canvas
            canvas_selected_id = st.session_state.get("native_graph_network_component")
            if canvas_selected_id and canvas_selected_id in id_to_label:
                st.session_state["active_node_id"] = canvas_selected_id

            # Active node ID state
            current_active_id = st.session_state.get("active_node_id", nodes[0]["id"])
            if current_active_id not in id_to_label:
                current_active_id = nodes[0]["id"]
                st.session_state["active_node_id"] = current_active_id

            # Sync selectbox key in session state with current_active_id
            st.session_state["inspector_select_box_key"] = id_to_label[current_active_id]

            # Selectbox callback function
            def on_selectbox_change():
                selected_lbl = st.session_state.get("inspector_select_box_key")
                if selected_lbl in label_to_id:
                    st.session_state["active_node_id"] = label_to_id[selected_lbl]

            with col_graph:
                col_head1, col_head2 = st.columns([7, 3])
                with col_head1:
                    st.markdown("### Interactive Network Graph")
                with col_head2:
                    if st.button("🔄 Refresh Graph", key="tab1_refresh_btn", use_container_width=True):
                        trigger_graph_refresh()
                        st.rerun()
                
                # Filter bar
                if st.session_state.get("clear_graph_search_flag"):
                    st.session_state["graph_search_input_key"] = ""
                    st.session_state["clear_graph_search_flag"] = False

                with st.form("form_graph_filter", clear_on_submit=False):
                    c_cat, c_srch, c_clr, c_phys = st.columns([3, 4, 2, 3], vertical_alignment="bottom")
                    with c_cat:
                        selected_cat = st.selectbox("Category Filter", ["All"] + CATEGORIES, index=0)
                    with c_srch:
                        search_query = st.text_input("Highlight Node", placeholder="Type title keywords...", key="graph_search_input_key")
                    with c_clr:
                        btn_clear_graph = st.form_submit_button("🗑️ Clear", use_container_width=True)
                    with c_phys:
                        physics_on = st.checkbox("Enable Physics", value=True)

                if btn_clear_graph:
                    st.session_state["clear_graph_search_flag"] = True
                    st.rerun()

                # Render canvas graph component with current_active_id
                clicked_canvas_id = render_vis_graph(
                    nodes,
                    edges,
                    selected_category=selected_cat,
                    search_term=search_query,
                    physics_enabled=physics_on,
                    currently_selected_id=current_active_id
                )

                # Update active node ID and selectbox state if component returns a new clicked ID
                if clicked_canvas_id and clicked_canvas_id in id_to_label:
                    if st.session_state.get("active_node_id") != clicked_canvas_id:
                        st.session_state["active_node_id"] = clicked_canvas_id
                        st.session_state["inspector_select_box_key"] = id_to_label[clicked_canvas_id]

            with col_inspector:
                st.markdown("### 🔍 Node Inspector Panel")
                
                selected_label = st.selectbox(
                    "Select or Click Canvas Node to Inspect:",
                    list(node_titles.keys()),
                    key="inspector_select_box_key",
                    on_change=on_selectbox_change
                )
                selected_node = node_titles[selected_label]

                cat = selected_node.get("category", "Resources")
                badge_cls = f"badge badge-{cat.lower()}"

                st.markdown(f"""
                <div class="glass-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span class="{badge_cls}">{cat}</span>
                        <span style="font-size:11px; color:#64748B;">ID: {selected_node.get('id')}</span>
                    </div>
                    <h3 style="color:#FFF; margin-top:10px; margin-bottom:6px;">{selected_node.get('title')}</h3>
                    <p style="color:#94A3B8; font-size:13px;"><b>Summary:</b> {selected_node.get('summary', 'No summary available.')}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown("#### Metadata & Connections")
                m_c1, m_c2 = st.columns(2)
                with m_c1:
                    tags = selected_node.get("tags", [])
                    st.markdown(f"**Tags:** `{', '.join(tags) if isinstance(tags, list) else tags}`")
                    st.markdown(f"**Source Type:** `{selected_node.get('source_type', 'N/A')}`")
                with m_c2:
                    st.markdown(f"**Source Value:** `{selected_node.get('source_value', 'N/A')}`")
                    st.markdown(f"**Filepath:** `{selected_node.get('filepath', 'N/A')}`")

                # Find connected nodes (edges)
                connected_edges = [e for e in edges if e["source"] == selected_node["id"] or e["target"] == selected_node["id"]]
                st.markdown(f"**Direct Links ({len(connected_edges)}):**")
                if connected_edges:
                    for e in connected_edges:
                        other_id = e["target"] if e["source"] == selected_node["id"] else e["source"]
                        other_node = next((n for n in nodes if n["id"] == other_id), None)
                        if other_node:
                            st.markdown(f"- 🔗 `[{other_node.get('category')}]` **{other_node.get('title')}**")
                else:
                    st.caption("No direct links.")

                st.markdown("<br/>", unsafe_allow_html=True)
                st.markdown("#### 📄 Note Body Content")
                file_rel = selected_node.get("filepath", "")
                normalized_rel = file_rel.replace("\\", "/")
                candidate_paths = [
                    os.path.join(BASE_DIR, file_rel),
                    os.path.join(BASE_DIR, normalized_rel),
                    os.path.join(BASE_DIR, "wiki", file_rel),
                    os.path.join(BASE_DIR, "wiki", normalized_rel),
                ]
                if "/" in normalized_rel:
                    candidate_paths.append(os.path.join(WIKI_DIR, normalized_rel))

                found_path = None
                for p in candidate_paths:
                    if os.path.exists(p) and os.path.isfile(p):
                        found_path = p
                        break

                if found_path:
                    with open(found_path, "r", encoding="utf-8", errors="replace") as f_n:
                        st.code(f_n.read(), language="markdown")
                else:
                    if selected_node.get("summary"):
                        st.info(f"**Summary:** {selected_node.get('summary')}")
                    st.warning("Note file not found on disk.")

    # =========================================================================
    # TAB 2: ASK CEREBRO (RAG Search Engine with Form Submit on Enter & Clear Button)
    # =========================================================================
    with tab_ask:
        st.markdown("### 🤖 Ask Cerebro RAG Search")
        st.markdown("Ask natural language questions to synthesize answers from your second brain.")

        if st.session_state.get("clear_ask_flag"):
            st.session_state["ask_q_input_key"] = ""
            st.session_state["ask_result_data"] = None
            st.session_state["clear_ask_flag"] = False

        with st.form("ask_rag_form", clear_on_submit=False):
            st_col_q, st_col_k, st_col_btn, st_col_clr = st.columns([6, 2, 2, 2], vertical_alignment="bottom")
            with st_col_q:
                q_text = st.text_input(
                    "Your Question:",
                    placeholder="e.g. What notes do I have on coding or project setup?",
                    key="ask_q_input_key"
                )
            with st_col_k:
                k_val = st.number_input("Top K Sources", min_value=1, max_value=10, value=3, key="ask_k_val_key")
            with st_col_btn:
                submit_ask = st.form_submit_button("🚀 Ask Cerebro", type="primary", use_container_width=True)
            with st_col_clr:
                clear_ask = st.form_submit_button("🗑️ Clear Query", use_container_width=True)

        if clear_ask:
            st.session_state["clear_ask_flag"] = True
            st.rerun()

        if submit_ask:
            if not q_text.strip():
                st.warning("Please enter a valid question.")
            elif not ASK_AVAILABLE:
                st.error("`ask.py` module unavailable.")
            else:
                with st.spinner("Retrieving relevant notes & synthesizing response..."):
                    try:
                        res = ask(q_text, top_k=k_val)
                        st.session_state["ask_result_data"] = res
                    except Exception as err:
                        st.error(f"Search Execution Failed: {err}")

        res = st.session_state.get("ask_result_data")
        if res and isinstance(res, dict) and "answer" in res:
            st.markdown("---")
            st.markdown("### 💡 Cerebro AI Response")
            st.markdown(f"""
            <div class="glass-card" style="border-left: 4px solid #00E5FF; padding: 20px 24px; font-size: 15px; line-height: 1.6;">
                {res['answer']}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("### 📚 Retrieved Context Sources")
            for idx, src in enumerate(res.get("sources", []), start=1):
                cat = src.get("category", "Resources")
                badge_cls = f"badge badge-{cat.lower()}"
                
                with st.expander(f"Source {idx}: [{cat}] {src['title']} (Similarity: {src['score']:.4f})"):
                    st.markdown(f"**Category:** <span class='{badge_cls}'>{cat}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Summary:** {src.get('summary', 'N/A')}")
                    st.markdown(f"**Filepath:** `{src.get('rel_path')}`")
                    st.markdown("**Body Content:**")
                    st.code(src.get("body", "").strip(), language="markdown")

    # =========================================================================
    # TAB 3: CAPTURE & UPLOADER (With Automatic Clear Input Fields On Submit)
    # =========================================================================
    with tab_upload:
        st.markdown("### 📥 Capture & Ingest New Resources")
        st.markdown("Add new notes, articles, or web links. Cerebro will auto-classify, link, and update your graph instantly.")

        input_type = st.radio("Select Resource Source:", ["✍️ Quick Text Note", "🔗 Web Link / Article URL", "📄 Upload File (.txt, .md)"], horizontal=True)

        if input_type == "✍️ Quick Text Note":
            with st.form("form_text_capture", clear_on_submit=True):
                note_content = st.text_area("Note Content / Thoughts:", height=180, placeholder="Write your note content here...")
                btn_submit = st.form_submit_button("✨ Ingest & Rebuild Graph", type="primary")
                
                if btn_submit:
                    if not note_content.strip():
                        st.warning("Note content cannot be empty.")
                    else:
                        success = process_and_rebuild_vault(source_type="text", source_value="streamlit_ui", content=note_content)
                        if success:
                            st.balloons()
                            st.success("Resource captured, classified into PARA, linked, and added to Graph successfully!")
                            st.rerun()

        elif input_type == "🔗 Web Link / Article URL":
            with st.form("form_link_capture", clear_on_submit=True):
                url_val = st.text_input("Article or Document URL:", placeholder="https://example.com/article")
                btn_submit = st.form_submit_button("🌐 Scrape, Ingest & Rebuild Graph", type="primary")

                if btn_submit:
                    if not url_val.strip().startswith("http"):
                        st.warning("Please enter a valid HTTP/HTTPS URL.")
                    else:
                        with st.spinner("Scraping URL contents..."):
                            scraped_text = scrape_url(url_val)
                        
                        success = process_and_rebuild_vault(source_type="link", source_value=url_val, content=scraped_text)
                        if success:
                            st.balloons()
                            st.success(f"Link '{url_val}' ingested and added to Knowledge Graph!")
                            st.rerun()

        elif input_type == "📄 Upload File (.txt, .md)":
            uploaded_file = st.file_uploader("Choose a Text or Markdown file", type=["txt", "md", "markdown", "json"], key="uploader_input_file")
            if uploaded_file is not None:
                file_str = uploaded_file.read().decode("utf-8", errors="replace")
                st.markdown("**File Preview:**")
                st.code(file_str[:400] + ("..." if len(file_str) > 400 else ""), language="markdown")
                
                if st.button("📥 Process File & Add to Graph", type="primary"):
                    success = process_and_rebuild_vault(source_type="file", source_value=uploaded_file.name, content=file_str)
                    if success:
                        st.balloons()
                        st.success(f"File '{uploaded_file.name}' successfully added to Cerebro!")
                        st.rerun()

    # =========================================================================
    # TAB 4: NOTE VAULT BROWSER
    # =========================================================================
    with tab_vault:
        st.markdown("### 📁 Note Vault Browser")
        
        if not nodes:
            st.info("Vault is currently empty.")
        else:
            cat_choice = st.radio("Filter Category:", ["All"] + CATEGORIES, horizontal=True)
            filtered = [n for n in nodes if cat_choice == "All" or n.get("category") == cat_choice]

            st.markdown(f"Displaying **{len(filtered)}** notes in vault:")
            for note in filtered:
                cat = note.get("category", "Resources")
                badge_cls = f"badge badge-{cat.lower()}"
                
                with st.expander(f"[{cat}] {note.get('title')} ({note.get('id')[:8]})"):
                    st.markdown(f"**Category:** <span class='{badge_cls}'>{cat}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Summary:** {note.get('summary', '')}")
                    tags = note.get("tags", [])
                    st.markdown(f"**Tags:** `{', '.join(tags) if isinstance(tags, list) else tags}`")
                    st.markdown(f"**Filepath:** `{note.get('filepath')}`")
                    
                    full_path = os.path.join(BASE_DIR, note.get("filepath", ""))
                    if os.path.exists(full_path):
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f_note:
                            st.code(f_note.read(), language="markdown")

if __name__ == "__main__":
    main()
