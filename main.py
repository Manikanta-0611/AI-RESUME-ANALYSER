import os
import streamlit as st
from pypdf import PdfReader
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env if available
load_dotenv()

# ==========================================
# STREAMLIT PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="AI Resume Analyser - Groq Qwen",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Professional CSS Styling
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Overall Dark Gradient Background */
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #0b0f19 100%);
        color: #f1f5f9;
    }

    /* Hero Section Header */
    .hero-container {
        padding: 2.5rem 2rem;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
    }

    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.15rem;
        font-weight: 400;
        max-width: 800px;
        line-height: 1.6;
    }

    .tech-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #a5b4fc;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.825rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    /* Glassmorphism Output Cards */
    .glass-card {
        background: rgba(17, 24, 39, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 2rem;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(16px);
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.7);
        padding: 8px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 10px;
        color: #94a3b8;
        font-weight: 500;
        font-size: 1.5rem;
        padding: 0 16px;
        transition: all 0.2s ease-in-out;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        font-weight: 600;
        box-shadow: 0 4px 14px 0 rgba(124, 58, 237, 0.35);
    }

    /* Primary Action Button */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        color: white;
        font-weight: 700;
        font-size: 1.3rem;
        border-radius: 12px;
        border: none;
        padding: 0.8rem 1.8rem;
        box-shadow: 0 8px 25px -5px rgba(79, 70, 229, 0.5);
        transition: all 0.3s ease;
        width: 100%;
        cursor: pointer;
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #1d4ed8 0%, #6d28d9 100%);
        box-shadow: 0 12px 30px -5px rgba(79, 70, 229, 0.7);
        transform: translateY(-2px);
    }

    /* Sidebar Clean Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(11, 15, 25, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.07);
    }

    /* Markdown Tables Custom Polish */
    .glass-card table {
        width: 100%;
        border-collapse: collapse;
        margin: 1.2rem 0;
        font-size: 1.5rem;
    }

    .glass-card th {
        background-color: rgba(30, 41, 59, 0.8);
        color: #38bdf8;
        padding: 12px 16px;
        text-align: left;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        font-weight: 600;
    }

    .glass-card td {
        padding: 12px 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        color: #cbd5e1;
    }

    .glass-card tr:hover td {
        background-color: rgba(255, 255, 255, 0.02);
    }

    /* Metric Badges */
    .metric-badge {
        display: inline-flex;
        align-items: center;
        padding: 6px 14px;
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        border-radius: 8px;
        font-size: 2rem;
        font-weight: 600;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)



# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_config_val(key_name: str, default: str = "") -> str:
    """Retrieves configuration from environment variables or Streamlit secrets."""
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
    """Extracts raw text content from an uploaded PDF resume."""
    try:
        pdf_reader = PdfReader(uploaded_file)
        text_content = []
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_content.append(extracted)
        return "\n".join(text_content).strip()
    except Exception as e:
        st.error(f"❌ Error reading PDF file: {str(e)}")
        return ""


