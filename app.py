import streamlit as st
import asyncio
from orchestrator import YouTubeOrchestrator
from dotenv import load_dotenv
from supabase import create_client
import os
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv()

st.set_page_config(page_title="YouTube Learning Orchestrator", layout="wide")

# Initialize Supabase client for auth
@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if url and key:
        return create_client(url, key)
    return None

supabase = init_supabase()

# Session State Init
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "stage" not in st.session_state:
        st.session_state.stage = "landing"

init_session_state()

def main():
    if not st.session_state.authenticated:
        render_auth()
    else:
        st.sidebar.success(f"Logged in as: {st.session_state.user_id}")
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.orchestrator = None
            st.rerun()
        
        st.title("📺 YouTube Learning Orchestrator")
        st.caption("Durable Understanding > Passive Watching")

        if st.session_state.stage == "landing":
            render_landing()
        elif st.session_state.stage == "processing":
            render_processing()
        elif st.session_state.stage == "dashboard":
            render_dashboard()
        elif st.session_state.stage == "session":
            render_session()

def render_auth():
    st.title("🔐 Welcome to YouTube Learning Orchestrator")
    
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    
    with tab1:
        with st.form("signin"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if not supabase:
                    st.error("Supabase not configured. Check your .env file.")
                    return
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    st.session_state.authenticated = True
                    st.session_state.user_id = response.user.id
                    # Use clean storage v2 with authenticated client
                    from storage_v2 import Storage
                    storage = Storage(user_id=response.user.id, client=supabase)
                    st.session_state.orchestrator = YouTubeOrchestrator(response.user.id, storage)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
    
    with tab2:
        with st.form("signup"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submit = st.form_submit_button("Sign Up")
            
            if submit:
                if not supabase:
                    st.error("Supabase not configured. Check your .env file.")
                    return
                try:
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    st.success("Account created! Please check your email to verify, then sign in.")
                except Exception as e:
                    st.error(f"Signup failed: {str(e)}")

def render_landing():
    st.header("Start Learning")
    urls_input = st.text_area("Paste YouTube URLs (one per line):", height=150, 
                               placeholder="https://youtube.com/watch?v=...")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Process Videos", type="primary"):
            urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
            if urls:
                if len(urls) > 20:
                    st.error("Maximum 20 videos allowed per batch.")
                else:
                    st.session_state.urls = urls
                    st.session_state.stage = "processing"
                    st.rerun()
            else:
                st.warning("Please enter at least one URL.")

def render_processing():
    st.header("⚙️ Processing Videos...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    async def process():
        status_text.text("Extracting transcripts and generating materials...")
        progress_bar.progress(0.3)
        
        result = await st.session_state.orchestrator.register_videos(st.session_state.urls)
        progress_bar.progress(1.0)
        
        if result["success"]:
            st.success(f"✅ Created {result['modules_count']} modules!")
            if result.get("errors"):
                with st.expander("⚠️ Some videos failed"):
                    for err in result["errors"]:
                        st.write(f"- {err['url']}: {err['error']}")
            st.session_state.stage = "dashboard"
            st.rerun()
        else:
            st.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            if result.get("errors"):
                for err in result["errors"]:
                    st.write(f"- {err['url']}: {err['error']}")
            if st.button("Back"):
                st.session_state.stage = "landing"
                st.rerun()

    asyncio.run(process())

def render_dashboard():
    st.header("📊 Your Learning Roadmap")
    roadmap = st.session_state.orchestrator.storage.get_roadmap()
    
    if not roadmap:
        st.warning("No roadmap found. Please process some videos first.")
        if st.button("Start Over"):
            st.session_state.stage = "landing"
            st.rerun()
        return

    for idx, item in enumerate(roadmap["sequence"]):
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 2])
            
            module = st.session_state.orchestrator.storage.get_module(item['module_id'])
            if module:
                col1.metric("Week", item.get('week', 1))
                col2.write(f"**{module['title']}**")
                # GATED: Concepts only, NO summary here
                concepts = module.get('key_concepts', [])
                if isinstance(concepts, list):
                    col2.caption("Concepts: " + ", ".join(concepts[:5]))
                
                if col3.button("Start Session", key=f"start_{item['module_id']}", type="primary"):
                    session_id = asyncio.run(st.session_state.orchestrator.start_session(item['module_id']))
                    st.session_state.current_session_id = session_id
                    st.session_state.stage = "session"
                    st.session_state.session_step = "reconstruction"
                    st.rerun()
            st.divider()

def render_session():
    st.header("🧠 Active Session")
    session_id = st.session_state.current_session_id
    session = st.session_state.orchestrator.storage.get_session(session_id)
    
    if not session:
        st.error("Session not found.")
        return
    
    st.subheader(f"📖 {session['modules']['title']}")
    
    # Sync steps with database status
    step = session.get("status", "in_progress")
    if step == "in_progress": step = "reconstruction_1"
    
    if step == "reconstruction_1":
        st.write("### Step 2: Reconstruction FIRST (Mandatory)")
        attempts = session.get("reconstruction_attempts", 0)
        st.caption(f"Attempt: {attempts + 1} / 3")
        st.info("💡 Explain what you think this video is teaching. NO hints. Be precise.")
        
        explanation = st.text_area("Your explanation:", height=200)
        if st.button("Submit Explanation", type="primary"):
            if explanation.strip():
                result = asyncio.run(st.session_state.orchestrator.handle_reconstruction(session_id, explanation))
                st.rerun()

    elif step == "attack":
        st.write("### Step 3: Attack phase (AI adversarial)")
        attack = asyncio.run(st.session_state.orchestrator.get_attack_question(session_id))
        st.rerun()

    elif step == "reconstruction_2":
        st.write("### Step 4: Reconstruction (User thinks again)")
        attempts = session.get("reconstruction_attempts", 0)
        st.caption(f"Attempt: {attempts + 1} / 3")
        # Show the attack question
        attack_data = session.get("attack_feedback", [{}])[-1]
        st.error(f"🎯 **Challenge:** {attack_data.get('question', 'Address your gaps.')}")
        st.caption("Identify what is missing, incorrect, or vague in your previous thought.")
        
        repair = st.text_area("Rewrite your explanation:", height=200)
        if st.button("Submit Repair", type="primary"):
            if repair.strip():
                result = asyncio.run(st.session_state.orchestrator.handle_reconstruction(session_id, repair))
                st.rerun()

    elif step == "gated_unlock":
        st.write("### Step 5 & 6: Content Unlock")
        st.success("✅ Mental model anchored. You have unlocked the reference materials.")
        
        tab1, tab2 = st.tabs(["Reference Summary", "Video Context"])
        with tab1:
            st.markdown(f"#### Reference Summary\n{session['modules']['summary']}")
            st.divider()
            st.write("**Key Concepts:**")
            for c in session['modules'].get('key_concepts', []):
                st.write(f"- {c}")
        
        with tab2:
            st.video(session['modules']['videos']['youtube_url'])
            st.caption("Verify, re-check, and resolve confusion.")
        
        if st.button("Proceed to Application Tasks", type="primary"):
            st.session_state.orchestrator.storage.update_session(session_id, {"status": "tasks"})
            st.rerun()

    elif step == "tasks":
        st.write("### Step 7: Application Tasks")
        st.info("💡 Apply this knowledge to a new scenario. Don't just repeat—synthesize.")
        
        # Pull transfer scenarios from module
        scenarios = session['modules'].get('transfer_scenarios', [])
        if scenarios:
            for s in scenarios:
                st.write(f"**Scenario:** {s.get('scenario', 'New Case')}")
                st.caption(f"Challenge: {s.get('challenge', 'Apply your learning.')}")
        
        task_response = st.text_area("Your response:", height=150)
        if st.button("Proceed to Final Quiz", type="primary"):
            asyncio.run(st.session_state.orchestrator.get_generative_quiz(session_id))
            st.rerun()

    elif step == "quiz":
        st.write("### Step 8: Generative Quiz")
        st.warning("⚠️ 10 Generative questions to evaluate your reasoning depth.")
        
        # Retrieve quiz from session if available
        quiz_data = session.get("attack_feedback", []) # Placeholder: check where we store quiz
        # Better: get_generative_quiz should store it in a specific field
        # For now, let's just show it's generated
        st.write("Please answer the following reasoning questions (mentally or in writing):")
        
        if st.button("Finalize Mastery"):
            asyncio.run(st.session_state.orchestrator.complete_session(session_id))
            st.balloons()
            st.session_state.stage = "dashboard"
            st.rerun()

if __name__ == "__main__":
    main()
