import streamlit as st
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import os
import whisper
import tempfile
import re
import requests
import wikipedia
from groq import Groq
from pypdf import PdfReader
from PIL import Image
import base64
from io import BytesIO
from bs4 import BeautifulSoup

# Initialize Groq Client
client = Groq(
    api_key=st.secrets["GROQ_API_KEY"]
)
@st.cache_resource
def load_whisper():
    return whisper.load_model("base")
whisper_model = load_whisper()

# ---------------- CORE UTILITY FUNCTIONS ---------------- #

def get_weather(city: str) -> str:
    """Fetches real-time weather data for a given city using OpenWeatherMap API."""
    api_key = st.secrets["OPENWEATHER_API_KEY"]
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            temp = data["main"]["temp"]
            weather = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            return f"🌦️ **Weather in {city.title()}**\n\n🌡️ **Temperature:** {temp}°C\n☁️ **Condition:** {weather.capitalize()}\n💧 **Humidity:** {humidity}%"
        return f"❌ Weather Error: {data.get('message', 'City not found.')}"
    except Exception as e:
        return f"⚠️ Weather Service Unavailable. ({e})"


def get_news(topic: str) -> str:
    """Fetches the top 5 latest news articles with summaries for a given topic using NewsAPI."""
    api_key = st.secrets["NEWS_API_KEY"]
    url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={api_key}&pageSize=5"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                articles = data.get("articles", [])
                if not articles:
                    return f"📰 No recent news found about '{topic}'."
                
                news_result = f"📰 **Latest News About {topic.title()}**\n\n"
                for article in articles[:5]:
                    title = article.get("title", "No Title Available")
                    description = article.get("description", "")
                    url_link = article.get("url", "")
                    
                    # 1. Format the Title as a clickable link
                    if url_link:
                        news_result += f"🔗 **[{title}]({url_link})**\n"
                    else:
                        news_result += f"• **{title}**\n"
                        
                    # 2. Append a short preview snippet/summary of the news item
                    if description:
                        truncated_desc = description[:150] + "..." if len(description) > 150 else description
                        news_result += f"*{truncated_desc}*\n\n"
                    else:
                        news_result += "_No summary description available for this story._\n\n"
                        
                return news_result
        return "❌ News data not available at the moment."
    except Exception as e:
        return f"⚠️ News Service Unavailable. ({e})"


def get_wikipedia_summary(query: str) -> str:
    """Finds the best matching article title first, then safely fetches its summary."""
    try:
        cleaned_query = re.sub(r'[^\w\s]', '', query).strip()
        if not cleaned_query:
            return "❌ Please provide a valid search term."
            
        search_results = wikipedia.search(cleaned_query)
        if not search_results:
            return f"❌ No Wikipedia entry found for '{cleaned_query}'."
            
        best_match = search_results[0]
        summary = wikipedia.summary(best_match, sentences=3)
        return f"📘 **Wikipedia Result for {best_match}**\n\n{summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:3])
        return f"🔍 **Multiple entries found.** Did you mean: {options}?"
    except Exception:
     return f"❌ Could not find a clear Wikipedia profile for '{query}'."


def extract_website_content(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Remove unnecessary elements
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        text = soup.get_text(separator=" ")
        text = " ".join(text.split())

        return text[:15000]

    except Exception as e:
        return f"Website Error: {e}"
    
    
# ---------------- AI VOICE FUNCTION ---------------- #

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(
        buffered.getvalue()
    ).decode()

def speak_text(text):
    tts = gTTS(text=text, lang="en")
    audio_file = "response.mp3"
    tts.save(audio_file)
    return audio_file


# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(
    page_title="Zoop One AI",
    page_icon="🤖",
    layout="wide"
)

