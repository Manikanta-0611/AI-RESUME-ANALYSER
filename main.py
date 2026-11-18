import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# STREAMLIT PAGE CONFIG & THEME
# ==========================================
st.set_page_config(
    page_title="AI Resume Analyser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: linear-gradient(135deg, #090d16 0%, #111827 50%, #0b0f19 100%); color: #f1f5f9; }

    .hero-container {
        padding: 2.5rem 2rem;
        background: linear-gradient(135deg, rgba(30,41,59,0.6) 0%, rgba(15,23,42,0.8) 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
        backdrop-filter: blur(12px);
    }
    .hero-title {
        font-size: 2.8rem; font-weight: 800; letter-spacing: -0.02em;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle { color: #94a3b8; font-size: 1.15rem; font-weight: 400; max-width: 800px; line-height: 1.6; }
    .tech-pill {
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3);
        color: #a5b4fc; padding: 4px 12px; border-radius: 9999px;
        font-size: 0.825rem; font-weight: 600; margin-bottom: 1rem;
    }
    .glass-card {
        background: rgba(17,24,39,0.75); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px; padding: 2rem; margin-top: 1rem; margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5); backdrop-filter: blur(16px);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background-color: rgba(15,23,42,0.7); padding: 8px;
        border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px; white-space: pre-wrap; border-radius: 10px;
        color: #94a3b8; font-weight: 500; font-size: 0.95rem; padding: 0 16px;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important; font-weight: 600;
        box-shadow: 0 4px 14px 0 rgba(124,58,237,0.35);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        color: white; font-weight: 700; font-size: 1.05rem;
        border-radius: 12px; border: none; padding: 0.8rem 1.8rem;
        box-shadow: 0 8px 25px -5px rgba(79,70,229,0.5);
        transition: all 0.3s ease; width: 100%; cursor: pointer;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #1d4ed8 0%, #6d28d9 100%);
        box-shadow: 0 12px 30px -5px rgba(79,70,229,0.7);
        transform: translateY(-2px);
    }
    section[data-testid="stSidebar"] {
        background-color: rgba(11,15,25,0.95);
        border-right: 1px solid rgba(255,255,255,0.07);
    }
    .glass-card table { width: 100%; border-collapse: collapse; margin: 1.2rem 0; font-size: 0.95rem; }
    .glass-card th {
        background-color: rgba(30,41,59,0.8); color: #38bdf8;
        padding: 12px 16px; text-align: left;
        border-bottom: 2px solid rgba(255,255,255,0.1); font-weight: 600;
    }
    .glass-card td {
        padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #cbd5e1;
    }
    .glass-card tr:hover td { background-color: rgba(255,255,255,0.02); }
    .metric-badge {
        display: inline-flex; align-items: center; padding: 6px 14px;
        background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3);
        color: #34d399; border-radius: 8px; font-size: 0.9rem; font-weight: 600;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ==========================================
# MODEL CONFIG (verified Groq model IDs)
# ==========================================
# Verify current IDs at https://console.groq.com/docs/models
MODEL_OPTIONS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]
DEFAULT_MODEL = "openai/gpt-oss-120b"

# ==========================================
# SCORING RUBRIC (deterministic aggregate)
# ==========================================
RUBRIC_WEIGHTS = {
    "clarity": 0.20,
    "skills": 0.20,
    "experience": 0.25,
    "role_fit": 0.20,
    "ats": 0.15,
}
assert abs(sum(RUBRIC_WEIGHTS.values()) - 1.0) < 1e-9, "Rubric weights must sum to 1.0"


def compute_score(sub_scores: dict) -> dict:
    """Weighted aggregate of LLM-produced sub-scores (each 0-100)."""
    total = sum(RUBRIC_WEIGHTS[k] * float(sub_scores.get(k, 0)) for k in RUBRIC_WEIGHTS)
    return {
        "total": round(total, 1),
        "breakdown": {k: float(sub_scores.get(k, 0)) for k in RUBRIC_WEIGHTS},
        "weights": RUBRIC_WEIGHTS,
    }

# ==========================================
# HELPERS
# ==========================================
def get_config_val(key_name: str, default: str = "") -> str:
    val = os.getenv(key_name, "")
    if val:
        return val
    try:
        if key_name in st.secrets:
            return str(st.secrets[key_name])
    except Exception:
        pass
    return default


def extract_text_from_pdf(uploaded_file) -> str:
    try:
        reader = PdfReader(uploaded_file)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts).strip()
    except Exception as e:
        st.error(f"❌ Error reading PDF file: {e}")
        return ""


def call_groq(client: Groq, model: str, system: str, user: str, json_mode: bool = False) -> str:
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=2500,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def call_with_fallback(client: Groq, primary: str, system: str, user: str, json_mode: bool = False) -> str:
    try:
        return call_groq(client, primary, system, user, json_mode)
    except Exception as e:
        if primary != DEFAULT_MODEL:
            st.warning(f"Primary model `{primary}` failed ({e}). Retrying with `{DEFAULT_MODEL}`…")
            return call_groq(client, DEFAULT_MODEL, system, user, json_mode)
        raise

