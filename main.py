import os
import streamlit as st
from pypdf import PdfReader
from groq import Groq
import json

# ==========================================
# STREAMLIT PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="AI Resume Analyser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism CSS Styling
CUSTOM_CSS = """
<style>
    /* Dark Theme Custom Accents */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Header Gradient Text */
    .main-title {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    
    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    /* Category Badges */
    .badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.4);
        margin-right: 0.5rem;
    }

    /* Metric Box */
    .metric-container {
        display: flex;
        align-items: center;
        justify-content: space-around;
        background: rgba(15, 23, 42, 0.6);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #38bdf8;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 23, 42, 0.5);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        font-weight: 600;
    }
    
    /* Primary Action Button */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        border-radius: 12px;
        border: none;
        padding: 0.75rem 1.5rem;
        box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }

    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(90deg, #1d4ed8 0%, #6d28d9 100%);
        box-shadow: 0 6px 20px 0 rgba(79, 70, 229, 0.6);
        transform: translateY(-2px);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def extract_text_from_pdf(uploaded_file) -> str:
    """Extracts raw text content from an uploaded PDF resume."""
    try:
        pdf_reader = PdfReader(uploaded_file)
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            extracted = page.extract_text()
            if extracted:
                text_content.append(extracted)
        
        full_text = "\n".join(text_content).strip()
        if not full_text:
            st.error("⚠️ Unable to extract text from the uploaded PDF. It might be scanned or image-only.")
        return full_text
    except Exception as e:
        st.error(f"❌ Error reading PDF file: {str(e)}")
        return ""

def get_groq_client(api_key: str):
    """Initializes and returns Groq client."""
    if not api_key:
        return None
    return Groq(api_key=api_key)

def get_analysis_prompts(resume_text: str, target_role: str, experience_level: str):
    """Constructs detailed prompts for each of the 6 required modules."""
    
    prompts = {
        "1. Content Clarity & Impact": f"""
You are an expert executive resume reviewer and hiring director.
Analyze the following resume for **Content Clarity & Impact**.

Target Role: {target_role}
Target Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your analysis in clean Markdown with the following structured sections:
### 1. Visual Hierarchy & Formatting Clarity
- Assess readability, section flow, and visual organization.
- Highlight any formatting inconsistencies or layout clutter.

### 2. Action Verbs & Voice
- Identify weak passive verbs vs strong action verbs.
- List specific passive phrases found and recommend high-impact alternatives.

### 3. Quantification & Impact Metrics
- Check if achievements include numbers, percentages, metrics, revenue, scale, or user counts.
- Identify bullet points lacking quantifiable results and show how to add measurable metrics.

### 4. Jargon & Clarity Balance
- Evaluate readability and conciseness.
""",

        "2. Skills Presentation": f"""
You are a Lead Technical Recruiter evaluating candidate skills.
Analyze the following resume for **Skills Presentation**.

Target Role: {target_role}
Target Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your analysis in Markdown with:
### 1. Technical Stack Breakdown
- Categorize identified skills into: Languages, Frameworks/Libraries, Databases, Tools & Platforms, DevOps/Cloud.

### 2. Hard vs Soft Skills Assessment
- List hard technical skills vs soft interpersonal/leadership skills.
- Evaluate balance and organization.

### 3. Missing Essential Skills for {target_role}
- Identify critical trending tools or frameworks expected for a {experience_level} {target_role} that are missing from this resume.

### 4. Skill Organization Recommendations
- Suggest how to reorder or group skills for maximum ATS scanning efficiency.
""",

        "3. Experience Descriptions": f"""
You are a Senior Engineering Manager reviewing work history descriptions.
Analyze the following resume for **Experience Descriptions**.

Target Role: {target_role}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your analysis in Markdown with:
### 1. STAR Method Compliance (Situation, Task, Action, Result)
- Evaluate whether work experience bullets describe clear context, problem solved, action taken, and final outcome.

### 2. Depth & Specificity Analysis
- Identify generic job descriptions (e.g., "Responsible for coding APIs") vs deep engineering descriptions.

### 3. Top 3 Bullet Points Rewrites
- Pick 3 weak or average bullet points from the resume and rewrite them into high-impact, STAR-formatted bullets tailored for {target_role}.
""",

        "4. Specific Recommendations for Full Stack Developer": f"""
You are a Principal Full Stack Architect evaluating a candidate for a **Full Stack Developer** position.
Analyze the resume specifically for **Full Stack Developer alignment**.