# ---------------- CUSTOM CSS ---------------- #
st.markdown("""
<style>

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(to bottom, #020617, #0F172A);
    border-right: 1px solid #1E293B;
}

/* Sidebar Text */
[data-testid="stSidebar"] * {
    color: white;
}

/* Sidebar Width */
section[data-testid="stSidebar"] {
    width: 320px !important;
}

/* File Uploader Container */
[data-testid="stFileUploader"] {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 12px;
}
            
/* Upload Button */
.stFileUploader button {
    background: linear-gradient(90deg, #2563EB, #7C3AED) !important;
    color: white !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: 600 !important;
}

/* Main Heading */
.main-title {
    font-size: 42px;
    font-weight: 700;
    text-align: center;
    margin-top: 10px;
    color: #F8FAFC;
}

/* Gradient Text */
.gradient-text {
    background: linear-gradient(90deg, #60A5FA, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Subtitle */
.sub-text {
    text-align: center;
    font-size: 16px;
    color: #94A3B8;
    margin-top: 10px;
    margin-bottom: 30px;
}

/* Chat Input */
.stChatInput input {
    background: #111827 !important;
    color: white !important;
    border-radius: 14px !important;
    padding: 12px !important;
    font-size: 16px !important;
    border: 1px solid #334155 !important;
}

/* Mini Feature Cards */
.mini-features {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 20px;
    margin-bottom: 25px;
}

.mini-card {
    background: rgba(17, 24, 39, 0.7);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 16px 22px;
    border-radius: 14px;
    color: white;
    font-size: 15px;
    font-weight: 600;
    backdrop-filter: blur(10px);
    transition: 0.3s;
}

.mini-card:hover {
    border: 1px solid #3B82F6;
    transform: translateY(-2px);
}

/* User Message */
[data-testid="stChatMessageContent"] {
    padding: 14px;
    border-radius: 14px;
    font-size: 16px;
    line-height: 1.6;
}

/* Assistant Message */
[data-testid="stChatMessage"]:has(div[data-testid="stMarkdownContainer"]) {
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 12px;
    margin-bottom: 14px;
}

/* User Bubble */
.stChatMessage.user {
    background: rgba(37, 99, 235, 0.15);
    border-radius: 16px;
    padding: 12px;
}

/* Better Text Visibility */
.stMarkdown {
    color: #F8FAFC !important;
}

/* --- BULLETPROOF FILENAME VISIBILITY PATCH --- */

/* 1. Force the file element bounding card background to a clear Slate Blue */
[data-testid="stFileUploaderFile"],
div[data-testid="stFileUploaderCard"] {
    background-color: #1E293B !important; 
    border: 1px solid #475569 !important;
    border-radius: 12px !important;
    padding: 10px !important;
}

/* 2. Universal override for text strings nested deep inside the uploaded card */
[data-testid="stFileUploaderFile"] div,
[data-testid="stFileUploaderFile"] span,
[data-testid="stFileUploaderFile"] p,
div[data-testid="stFileUploaderCard"] div,
div[data-testid="stFileUploaderCard"] span {
    color: #FFFFFF !important;
    opacity: 1 !important;
}

/* 3. Specifically targets file size or structural metrics to display as soft gray */
[data-testid="stFileUploaderFile"] data,
[data-testid="stFileUploaderFile"] small {
    color: #94A3B8 !important;
}

/* 4. Keeps the close (X) interaction icon clean */
[data-testid="stFileUploaderFile"] button svg,
div[data-testid="stFileUploaderCard"] button svg {
    fill: #94A3B8 !important;
}  
            
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ---------------- #
with st.sidebar:

    st.markdown("""
    <h2 style="
    color:white;
    font-weight:700;
    margin-top:10px;
    margin-bottom:20px;
    ">
    🤖 Zoop One AI
    </h2>
    """, unsafe_allow_html=True)

    st.markdown("---")

    menu = st.radio(
    "📌 Navigation",
    [
        "💬 AI Chat",
        "📄 Resume Analysis",
        "🎤 Interview",
        "🎨 Logo Generator"
    ]
)

    # Resume Upload
    uploaded_file = st.file_uploader(
        "📄 Upload Resume",
        type=["pdf", "docx"]
    )

    # Image Upload
    uploaded_image = st.file_uploader(
        "👁️ Upload Image",
        type=["jpg", "jpeg", "png"]
    )

    # Experience Input
    experience = st.text_area(
        "💼 Describe Your Experience",
        placeholder="Example: Python Developer with 2 years experience...",
        height=120
    )

    # Interview Mode
    interview_mode = st.toggle(
        "🧠 Enable Mock Interview"
    )

    resume_text = ""
    image_description = ""

    if uploaded_image:
        image = Image.open(uploaded_image)

        st.image(
            image,
            caption="Uploaded Image",
            use_container_width=True
        )

    if uploaded_file is not None:
        pdf_reader = PdfReader(uploaded_file)

        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                resume_text += text

        st.success("✅ Resume uploaded successfully")

    st.markdown("---")

    st.markdown("### 🚀 Features")

    st.markdown("""
⚡ Zoop One AI Features
📄 ATS Resume Analysis
🎯 Career Roadmaps
💼 Interview Preparation
💻 Coding Assistance
🤖 General AI Chat
📚 Educational Support
🧠 Skill Gap Detection
🌟 Professional Guidance
🚀 Smart AI Assistant
""")

    st.markdown("---")

    st.markdown("### ⚙️ Settings")

    st.selectbox(
        "Choose AI Model",
        ["Groq Llama3", "Phi3", "Gemma"]
    )

    st.slider(
        "Response Creativity",
        0.0,
        1.0,
        0.5
    )

  # ---------------- WEATHER WIDGET ---------------- #
    st.markdown("---")
    st.markdown("### 🌦️ Environment Info")

    city_input = st.text_input(
        "Enter City for Weather Update",
        placeholder="e.g., Delhi, New York",
        key="sidebar_weather"
    )

    if city_input:
        with st.spinner("Fetching weather..."):
            weather_report = get_weather(city_input)
            st.info(weather_report)

# ---------------- WEBSITE URL CHAT ---------------- #
    st.markdown("---")
    st.markdown("### 🌐 Website URL Chat")

    website_url = st.text_input(
        "Enter Website URL",
        placeholder="https://example.com"
    )

    website_content = ""

    if website_url:
        with st.spinner("Reading website..."):
            website_content = extract_website_content(
                website_url
            )

            st.success("✅ Website loaded successfully")


# ---------------- MAIN TITLE ---------------- #
st.markdown(
    """
    <h1 class="main-title">
        <span class="gradient-text">
            Zoop One AI 
        </span>
    </h1>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<div class="sub-text">
Your intelligent AI assistant for careers, coding, learning, productivity, and everyday conversations.
</div>
""", unsafe_allow_html=True)


# ---------------- FEATURE SECTION ---------------- #
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
<div class="mini-features">
<div class="mini-card">
📄 Resume Analysis
</div>
<div class="mini-card">
🎯 Career Roadmaps
</div>
<div class="mini-card">
💡 Interview Prep
</div>
</div>
""", unsafe_allow_html=True)
    
    image_context = ""

