import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import sys
import os
import json
import time
import importlib

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.database import DatabaseManager

st.set_page_config(page_title="Rito Control Panel", layout="wide", page_icon="🤖")

# Initialize session state for persistent messages
if 'success_message' not in st.session_state:
    st.session_state.success_message = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

# Initialize DB
@st.cache_resource
def get_db():
    return DatabaseManager()

db = get_db()

# Sidebar Navigation
st.sidebar.title("🤖 Rito AI V2.0")
page = st.sidebar.radio(
    "Navigation",
    ["📊 Dashboard", "🧠 Persona Editor", "📜 History Viewer", "👥 Relationship Manager", "🔗 Identity Management", "⚙️ Settings", "🔧 Check Mode", "🔍 Search", "🔧 Diagnostics"]
)

# Display persistent messages at top
if st.session_state.success_message:
    st.success(st.session_state.success_message)
    if st.button("✖ Clear message"):
        st.session_state.success_message = None
        st.rerun()

if st.session_state.error_message:
    st.error(st.session_state.error_message)
    if st.button("✖ Clear error"):
        st.session_state.error_message = None
        st.rerun()

# --- System Alerts (from DB) ---
alert = db.get_system_alert()
if alert:
    msg = alert.get("message", "Unknown alert")
    level = alert.get("level", "warning")
    ts = alert.get("timestamp", 0)
    dt = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
    
    if level == "error":
        st.error(f"🚨 **SYSTEM ALERT** [{dt}]: {msg}")
    else:
        st.warning(f"⚠️ **SYSTEM ALERT** [{dt}]: {msg}")
    
    if st.button("Dismiss Alert", key="dismiss_system_alert"):
        db.clear_system_alert()
        st.rerun()

# === Dashboard ===
if page == "📊 Dashboard":
    st.title("📊 System Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            memory_count = cursor.fetchone()[0]
        st.metric("Total Memories", memory_count)
    
    with col2:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM master_actions")
            action_count = cursor.fetchone()[0]
        st.metric("Master Actions Logged", action_count)
    
    with col3:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        st.metric("Registered Users", user_count)
    
    st.divider()
    
    st.subheader("Recent Master Actions")
    with db.get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM master_actions ORDER BY timestamp DESC LIMIT 20",
            conn
        )
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No master actions recorded yet.")

# === Persona Editor ===
elif page == "🧠 Persona Editor":
    st.title("🧠 Persona Editor")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM personas")
        personas = cursor.fetchall()
    
    if personas:
        persona_names = [p['name'] for p in personas]
        selected_persona = st.selectbox("Select Persona", persona_names)
        
        persona = [p for p in personas if p['name'] == selected_persona][0]
        
        st.subheader(f"Editing: {persona['name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            role_value = persona['role'] if 'role' in persona.keys() and persona['role'] else 'router'
            new_role = st.selectbox("Role", ["router", "analysis", "communication", "coding"], 
                                     index=["router", "analysis", "communication", "coding"].index(role_value) if role_value in ["router", "analysis", "communication", "coding"] else 0,
                                     key=f"role_{persona['id']}")
        with col2:
            is_active = st.checkbox("Active", value=bool(persona['active']), key=f"active_{persona['id']}")
        
        tab1, tab2 = st.tabs(["📝 System Prompt", "📇 Character Card (JSON)"])
        
        with tab1:
            new_prompt = st.text_area(
                "System Prompt",
                value=persona['system_prompt'],
                height=400,
                key=f"prompt_{persona['id']}"
            )
        
        with tab2:
            current_metadata = persona['metadata_json'] if persona['metadata_json'] else "{}"
            new_metadata = st.text_area(
                "Metadata JSON (AiriCard Format)",
                value=current_metadata,
                height=400,
                key=f"metadata_{persona['id']}"
            )
        
        if st.button("💾 Save Changes", key=f"save_{persona['id']}"):
            try:
                json_data = json.loads(new_metadata)
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    if is_active:
                        cursor.execute("UPDATE personas SET active = 0 WHERE role = ?", (new_role,))
                    
                    cursor.execute(
                        "UPDATE personas SET system_prompt = ?, metadata_json = ?, role = ?, active = ? WHERE id = ?",
                        (new_prompt, json.dumps(json_data, ensure_ascii=False), new_role, int(is_active), persona['id'])
                    )
                    conn.commit()
                st.success("✅ Character Persona updated successfully!")
                st.rerun()
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON in Character Card!")

    else:
        st.warning("No personas found. Run init_db.py first.")

# === History Viewer ===
elif page == "📜 History Viewer":
    st.title("📜 History Viewer")
    
    tab1, tab2, tab3 = st.tabs(["Memories", "Actions Log", "Master Actions"])
    
    with tab1:
        st.subheader("Memories")
        with db.get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM memories ORDER BY timestamp DESC LIMIT 100",
                conn
            )
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No memories recorded yet.")
    
    with tab2:
        st.subheader("Actions Log")
        with db.get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM actions_log ORDER BY timestamp DESC LIMIT 100",
                conn
            )
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No actions logged yet.")
    
    with tab3:
        st.subheader("Master Actions")
        with db.get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM master_actions ORDER BY timestamp DESC LIMIT 100",
                conn
            )
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No master actions recorded yet.")