Target Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your analysis in Markdown with:
### 1. Frontend Competency
- Evaluate modern frontend frameworks (React, Next.js, Vue, Angular, TypeScript, State Management, CSS/Tailwind, Web Vitals).

### 2. Backend & System Design Competency
- Evaluate backend tech (Node.js, Python, Java, Go, RESTful APIs, GraphQL, Microservices, Authentication, Caching).

### 3. Database & Cloud / DevOps Readiness
- Evaluate SQL/NoSQL databases, ORMs, Docker, Kubernetes, CI/CD pipelines, Cloud platforms (AWS/GCP/Azure).

### 4. Recommended Full Stack Portfolio Projects
- Suggest 2 concrete, production-grade project ideas the candidate can build to dramatically upgrade their Full Stack profile.
""",

        "5. Overall Rating & Checklist": f"""
You are an Executive Talent Scout providing a final evaluation score and audit checklist.

Target Role: {target_role}
Target Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Provide your evaluation in structured Markdown:
### 📊 Overall Score Breakdown
- **Overall Score**: [Provide a score out of 100]
- **Content & Clarity Score**: [0-100]
- **Technical Skills Score**: [0-100]
- **Impact & Metrics Score**: [0-100]
- **ATS Compatibility Score**: [0-100]

### ✅ Resume Checklist Audit
| Section | Status (Pass/Needs Work/Missing) | Key Observation |
| :--- | :--- | :--- |
| Contact & Professional Links | | |
| Professional Summary / Pitch | | |
| Technical Skills Matrix | | |
| Work Experience & Impact | | |
| Projects & Architecture | | |
| Education & Certifications | | |

### 🌟 Top 3 Key Strengths
1.
2.
3.

### ⚠️ Top 3 Critical Areas for Improvement
1.
2.
3.
""",

        "6. Refined Resume": f"""
You are a professional Resume Writer and ATS Optimization Specialist.
Rewrite the candidate's resume into a polished, high-impact, modern **Refined Resume** formatted in clean Markdown.