if uploaded_image:
    image_context = """
User has uploaded an image.
Analyze the image carefully and explain:
- Objects
- People
- Scene
- Text visible in image
- Colors
- Context
"""
     
# --- TAB 1: AI CHAT ----------------------------
if menu == "💬 AI Chat":
    if "messages" not in st.session_state:
        st.session_state.messages = []

    user_input = ""

    # Voice Input Layer
    audio = mic_recorder(
        start_prompt="🎤 Start Recording",
        stop_prompt="⏹ Stop Recording",
        key="recorder"
    )

    # SECURE ENCLOSURE FIX: Indented inside audio check loop to prevent NameError
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio["bytes"])
            temp_audio_path = temp_audio.name

        with st.spinner("Transcribing your audio..."):
            result = whisper_model.transcribe(temp_audio_path)
            user_input = result["text"]
            st.success(f"🎤 You said: {user_input}")
            
        # Clean up audio files securely
        try:
            os.remove(temp_audio_path)
        except:
            pass

    # Typed Input Layer
    typed_input = st.chat_input("Ask anything...")
    if typed_input:
        user_input = typed_input

    # Show old conversational logs on screen
    for message in st.session_state.messages:
        if message["role"] != "system":
            with st.chat_message(message["role"]):
                if "ATS Score" in message["content"]:
                    score_match = re.search(r"ATS Score:\s*(\d+)", message["content"], re.IGNORECASE)
                    ats_score = int(score_match.group(1)) if score_match else 0
                    st.markdown("## 📊 ATS Resume Score")
                    st.progress(ats_score / 100)
                    st.markdown(f"### ✅ ATS Score: {ats_score}/100")
                    st.markdown(
                        f"""
                        <div style="background: linear-gradient(135deg, #1E293B, #0F172A); padding: 20px; border-radius: 18px; border: 1px solid #334155; margin-top: 20px;">
                            <p style="color:white; white-space: pre-wrap; line-height:1.8;">{message["content"]}</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(message["content"])

    # User active transaction processing
    if user_input:
        # Show user query message bubble
        with st.chat_message("user"):
            st.markdown(user_input)

        # Save user message to chat data state
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
         # ----------------------------------------------------
        # 📰 LIVE NEWS INTERCEPTION (FIXED & CLEANED)
        # ----------------------------------------------------
        if "news" in user_input.lower():
            with st.chat_message("assistant"):
                with st.spinner("Fetching latest news updates..."):
                    # Clean up the query string text safely
                    topic = user_input.lower()
                    topic = topic.replace("news", "")
                    topic = topic.replace("about", "")
                    topic = topic.replace("latest", "")
                    topic = topic.replace("today", "")
                    topic = topic.strip()
                    
                    if "stock market" in topic or "share market" in topic:
                        topic = "finance"
                    
                    if not topic:
                        topic = "technology"  # Safe default fallback

                    news_response = get_news(topic)
                    st.markdown(news_response)
                    
                    # Save to chat history session memory
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": news_response
                    })
            st.stop() # Stops execution so it doesn't trigger the Groq API call below
         
        # ----------------------------------------------------
        # 📘 WIKIPEDIA KNOWLEDGE INTERCEPTION (FIXED WITH SEARCH MATCH)
        # ----------------------------------------------------
        if "wikipedia" in user_input.lower():
            with st.chat_message("assistant"):
                with st.spinner("Searching Wikipedia database..."):
                    # Strip away conversational words to parse a clean search phrase
                    search_query = (
                        user_input.lower()
                        .replace("what is", "")
                        .replace("who is", "")
                        .replace("define", "")
                        .replace("wikipedia", "")
                        .replace("about", "")
                        .strip()
                    )
                    
                    if search_query:
                        wiki_response = get_wikipedia_summary(search_query)
                        st.markdown(wiki_response)
                        
                        # Persist output into session conversational history logs
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": wiki_response
                        })
            st.stop() # Halts app pipeline early to save precious LLM usage tokens
        # ----------------------------------------------------

        # ----------------------------------------------------
        # 🤖 CORE LLM ASSISTANT GENERATION BLOCK (BOUNDED SAFELY)
        # ----------------------------------------------------
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are Zoop One AI. Remember previous conversation context. "
                                "You are a smart AI assistant like ChatGPT that can help with "
                                "general conversations, coding, resume analysis, ATS scoring, "
                                "career guidance, education, emotional support, interview preparation, "
                                "and professional advice."
                            )
                        }
                    ]

                    # Add history thread contexts
                    for msg in st.session_state.messages[:-1]:
                        messages.append({"role": msg["role"], "content": msg["content"]})

                        website_context = ""


                        if website_url:
                          website_context = extract_website_content(
                             website_url
                             )
                         

                          image_context = ""

                        if uploaded_image:
                         image_context = """
                         User has uploaded an image.
                         Please explain everything visible in the image.
                         Describe:
                         - Objects
                         - People
                         - Scene
                         - Text if visible
                         - Colors
                         - Context
                        """

                   # ----------------------------------------------------
                    # 🧠 COMPREHENSIVE ENGINEERING CONTEXT INSTRUCTION PARAMETERS
                    # ----------------------------------------------------
                    combined_prompt = f"""
You are Zoop One AI.
You are a highly intelligent, professional, friendly, and helpful AI assistant like ChatGPT.

You can help users with:
General conversations, Resume analysis, ATS score analysis, Career guidance, Interview preparation, Coding and debugging, Python, SQL, AI, and programming help, Educational support, Teaching explanations, Professional advice, Emotional support conversations, Productivity and study guidance, Roadmaps and skill development.
"IMPORTANT: You are multilingual. You can understand and communicate in "
                                "Hindi, English, and other regional Indian languages fluently. "
                                "Always respond in the same language the user uses to communicate with you."
Rules:
If user asks normal questions, answer naturally like ChatGPT.
If user uploads a resume, analyze it professionally.
If user asks career questions, act like a career coach.
If user asks coding questions, act like a software engineer.
If user asks educational questions, teach clearly step-by-step.
If user is emotional or sad, respond supportively.
Always give intelligent, structured, professional, and conversational responses.
Only use Resume Analysis, ATS Analysis, Interview Mode, Website Content, or Image Analysis when the user's request is related to those inputs.
Otherwise answer normally.

If user asks for a career roadmap:

Generate a detailed roadmap including:

- Beginner Level
- Intermediate Level
- Advanced Level
- Skills to Learn
- Projects to Build
- Certifications
- Job Roles
- Expected Salary Range
- Timeline


Present roadmap in a structured format.

If user asks about skill gaps:

1. Extract skills from the uploaded resume.
2. Identify the target role mentioned by the user.
3. Compare resume skills with the target role requirements.
4. Show:

Current Skills
Missing Skills
Skill Match Percentage
Recommended Skills
Learning Roadmap
Projects to Build
Certifications to Pursue

5. Format the response professionally using clear headings and bullet points.
For normal tasks such as emails, applications, letters, messages, leave requests, cover letters, LinkedIn posts, or content writing:

Do not ask unnecessary follow-up questions.
Generate the requested content directly unless essential information is missing.

Only calculate ATS Score when the user explicitly asks for:
- ATS analysis
- Resume review
- Resume analysis
- Resume score

Otherwise do not show ATS Score.

ATS Score: X%
If website content is available, answer questions using the website information.

User Question:
{user_input}

Website Content:
{website_content}

Image Context:
{image_context}

Resume:
{resume_text}

Experience:
{experience}

Interview Mode:
{interview_mode}
"""

                    # ----------------------------------------------------
                    # 🖼️ FIX: UPDATED ACTIVE GROQ MODEL FOR VISION & CHAT
                    # ----------------------------------------------------
                    if uploaded_image:
                        image = Image.open(uploaded_image)
                        base64_image = image_to_base64(image)

                        response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",  # <-- UPDATED LATEST GROQ MODEL
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": combined_prompt
                                        },
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{base64_image}"
                                            }
                                        }
                                    ]
                                }
                            ]
                        )
                    else:
                        messages.append({
                            "role": "user",
                            "content": combined_prompt
                        })
                        
                        response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",  # <-- UPDATED LATEST GROQ MODEL
                            messages=messages
                        )
                    # ----------------------------------------------------

                    ai_response = response.choices[0].message.content

                    # Voice Pipeline Text-to-Speech Processing
                    audio_path = speak_text(ai_response)
                    audio_file = open(audio_path, "rb")
                    st.audio(audio_file.read(), format="audio/mp3")

                    # Custom Dashboard rendering options matching ATS rules
                    if "ATS Score" in ai_response:
                        score_match = re.search(r"ATS Score:\s*(\d+)", ai_response, re.IGNORECASE)
                        ats_score = int(score_match.group(1)) if score_match else 0

                        st.markdown("## 📊 ATS Resume Score")
                        st.progress(ats_score / 100)
                        st.markdown(f"### ✅ ATS Score: {ats_score}/100")
                        st.markdown(
                            f"""
                            <div style="
                                background: linear-gradient(135deg, #1E293B, #0F172A);
                                padding: 20px;
                                border-radius: 18px;
                                border: 1px solid #334155;
                                margin-top: 20px;
                            ">
                                <p style="color:white; white-space: pre-wrap; line-height:1.8;">
                                {ai_response}
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(ai_response)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": ai_response
                    })

                except Exception as e:
                    st.error(f"Error: {e}")
                    