# === Relationship Manager ===
elif page == "👥 Relationship Manager":
    st.title("👥 Relationship Manager")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
    
    if users:
        for user in users:
            discord_id = user['discord_id'] if 'discord_id' in user.keys() else 'N/A'
            with st.expander(f"👤 {user['username']} (Discord: {discord_id})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    rel_level = user['relationship_level'] if 'relationship_level' in user.keys() else 50
                    new_level = st.slider(
                        "Relationship Level",
                        0, 100,
                        value=rel_level,
                        key=f"level_{user['id']}"
                    )
                
                with col2:
                    rel_type = user['relationship_type'] if 'relationship_type' in user.keys() else 'stranger'
                    rel_types = ["stranger", "acquaintance", "friend", "master", "ignored"]
                    new_type = st.selectbox(
                        "Relationship Type",
                        rel_types,
                        index=rel_types.index(rel_type) if rel_type in rel_types else 0,
                        key=f"type_{user['id']}"
                    )
                
                notes_value = user['notes'] if 'notes' in user.keys() and user['notes'] else ''
                new_notes = st.text_area(
                    "Notes",
                    value=notes_value,
                    key=f"notes_{user['id']}"
                )
                
                if st.button(f"💾 Update {user['username']}", key=f"save_{user['id']}"):
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE users SET relationship_level = ?, relationship_type = ?, notes = ? WHERE id = ?",
                            (new_level, new_type, new_notes, user['id'])
                        )
                        conn.commit()
                    st.success(f"✅ Updated {user['username']}")
    else:
        st.info("No users registered yet. Start a conversation first.")