def get_analysis_prompts(resume_text: str, target_role: str, experience_level: str):
    """Constructs detailed prompts for each of the 6 required categories."""
    return {
        "1. Content Clarity & Impact": f"""
You are a senior executive resume reviewer. Analyze this resume for **Content Clarity & Impact** tailored for a {experience_level} {target_role} role.

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your evaluation in clean Markdown:
### 📌 1. Visual Hierarchy & Readability
- Assess section flow, structure, and readability.

### ⚡ 2. Action Verbs & Active Voice
- Identify weak passive phrasing vs strong action verbs. Highlight weak examples and recommend strong alternatives.

### 📈 3. Quantifiable Achievements
- Check for measurable metrics ($, %, scale, team size). Highlight bullets lacking numbers and demonstrate how to add impact metrics.

### 🎯 4. Conciseness & Jargon Balance
- Identify unnecessary fluff or overly dense wording.
""",

        "2. Skills Presentation": f"""
You are a Lead Technical Recruiter evaluating technical competency. Analyze this resume for **Skills Presentation** for a {experience_level} {target_role}.

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your evaluation in clean Markdown:
### 🛠️ 1. Technical Stack Breakdown
- Categorize identified skills: Languages, Frameworks & Libraries, Databases, Tools & Cloud/DevOps.

### ⚖️ 2. Hard vs Soft Skills Balance
- Evaluate organization and representation of technical vs interpersonal skills.

### 🔍 3. Missing Critical Industry Skills
- Identify essential trending tools or frameworks for a {experience_level} {target_role} that are currently missing.

### 🤖 4. ATS Optimization & Formatting
- Reordering and grouping recommendations for optimal ATS parsing.
""",

        "3. Experience Descriptions": f"""
You are a Senior Engineering Manager evaluating work experience descriptions.

Target Role: {target_role}
Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your evaluation in clean Markdown:
### ⭐ 1. STAR Method Compliance
- Assess whether bullets describe Situation, Task, Action, and Result clearly.

### 🔬 2. Technical Depth & Specificity
- Check for high-level vague responsibilities vs concrete engineering achievements.

### ✍️ 3. Top 3 High-Impact Bullet Rewrites
- Select 3 weak bullet points from the resume and rewrite them into high-impact STAR bullets.
""",

        "4. Specific Recommendations for Full Stack Developer": f"""
You are a Principal Full Stack Architect evaluating a candidate for a **Full Stack Developer** position.

Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your evaluation in clean Markdown:
### 🎨 1. Frontend Competency
- Evaluate modern frontend stack (React, Next.js, Vue, TypeScript, Tailwind/CSS, State Management, Web Vitals).

### ⚙️ 2. Backend & API Competency
- Evaluate backend tech (Node.js, Python, Java, REST/GraphQL, Databases, Caching, System Architecture).

### ☁️ 3. DevOps & Database Readiness
- Evaluate SQL/NoSQL databases, Docker, CI/CD pipelines, Cloud platforms (AWS/GCP).

### 💡 4. Recommended Full Stack Portfolio Projects
- Suggest 2 concrete, production-grade project concepts to elevate their Full Stack engineering profile.
""",

        "5. Overall Rating & Checklist": f"""
You are a Talent Acquisition Director giving a final score audit.

Target Role: {target_role}
Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your analysis in Markdown:
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
1.
2.
3.

### ⚠️ Top 3 Critical Areas for Improvement
1.
2.
3.
""",

        "6. Refined Resume": f"""
You are an expert ATS Resume Writer. Rewrite the candidate's resume into a polished, high-impact **Refined Resume** formatted in clean Markdown.

Target Role: {target_role}
Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Instructions:
- Use clean Markdown headers (`# Name`, `## Professional Summary`, `## Technical Skills`, `## Work Experience`, `## Projects`, `## Education`).
- Rewrite work experience bullets into strong STAR action statements with metrics.
- Keep it 100% ready for copy-pasting or downloading.
"""
    }


# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================