# #---------------- TAB-2-----RESUME TAB ---------------- #
if menu == "📄 Resume Analysis":
    st.subheader("📄 Resume Analysis")
    if resume_text:
        st.success("Resume Loaded Successfully ✅")
        st.text_area(
            "Extracted Resume Text",
            resume_text,
            height=300
        )
    else:
        st.warning("Please upload a resume.")


# ---------------- INTERVIEW TAB ---------------- #

if menu == "🎤 Interview":
    st.subheader("🎤 AI Mock Interview")

    # Initialize Session States
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = False

    if "interview_history" not in st.session_state:
        st.session_state.interview_history = []

    # UI Options
    job_role = st.selectbox(
        "Select Job Role",
        [
            "Python Developer", "Data Scientist", "Frontend Developer", 
            "Backend Developer", "Full Stack Developer", "AI Engineer",
            "Machine Learning Engineer", "Cybersecurity Analyst", "Cloud Engineer",
            "DevOps Engineer", "UI/UX Designer", "Mobile App Developer",
            "Business Analyst", "Software Tester", "Product Manager",
            "Digital Marketer", "HR Manager", "Sales Executive",
            "Content Writer", "Graphic Designer", "Other"
        ]
    )

    custom_role = ""
    if job_role == "Other":
        custom_role = st.text_input("Enter Job Role")

    final_role = custom_role if custom_role else job_role

    difficulty = st.selectbox(
        "Difficulty",
        ["Beginner", "Intermediate", "Advanced"]
    )

    # Common function to process candidate's answer and get LLM response
    def process_user_answer(answer_text):
        if not answer_text.strip():
            return
            
        # Append User Answer to History
        st.session_state.interview_history.append({
            "role": "user",
            "content": answer_text
        })

        # System Prompt Generation
        interview_messages = [
            {
                "role": "system",
                "content": f"""
You are conducting a professional interview.
Role: {final_role}
Difficulty: {difficulty}

For every candidate answer:
1. Evaluate answer.
2. Give score out of 10.
3. Explain mistakes.
4. Give correct answer if candidate is wrong.
5. Give encouragement.
6. Ask NEXT interview question.

Format your response exactly like this:
Score: X/10

Feedback:
...

Correct Answer:
...

Next Question:
...
"""
            }
        ]
        
        # Extend with total conversation history
        interview_messages.extend(
    st.session_state.interview_history[-6:]
)

        # Get LLM Response
        with st.spinner("AI Interviewer is thinking..."):
            response = client.chat.completions.create(
             model="llama-3.1-8b-instant",
                messages=interview_messages
            )
        
        ai_feedback = response.choices[0].message.content

        # Append AI Feedback to History
        st.session_state.interview_history.append({
            "role": "assistant",
            "content": ai_feedback
        })

        # Audio Feedback (Optional voice response)
        try:
            audio_path = speak_text(ai_feedback)
            with open(audio_path, "rb") as audio_file:
                st.session_state["audio_bytes"] = audio_file.read()
        except Exception as e:
            pass

        st.rerun()


    # 🚀 START INTERVIEW TRIGGER
    if st.button("🚀 Start Interview"):
        st.session_state.interview_started = True
        
        start_prompt = f"You are an expert interviewer.\nRole: {final_role}\nDifficulty: {difficulty}\n\nAsk only ONE interview question.\nDo not provide an answer.\nWait for the candidate's response."

        with st.spinner("Generating first question..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": start_prompt}]
            )

        first_question = response.choices[0].message.content
        st.session_state.interview_history = [
            {"role": "assistant", "content": first_question}
        ]
        if "audio_bytes" in st.session_state:
            del st.session_state["audio_bytes"]
            
        st.rerun()


    # 🎭 DISPLAY CHAT & INPUTS
    if st.session_state.interview_started:
        
        # Display entire chat log cleanly
        for msg in st.session_state.interview_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Play latest audio if generated
        if "audio_bytes" in st.session_state and st.session_state["audio_bytes"]:
            st.audio(st.session_state["audio_bytes"], format="audio/mp3")

        st.markdown("---")
        st.markdown("### 🎤 Answer Question")

        # Voice Recorder
        audio = mic_recorder(
            start_prompt="🎤 Start Answer",
            stop_prompt="⏹ Stop Recording",
            key="interview_recorder"
        )

        if audio:
            # Check to see if this audio file has already been processed 
            # to prevent rerun-loops on the same voice snippet
            current_audio_bytes = audio["bytes"]
            if "last_audio_bytes" not in st.session_state or st.session_state.last_audio_bytes != current_audio_bytes:
                st.session_state.last_audio_bytes = current_audio_bytes
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
                    temp_audio.write(current_audio_bytes)
                    temp_audio_path = temp_audio.name

                with st.spinner("Transcribing your audio..."):
                    result = whisper_model.transcribe(temp_audio_path)
                    voice_answer = result["text"]

                if voice_answer.strip():
                    st.success(f"Recognized: {voice_answer}")
                    process_user_answer(voice_answer)

        # Text input alternative
        typed_answer = st.chat_input("Or type your answer here...")
        if typed_answer:
            process_user_answer(typed_answer)

        # 🛑 End Interview Button
        st.markdown(" ")
        if st.button("🛑 End Interview"):
            st.session_state.interview_started = False
            st.session_state.interview_history = []
            if "audio_bytes" in st.session_state:
                del st.session_state["audio_bytes"]
            if "last_audio_bytes" in st.session_state:
                del st.session_state["last_audio_bytes"]
            st.success("Interview Ended")
            st.rerun()


# ---------------- LOGO GENERATOR ---------------- #
if menu == "🎨 Logo Generator":

    st.subheader("🎨 AI Logo Generator")

    company_name = st.text_input(
        "Company / Brand Name"
    )

    logo_style = st.selectbox(
        "Logo Style",
        [
            "Modern",
            "Minimalist",
            "Tech",
            "Luxury",
            "Gaming",
            "Startup",
            "Corporate"
        ]
    )

    logo_colors = st.text_input(
        "Preferred Colors",
        placeholder="Blue, White"
    )

    if st.button("Generate Logo Idea"):

        prompt = f"""
Create a professional logo concept.

Company Name: {company_name}

Style: {logo_style}

Colors: {logo_colors}

Generate:
- Logo Concept
- Design Elements
- Color Strategy
- Typography
- Brand Identity
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        st.markdown(
            response.choices[0].message.content
        )

# ---------------- FOOTER ---------------- #
st.markdown("""
<div class="footer">
</div>
""", unsafe_allow_html=True)