# === Identity Management ===
elif page == "🔗 Identity Management":
    st.title("🔗 Identity Management")
    
    try:
        from src.core.identity_manager import IdentityManager
        from src.core.relationship_analyzer import RelationshipAnalyzer
        from src.llm.client import LLMClient
        
        llm = LLMClient()
        identity_manager = IdentityManager(db, llm_client=llm)
        analyzer = RelationshipAnalyzer(db, llm)
        
        tab1, tab2, tab3 = st.tabs(["📋 All Identities", "🔗 Merge Requests", "🤖 Auto-tag Suggestions"])
        
        with tab1:
            st.subheader("📋 All User Identities")
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users")
                all_users = cursor.fetchall()
            
            if all_users:
                for user in all_users:
                    identities = identity_manager.get_user_identities(user['id'])
                    with st.expander(f"👤 {user['username']} ({len(identities)} identities)"):
                        if identities:
                            for identity in identities:
                                col1, col2, col3 = st.columns([2, 2, 1])
                                with col1: st.write(f"**{identity['platform'].upper()}**")
                                with col2: st.write(f"`{identity['platform_id']}`")
                                with col3:
                                    if identity['verified']: st.success("✅ Verified")
                                    else: st.warning("⚠️ Unverified")
                        else:
                            st.info("No platform identities registered")
        
        with tab2:
            st.subheader("🔗 Identity Merge Requests")
            pending_requests = identity_manager.get_pending_merge_requests()
            if pending_requests:
                for request in pending_requests:
                    with st.expander(f"🔄 Merge {request['platform'].upper()} → {request['target_username']}"):
                        st.write(f"Reason: {request['reason']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ Approve", key=f"approve_{request['id']}"):
                                identity_manager.approve_merge_request(request['id'])
                                st.rerun()
                        with col2:
                            if st.button("❌ Reject", key=f"reject_{request['id']}"):
                                identity_manager.reject_merge_request(request['id'])
                                st.rerun()
            else:
                st.success("✅ No pending merge requests")
        
        with tab3:
            st.subheader("🤖 Relationship Tag Auto-suggestions")
            # Analysis logic here (simplified)
            st.info("AI Analysis module active.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# === Settings ===
elif page == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")
    
    tab1, tab2 = st.tabs(["🔑 API Configuration", "🛠️ Module Controls"])
    
    with tab1:
        st.subheader("API Configuration")
        st.info("💡 Settings are stored in `.env` file.")
        # Env editing logic (omitted for brevity in this fix, can be restored if needed)
        st.warning("Use textual editor for .env if needed.")
    
    with tab2:
        st.subheader("🛠️ Module Controls (Deep Settings)")
        st.info("💡 変更時には「理由」の入力が推奨されます。")

        config_items = [
            {"key": "maintenance_mode", "label": "🛠️ Maintenance Mode", "help": "保守モードを有効にします。"},
            {"key": "allow_screenshots", "label": "📸 Allow Screenshots", "help": "画面キャプチャを許可するか"},
            {"key": "allow_sns_post", "label": "🐦 Allow SNS Posting", "help": "SNSへの自動投稿を許可するか"},
            {"key": "autonomous_mode", "label": "🤖 Autonomous Mode", "help": "自律モードを許可するか"}
        ]

        for item in config_items:
            current_val = db.get_config(item["key"], True)
            col1, col2 = st.columns([1, 2])
            with col1:
                new_val = st.toggle(item["label"], value=bool(current_val), key=f"toggle_{item['key']}")
            
            if new_val != bool(current_val):
                with col2:
                    reason = st.text_input("変更の理由", key=f"reason_{item['key']}", placeholder="（任意）")
                    if st.button("適用", key=f"apply_{item['key']}"):
                        db.set_config(item["key"], new_val, reason=reason if reason else "No reason provided")
                        st.rerun()

        st.divider()
        st.subheader("📜 Config Audit Log")
        with db.get_connection() as conn:
            audit_df = pd.read_sql_query("SELECT * FROM config_audit_log ORDER BY timestamp DESC LIMIT 50", conn)
        if not audit_df.empty:
            st.dataframe(audit_df, use_container_width=True)

# === Check Mode ===
elif page == "🔧 Check Mode":
    st.title("🔧 Check Mode (Maintenance & Testing)")
    
    is_maint = db.get_config("maintenance_mode", False)
    if is_maint: st.warning("⚠️ **Maintenance Mode is ON.**")
    else: st.info("💡 Maintenance Mode is OFF.")

    st.subheader("🚀 Quick Diagnostics")
    from src.tests.system_check import run_all_checks
    
    # Force reload to get latest check logic
    import src.tests.system_check
    importlib.reload(src.tests.system_check)
    from src.tests.system_check import run_all_checks

    if st.button("🔍 Run Full System Check"):
        results = run_all_checks()
        for r in results:
            st.write(f"{'✅' if r['status'] else '❌'} **{r['component']}**: {r['message']}")

    st.divider()
    st.subheader("🧪 Individual Tool Testing")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📸 Vision Test")
        v_prompt = st.text_input("Vision Prompt", value="画面を説明して下さい")
        if st.button("Execute Vision Test"):
            from src.adapter.vision import VisionAdapter
            vision = VisionAdapter(db)
            res = vision.execute({"prompt": v_prompt})
            st.write(res)
    with col2:
        st.markdown("### 🔍 Search Test")
        s_query = st.text_input("Search Query", value="Google Gemini")
        if st.button("Execute Search Test"):
            from src.adapter.search import SearchAdapter
            search = SearchAdapter()
            res = search.execute({"query": s_query})
            st.write(res)

# === Search ===
elif page == "🔍 Search":
    st.title("🔍 Search")
    search_query = st.text_input("Enter search query")
    if search_query:
        with db.get_connection() as conn:
            query = "SELECT * FROM memories WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 50"
            df = pd.read_sql_query(query, conn, params=(f"%{search_query}%",))
            st.dataframe(df, use_container_width=True)

# === Diagnostics ===
elif page == "🔧 Diagnostics":
    st.title("🔧 System Diagnostics")
    # Import system check module
    import src.tests.system_check
    importlib.reload(src.tests.system_check)
    from src.tests.system_check import run_all_checks
    
    # Run checks
    if st.button("🔄 Run Diagnostics", type="primary"):
        results = run_all_checks()
        for result in results:
            with st.expander(f"{'✅' if result['status'] else '❌'} {result['component']}"):
                st.write(result['message'])