def main():
    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <div class="tech-pill">⚡ Powered by Groq AI • Free Tier Qwen 3.6 / 2.5</div>
        <div class="hero-title">AI Resume Analyser</div>
        <div class="hero-subtitle">
            Upload your resume PDF for instant, deep multi-dimensional evaluation across 6 critical hiring pillars tailored for <b>Full Stack Developers</b> and modern tech roles.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Groq API Key Setup
        env_key = get_config_val("GROQ_API_KEY", "")
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=env_key,
            help="Get your free API key at console.groq.com"
        )
        
        if api_key:
            st.success("🔑 API Key configured", icon="✅")
        else:
            st.warning("🔑 Enter your Groq API Key to proceed.", icon="⚠️")
            st.markdown("[👉 Get Free Groq API Key](https://console.groq.com/keys)")

        st.divider()

        # Model Selection
        model_options = ["qwen/qwen3.6-27b", "qwen-2.5-32b", "qwen-2.5-coder-32b", "llama-3.3-70b-versatile"]
        env_model = get_config_val("GROQ_MODEL", "qwen/qwen3.6-27b")
        default_index = model_options.index(env_model) if env_model in model_options else 0

        model_name = st.selectbox(
            "Select Groq LLM Model",
            options=model_options,
            index=default_index,
            help="Free-tier Qwen and LLaMA models hosted on Groq"
        )
        st.caption(f"Active Model: `{model_name}`")

        st.divider()

        # Target Profile Setup
        st.subheader("🎯 Target Profile")
        target_role = st.text_input("Target Job Role", value="Full Stack Developer")
        experience_level = st.selectbox(
            "Experience Level",
            options=["Junior (1-3 yrs)", "Mid-Level (3-5 yrs)", "Senior (5+ yrs)", "Lead / Architect"],
            index=1
        )

    # Upload Workspace
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 📤 Upload Resume")
        uploaded_file = st.file_uploader(
            "Upload your PDF Resume",
            type=["pdf"],
            help="Select a PDF resume file to extract and analyze."
        )

    with col2:
        st.markdown("### 🎯 6 Evaluation Pillars")
        st.markdown("""
        - 📌 **1. Content Clarity & Impact**
        - 🛠️ **2. Skills Presentation**
        - ⭐ **3. Experience Descriptions**
        - 🚀 **4. Full Stack Developer Alignment**
        - 📊 **5. Overall Rating & Audit Checklist**
        - ✨ **6. Refined Resume Rewrite**
        """)

    # PDF Processing & Submit Action
    if uploaded_file is not None:
        resume_text = extract_text_from_pdf(uploaded_file)
        
        if resume_text:
            word_count = len(resume_text.split())
            char_count = len(resume_text)
            
            st.markdown(f"""
            <div style="display: flex; gap: 1rem; margin: 1rem 0;">
                <span class="metric-badge">📄 Text Extracted Successfully</span>
                <span class="metric-badge" style="background: rgba(56, 189, 248, 0.15); border-color: rgba(56, 189, 248, 0.3); color: #38bdf8;">
                    📝 {word_count} Words ({char_count} Chars)
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("🔍 View Extracted Resume Text", expanded=False):
                st.text_area("Extracted Plain Text", resume_text, height=180)

            # Analyze Action Button
            if st.button("🚀 Resume Analyse", type="primary", use_container_width=True):
                if not api_key:
                    st.error("🔑 Please provide a valid Groq API Key in the sidebar before running analysis.")
                    return

                client = Groq(api_key=api_key)
                prompts = get_analysis_prompts(resume_text, target_role, experience_level)
                results = {}

                progress_bar = st.progress(0, text="Initializing Groq LLM engine...")
                total = len(prompts)

                for idx, (category, prompt_text) in enumerate(prompts.items(), start=1):
                    progress_bar.progress(
                        int((idx - 1) / total * 100),
                        text=f"Evaluating Module {idx}/{total}: {category}..."
                    )
                    
                    try:
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a world-class HR director, technical recruiter, and ATS specialist."
                                },
                                {
                                    "role": "user",
                                    "content": prompt_text
                                }
                            ],
                            temperature=0.3,
                            max_tokens=2500
                        )
                        results[category] = response.choices[0].message.content
                    except Exception as e:
                        # Fallback attempt if specific model string has temporary API issue
                        try:
                            fallback_res = client.chat.completions.create(
                                model="qwen/qwen3.6-27b",
                                messages=[
                                    {"role": "system", "content": "You are an expert HR director and technical recruiter."},
                                    {"role": "user", "content": prompt_text}
                                ],
                                temperature=0.3,
                                max_tokens=2500
                            )
                            results[category] = fallback_res.choices[0].message.content
                        except Exception as fb_err:
                            results[category] = f"⚠️ Error during evaluation with `{model_name}`: {str(e)}"

                progress_bar.progress(100, text="✅ Analysis Complete!")
                st.session_state["analysis_results"] = results
                st.session_state["resume_text"] = resume_text

    # Render Results in Tabbed Layout
    if "analysis_results" in st.session_state:
        st.divider()
        st.markdown("## 📊 Analysis Report & Recommendations")
        
        results = st.session_state["analysis_results"]

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📌 1. Clarity & Impact",
            "🛠️ 2. Skills Presentation",
            "⭐ 3. Experience",
            "🚀 4. Full Stack",
            "📊 5. Rating & Audit",
            "✨ 6. Refined Resume"
        ])

        with tab1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("1. Content Clarity & Impact", ""))
            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("2. Skills Presentation", ""))
            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("3. Experience Descriptions", ""))
            st.markdown('</div>', unsafe_allow_html=True)

        with tab4:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("4. Specific Recommendations for Full Stack Developer", ""))
            st.markdown('</div>', unsafe_allow_html=True)

        with tab5:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("5. Overall Rating & Checklist", ""))
            st.markdown('</div>', unsafe_allow_html=True)

        with tab6:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            refined_resume = results.get("6. Refined Resume", "")
            st.markdown(refined_resume)
            st.markdown('</div>', unsafe_allow_html=True)

            st.download_button(
                "📥 Download Refined Resume (.md)",
                data=refined_resume,
                file_name="Refined_Resume.md",
                mime="text/markdown",
                use_container_width=True
            )

        st.divider()
        full_report = "\n\n---\n\n".join([f"# {category}\n{content}" for category, content in results.items()])
        st.download_button(
            "📥 Download Complete Evaluation Report (.md)",
            data=full_report,
            file_name="Complete_Resume_Analysis_Report.md",
            mime="text/markdown",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