# ==========================================
# PROMPTS
# ==========================================
def get_analysis_prompts(resume_text: str, target_role: str, experience_level: str):
    return {
        "1. Content Clarity & Impact": f"""
You are a senior executive resume reviewer. Analyze this resume for **Content Clarity & Impact** tailored for a {experience_level} {target_role} role.

Resume:
\"\"\"
{resume_text}
\"\"\"

Return clean Markdown:
### 📌 1. Visual Hierarchy & Readability
### ⚡ 2. Action Verbs & Active Voice
### 📈 3. Quantifiable Achievements
### 🎯 4. Conciseness & Jargon Balance
""",
        "2. Skills Presentation": f"""
You are a Lead Technical Recruiter. Analyze **Skills Presentation** for a {experience_level} {target_role}.

Resume:
\"\"\"
{resume_text}
\"\"\"

Return clean Markdown:
### 🛠️ 1. Technical Stack Breakdown
### ⚖️ 2. Hard vs Soft Skills Balance
### 🔍 3. Missing Critical Industry Skills
### 🤖 4. ATS Optimization & Formatting
""",
        "3. Experience Descriptions": f"""
You are a Senior Engineering Manager evaluating work experience.

Target Role: {target_role}
Experience Level: {experience_level}

Resume:
\"\"\"
{resume_text}
\"\"\"

Return clean Markdown:
### ⭐ 1. STAR Method Compliance
### 🔬 2. Technical Depth & Specificity
### ✍️ 3. Top 3 High-Impact Bullet Rewrites
""",
        f"4. Recommendations for {target_role}": f"""
You are a Principal Engineer evaluating a candidate for **{target_role}**.

Experience Level: {experience_level}

Resume:
\"\"\"
{resume_text}
\"\"\"

Return clean Markdown:
### 🎨 1. Core Competency Depth
### ⚙️ 2. Systems / Architecture Readiness
### ☁️ 3. Tooling & Deployment Readiness
### 💡 4. Two Recommended Portfolio Projects
""",
        "5. Overall Rating & Checklist": f"""
You are a Talent Acquisition Director giving a final score audit.

Target Role: {target_role}
Experience Level: {experience_level}

Resume:
\"\"\"
{resume_text}
\"\"\"

Return Markdown:
### 📊 Overall Evaluation Score: [Score out of 100]

### ✅ Resume Audit Checklist
| Section | Status (Pass / Needs Work / Missing) | Key Observation |
| :--- | :--- | :--- |
| Contact Info & Links | | |
| Professional Summary | | |
| Technical Skills Matrix | | |
| Work Experience | | |
| Projects & Architecture | | |
| Education & Certifications | | |

### 🌟 Top 3 Strengths
### ⚠️ Top 3 Critical Areas for Improvement
""",
        "6. Refined Resume": f"""
You are an expert ATS Resume Writer. Rewrite this resume into a polished **Refined Resume** in clean Markdown.

Target Role: {target_role}
Experience Level: {experience_level}

Resume:
\"\"\"
{resume_text}
\"\"\"

Instructions:
- Use `# Name`, `## Professional Summary`, `## Technical Skills`, `## Work Experience`, `## Projects`, `## Education`.
- Rewrite bullets into strong STAR statements with metrics where plausible.
- 100% ready to copy-paste or download.
""",
    }


def get_rubric_prompt(resume_text: str, target_role: str, experience_level: str) -> str:
    return f"""
Score this resume for a {experience_level} {target_role} on five dimensions, each 0-100.
Return ONLY valid JSON of this exact shape, no prose:

{{"clarity": <int>, "skills": <int>, "experience": <int>, "role_fit": <int>, "ats": <int>}}

Resume:
\"\"\"
{resume_text}
\"\"\"

- clarity: structure, action verbs, conciseness
- skills: stack depth, relevance, presentation
- experience: STAR quality, impact, specificity
- role_fit: alignment to {target_role}
- ats: parseability, keyword coverage, formatting
"""