Target Role: {target_role}
Target Experience Level: {experience_level}

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Instructions:
- Use clean, structured Markdown sections (`# Name`, `## Professional Summary`, `## Technical Skills`, `## Work Experience`, `## Projects`, `## Education`).
- Transform all work experience bullet points into strong STAR-impact statements with action verbs and metrics.
- Group technical skills logically.
- Make it 100% ATS friendly and ready for instant use.
"""
    }
    return prompts


# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================

def main():
    # Header Banner
    st.markdown('<div class="main-title">📄 AI Resume Analyser</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Elevate your resume with instant, AI-powered evaluations powered by <b>Groq LLM Models</b> (Qwen & LLaMA).</div>',
        unsafe_allow_html=True
    )
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Groq API Key Setup
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            value=os.getenv("GROQ_API_KEY", ""),
            help="Get your free API key at https://console.groq.com/keys"
        )
        
        if groq_api_key:
            st.success("🔑 API Key configured", icon="✅")
        else:
            st.warning("⚠️ Enter your Groq API Key to proceed.", icon="🔑")
            st.markdown("[Get Free Groq API Key](https://console.groq.com/keys)")
        
        st.divider()
        
        # Model Selection
        model_options = [
            "qwen-2.5-32b",
            "qwen-2.5-coder-32b",
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "qwen/qwen3.6-27b",
            "Custom Model ID..."
        ]
        
        selected_model_choice = st.selectbox(
            "Select LLM Model",
            options=model_options,
            index=0,
            help="Select Qwen or LLaMA models available on Groq free tier"
        )
        
        if selected_model_choice == "Custom Model ID...":
            selected_model = st.text_input("Enter Custom Model String", value="qwen-2.5-32b")
        else:
            selected_model = selected_model_choice
            
        st.caption(f"Active Model: `{selected_model}`")
        st.divider()
        
        # Candidate Profile Customization
        st.subheader("🎯 Target Profile")
        target_role = st.text_input("Target Job Role", value="Full Stack Developer")
        experience_level = st.selectbox(
            "Experience Level",
            options=["Entry-Level / Graduate", "Junior (1-3 yrs)", "Mid-Level (3-5 yrs)", "Senior (5+ yrs)", "Lead / Principal Architect"],
            index=2
        )
        
        st.divider()
        st.markdown("### 💡 About")
        st.caption(
            "This tool evaluates resumes across 6 key performance pillars using Groq's high-speed AI models."
        )

    # Main Workspace Layout
    col_input, col_info = st.columns([2, 1])
    
    with col_input:
        st.markdown("### 📤 Upload Resume")
        uploaded_file = st.file_uploader(
            "Choose a PDF resume file",
            type=["pdf"],
            help="Upload your resume in PDF format to begin analysis."
        )
        
    with col_info:
        st.markdown("### 🔍 Evaluation Pillars")
        st.markdown("""
        - 1️⃣ **Content Clarity & Impact**
        - 2️⃣ **Skills Presentation**
        - 3️⃣ **Experience Descriptions**
        - 4️⃣ **Full Stack Developer Alignment**
        - 5️⃣ **Overall Rating & Checklist Audit**
        - 6️⃣ **Refined Resume Rewrite**
        """)

    # PDF Processing and Submit
    if uploaded_file is not None:
        resume_text = extract_text_from_pdf(uploaded_file)
        
        if resume_text:
            with st.expander("📄 Extracted PDF Text Preview", expanded=False):
                st.text_area("Raw Text Content", resume_text, height=200)
                
            # Submit Button
            analyze_button = st.button("🚀 Resume Analyse", kind="primary", use_container_width=True)
            
            if analyze_button:
                if not groq_api_key:
                    st.error("🔑 Please provide a valid Groq API Key in the sidebar before starting analysis!")
                    return
                
                client = get_groq_client(groq_api_key)
                prompts = get_analysis_prompts(resume_text, target_role, experience_level)
                
                results = {}
                progress_bar = st.progress(0, text="Initializing analysis engine...")
                
                total_steps = len(prompts)
                
                for idx, (title, prompt_content) in enumerate(prompts.items(), start=1):
                    progress_bar.progress(
                        int((idx - 1) / total_steps * 100),
                        text=f"Analyzing Module {idx}/{total_steps}: {title}..."
                    )
                    
                    try:
                        completion = client.chat.completions.create(
                            model=selected_model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a world-class executive recruiter, ATS expert, and technical hiring manager."
                                },
                                {
                                    "role": "user",
                                    "content": prompt_content
                                }
                            ],
                            temperature=0.3,
                            max_tokens=2500
                        )
                        results[title] = completion.choices[0].message.content
                    except Exception as e:
                        err_msg = str(e)
                        if "model_not_found" in err_msg or "NotFound" in err_msg:
                            # Fallback attempt with standard qwen-2.5-32b if custom name fails
                            try:
                                fallback_completion = client.chat.completions.create(
                                    model="qwen-2.5-32b",
                                    messages=[
                                        {"role": "system", "content": "You are an expert technical resume reviewer."},
                                        {"role": "user", "content": prompt_content}
                                    ],
                                    temperature=0.3,
                                    max_tokens=2500
                                )
                                results[title] = fallback_completion.choices[0].message.content
                            except Exception as fallback_e:
                                results[title] = f"⚠️ Error running module with model `{selected_model}`: {str(e)}"
                        else:
                            results[title] = f"⚠️ Error running analysis for {title}: {str(e)}"

                progress_bar.progress(100, text="✅ Analysis Complete!")
                st.session_state["resume_results"] = results
                st.session_state["resume_text"] = resume_text

    # Display Results if available in Session State
    if "resume_results" in st.session_state:
        st.divider()
        st.markdown("## 📊 Analysis Report & Recommendations")
        
        results = st.session_state["resume_results"]
        
        # Tabs for the 6 prompts
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "1. Clarity & Impact",
            "2. Skills Breakdown",
            "3. Experience",
            "4. Full Stack Recommendations",
            "5. Overall Rating & Audit",
            "6. Refined Resume"
        ])
        
        with tab1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("1. Content Clarity & Impact", "No data"))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("2. Skills Presentation", "No data"))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab3:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("3. Experience Descriptions", "No data"))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab4:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("4. Specific Recommendations for Full Stack Developer", "No data"))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab5:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(results.get("5. Overall Rating & Checklist", "No data"))
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tab6:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            refined_content = results.get("6. Refined Resume", "No data")
            st.markdown(refined_content)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Download refined resume button
            st.download_button(
                label="📥 Download Refined Resume (.md)",
                data=refined_content,
                file_name="Refined_Resume.md",
                mime="text/markdown"
            )
            
        # Complete Report Download
        st.divider()
        full_report_text = "\n\n---\n\n".join([f"# {k}\n{v}" for k, v in results.items()])
        st.download_button(
            label="📥 Download Full Analysis Report (.md)",
            data=full_report_text,
            file_name="Complete_Resume_Analysis_Report.md",
            mime="text/markdown",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