# ==========================================
# MAIN APP
# ==========================================
def main():
    st.markdown("""
    <div class="hero-container">
        <div class="tech-pill">⚡ Powered by Groq • LLaMA 3.3 / Qwen</div>
        <div class="hero-title">AI Resume Analyser</div>
        <div class="hero-subtitle">
            Upload a PDF resume for a deep multi-dimensional evaluation across 6 hiring pillars,
            tailored to your target role and experience level.
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Configuration")
        env_key = get_config_val("GROQ_API_KEY", "")
        api_key = st.text_input("Groq API Key", type="password", value=env_key,
                                help="Get a free key at console.groq.com")
        if api_key:
            st.success("🔑 API Key configured", icon="✅")
        else:
            st.warning("🔑 Enter your Groq API Key.", icon="⚠️")
            st.markdown("[👉 Get Free Groq API Key](https://console.groq.com/keys)")

        st.divider()
        env_model = get_config_val("GROQ_MODEL", DEFAULT_MODEL)
        default_idx = MODEL_OPTIONS.index(env_model) if env_model in MODEL_OPTIONS else 0
        model_name = st.selectbox("Groq LLM Model", MODEL_OPTIONS, index=default_idx)
        st.caption(f"Active: `{model_name}`")

        st.divider()
        st.subheader("🎯 Target Profile")
        target_role = st.text_input("Target Job Role", value="Full Stack Developer")
        experience_level = st.selectbox(
            "Experience Level",
            ["Junior (1-3 yrs)", "Mid-Level (3-5 yrs)", "Senior (5+ yrs)", "Lead / Architect"],
            index=1,
        )

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### 📤 Upload Resume")
        uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf"])
    with col2:
        st.markdown("### 🎯 6 Evaluation Pillars")
        st.markdown("""
        - 📌 **1. Content Clarity & Impact**
        - 🛠️ **2. Skills Presentation**
        - ⭐ **3. Experience Descriptions**
        - 🚀 **4. Role-Specific Recommendations**
        - 📊 **5. Overall Rating & Audit**
        - ✨ **6. Refined Resume Rewrite**
        """)

    if uploaded_file is not None:
        # clear stale results if the file changed
        if st.session_state.get("last_file") != uploaded_file.name:
            st.session_state.pop("analysis_results", None)
            st.session_state.pop("score", None)
            st.session_state["last_file"] = uploaded_file.name

        resume_text = extract_text_from_pdf(uploaded_file)
        if not resume_text:
            return

        wc, cc = len(resume_text.split()), len(resume_text)
        st.markdown(f"""
        <div style="display:flex; gap:1rem; margin:1rem 0;">
            <span class="metric-badge">📄 Text Extracted</span>
            <span class="metric-badge" style="background:rgba(56,189,248,0.15); border-color:rgba(56,189,248,0.3); color:#38bdf8;">
                📝 {wc} Words ({cc} Chars)
            </span>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 View Extracted Text", expanded=False):
            st.text_area("Plain text", resume_text, height=180)

        if st.button("🚀 Analyse Resume", type="primary", width="stretch"):
            if not api_key:
                st.error("🔑 Provide a Groq API Key first.")
                return

            client = Groq(api_key=api_key)
            prompts = get_analysis_prompts(resume_text, target_role, experience_level)
            system_msg = "You are a world-class HR director, technical recruiter, and ATS specialist."
            results: dict[str, str] = {}

            progress = st.progress(0, text="Running 6 evaluations in parallel…")
            total = len(prompts)
            completed = 0

            with ThreadPoolExecutor(max_workers=6) as pool:
                future_map = {
                    pool.submit(call_with_fallback, client, model_name, system_msg, p): cat
                    for cat, p in prompts.items()
                }
                for fut in as_completed(future_map):
                    cat = future_map[fut]
                    try:
                        results[cat] = fut.result()
                    except Exception as e:
                        results[cat] = f"⚠️ Evaluation failed: {e}"
                    completed += 1
                    progress.progress(
                        int(completed / total * 100),
                        text=f"Completed {completed}/{total}: {cat}",
                    )

            # Rubric scoring
            try:
                raw = call_with_fallback(
                    client, model_name,
                    "You are a strict but fair resume scoring engine. Return only JSON.",
                    get_rubric_prompt(resume_text, target_role, experience_level),
                    json_mode=True,
                )
                sub = json.loads(raw)
                st.session_state["score"] = compute_score(sub)
            except Exception as e:
                st.session_state["score"] = {"error": str(e)}

            st.session_state["analysis_results"] = results
            progress.empty()

    # Render
    if "analysis_results" in st.session_state:
        st.divider()
        st.markdown("## 📊 Analysis Report")

        score = st.session_state.get("score", {})
        if "total" in score:
            st.markdown(f"### 🎯 Weighted Score: **{score['total']} / 100**")
            with st.expander("See rubric breakdown"):
                for k, v in score["breakdown"].items():
                    st.write(f"- **{k}**: {v} (weight {score['weights'][k]})")

        results = st.session_state["analysis_results"]
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📌 1. Clarity & Impact",
            "🛠️ 2. Skills",
            "⭐ 3. Experience",
            "🚀 4. Role Fit",
            "📊 5. Rating & Audit",
            "✨ 6. Refined Resume",
        ])
        keys = [
            "1. Content Clarity & Impact",
            "2. Skills Presentation",
            "3. Experience Descriptions",
            f"4. Recommendations for {target_role}",
            "5. Overall Rating & Checklist",
            "6. Refined Resume",
        ]
        for tab, key in zip([tab1, tab2, tab3, tab4, tab5, tab6], keys):
            with tab:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown(results.get(key, "_No output._"))
                st.markdown('</div>', unsafe_allow_html=True)

        refined = results.get("6. Refined Resume", "")
        if refined:
            st.download_button(
                "📥 Download Refined Resume (.md)",
                data=refined, file_name="Refined_Resume.md", mime="text/markdown",
                width="stretch",
            )

        full = "\n\n---\n\n".join(f"# {c}\n{v}" for c, v in results.items())
        st.download_button(
            "📥 Download Full Report (.md)",
            data=full, file_name="Resume_Analysis_Report.md", mime="text/markdown",
            width="stretch",
        )


if __name__ == "__main__":
    main()