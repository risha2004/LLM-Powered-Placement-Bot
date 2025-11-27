import os
import json
import requests
import streamlit as st
import datetime
import pdfplumber
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import firebase_admin
from firebase_admin import credentials, firestore

# === Load Environment ===
load_dotenv()

# === Firebase REST API Auth Setup ===
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts"


# === Firebase Admin Setup ===
try:
    firebase_admin.get_app()
except ValueError:
    # 1. Get the raw JSON string from the environment variable
    service_account_json = os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"]

    # 2. Parse it into a dictionary
    service_account_info = json.loads(service_account_json)

    # 3. Pass the dict directly to credentials.Certificate
    cred = credentials.Certificate(service_account_info)

    firebase_admin.initialize_app(cred)

db = firestore.client()

# === Gemini API ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# === Firebase Login/Signup ===
def signup(email, password):
    url = f"{FIREBASE_AUTH_URL}:signUp?key={FIREBASE_API_KEY}"
    response = requests.post(url, data=json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    }))
    return response.json()

def login(email, password):
    url = f"{FIREBASE_AUTH_URL}:signInWithPassword?key={FIREBASE_API_KEY}"
    response = requests.post(url, data=json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    }))
    return response.json()

def login_page():
    st.set_page_config(page_title="Login", layout="centered")
    st.title("🔐 Login to Placement Helper Bot")
    choice = st.radio("Login or Signup", ["Login", "Signup"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if choice == "Signup":
        if st.button("Create Account"):
            res = signup(email, password)
            if "idToken" in res:
                st.success("Account created! Please login.")
            else:
                st.error(res.get("error", {}).get("message", "Signup failed."))
    else:
        if st.button("Login"):
            res = login(email, password)
            # === After successful login ===
            if "idToken" in res:
                st.session_state.user = res
                st.session_state.user_id = res["email"]
                user_id = res["email"]

                # 🔄 Load saved user data from Firestore
                doc_ref = db.collection("users").document(user_id)
                doc = doc_ref.get()

                if doc.exists:
                    user_data = doc.to_dict()
                    for key in ["chat_log", "chat_history", "placement_calendar", "completed_companies"]:
                        if key not in st.session_state:
                            st.session_state[key] = {}
                        st.session_state[key][user_id] = user_data.get(key, {})
                else:
                    # First time login fallback
                    for key in ["chat_log", "chat_history", "placement_calendar", "completed_companies"]:
                        if key not in st.session_state:
                            st.session_state[key] = {}
                        st.session_state[key][user_id] = {}

                st.experimental_rerun()
            else:
                st.error(res.get("error", {}).get("message", "Login failed."))

# === Require Login ===
if "user" not in st.session_state:
    login_page()
    st.stop()

user_id = st.session_state.user_id

# === Session State Defaults ===
for key in ["chat_log", "chat_history", "placement_calendar", "completed_companies"]:
    if key not in st.session_state:
        st.session_state[key] = {}
    if user_id not in st.session_state[key]:
        st.session_state[key][user_id] = {}

# === Helper for text/file input ===
def get_text_from_input(label_prefix):
    upload = st.file_uploader(f"{label_prefix} Upload (PDF or TXT)", type=["pdf", "txt"], key=label_prefix)
    text = ""
    if upload:
        if upload.type == "application/pdf":
            with pdfplumber.open(upload) as pdf:
                text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        elif upload.type == "text/plain":
            text = upload.read().decode("utf-8")
    else:
        text = st.text_area(f"Or paste {label_prefix.lower()} here")
    return text

# === Main UI ===
st.set_page_config(page_title="📚 Placement Helper Bot", page_icon="🎓", layout="wide")
st.title("🎓 Placement Helper Bot")

mode = st.sidebar.radio("Select Tool", [
    "💬 Chat with Gemini",
    "📑 Resume vs JD Comparator",
    "📋 ATS Score & Feedback",
    "📄 Cover Letter Generator",
    "📆 Placement Calendar",
    "🧠 Aptitude Practice Generator",
])

if "current_session" not in st.session_state:
    st.session_state.current_session = datetime.datetime.now().strftime("Session %Y-%m-%d %H:%M:%S")

if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.experimental_rerun()

# === Tool 1: Chat with Gemini ===
if mode == "💬 Chat with Gemini":
    st.subheader("💬 Chat with Gemini")
    if "chat" not in st.session_state:
        model = genai.GenerativeModel("gemini-2.5-flash")
        st.session_state.chat = model.start_chat(history=[])

    for msg in st.session_state.chat.history:
        with st.chat_message(msg.role):
            st.markdown(msg.parts[0].text)

    user_prompt = st.chat_input("Ask anything...")
    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        try:
            response = st.session_state.chat.send_message(user_prompt)
            reply = response.text
            st.chat_message("assistant").markdown(reply)
            session = st.session_state.current_session
            st.session_state.chat_log[user_id].setdefault(session, []).append({"role": "user", "content": user_prompt})
            st.session_state.chat_log[user_id][session].append({"role": "model", "content": reply})
            st.session_state.chat_history[user_id][session] = list(st.session_state.chat_log[user_id][session])

            # Save chat log to Firestore
            db.collection("users").document(user_id).set({"chat_history": st.session_state.chat_history[user_id]}, merge=True)
        except ResourceExhausted:
            st.error("⚠️ Gemini quota exhausted. Try again later.")
        except Exception as e:
            st.error("🚨 Error: " + str(e))

elif mode == "📑 Resume vs JD Comparator":
    st.subheader("📑 Resume vs Job Description Comparator")
    resume_text = get_text_from_input("Resume")
    jd_text = get_text_from_input("Job Description")
    if st.button("Compare") and resume_text and jd_text:
        model = genai.GenerativeModel("gemini-2.5-flash")
        chat = model.start_chat()
        with st.spinner("Analyzing Resume vs JD..."):
            prompt = f"Compare the following resume and job description. Highlight strengths, gaps, and suggestions.\n\nResume:\n{resume_text}\n\nJob Description:\n{jd_text}"
            response = chat.send_message(prompt)
            st.markdown(response.text)
            db.collection("users").document(user_id).set({"last_comparator_result": response.text}, merge=True)

elif mode == "📋 ATS Score & Feedback":
    st.subheader("📋 ATS Checker")
    resume_text = get_text_from_input("Resume")
    jd_text = get_text_from_input("Job Description")
    if st.button("Check ATS Compatibility") and resume_text and jd_text:
        model = genai.GenerativeModel("gemini-2.5-flash")
        chat = model.start_chat()
        with st.spinner("Scoring Resume for ATS..."):
            prompt = f"Give an ATS compatibility score out of 100 for the resume below when matched with the job description. Explain the score and provide improvements.\n\nResume:\n{resume_text}\n\nJob Description:\n{jd_text}"
            response = chat.send_message(prompt)
            st.markdown(response.text)
            db.collection("users").document(user_id).set({"last_ats_result": response.text}, merge=True)

elif mode == "📄 Cover Letter Generator":
    st.subheader("📄 Generate Cover Letter")
    resume_text = get_text_from_input("Resume")
    jd_text = get_text_from_input("Job Description")
    if st.button("Generate Cover Letter") and resume_text and jd_text:
        model = genai.GenerativeModel("gemini-2.5-flash")
        chat = model.start_chat()
        with st.spinner("Creating cover letter..."):
            prompt = f"Write a professional cover letter based on the resume and job description below.\n\nResume:\n{resume_text}\n\nJob Description:\n{jd_text}"
            response = chat.send_message(prompt)
            st.markdown(response.text)
            db.collection("users").document(user_id).set({"last_cover_letter": response.text}, merge=True)

elif mode == "📆 Placement Calendar":
    st.subheader("📆 Add or View Placement Calendar")
    date = st.date_input("📅 Select date")
    company = st.text_input("🏢 Company name")

    if st.button("➕ Add to Calendar") and company:
        key = date.isoformat()
        if key not in st.session_state.placement_calendar[user_id]:
            st.session_state.placement_calendar[user_id][key] = []

        if company in st.session_state.placement_calendar[user_id][key]:
            st.warning(f"⚠️ '{company}' is already added for {date}.")
        else:
            st.session_state.placement_calendar[user_id][key].append(company)
            st.success(f"✅ Added '{company}' to {date}.")

    st.markdown("---")
    st.subheader("🗓️ Placement Schedule")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔜 Yet to Come")
        for date, jobs in sorted(st.session_state.placement_calendar[user_id].items()):
            for i, job in enumerate(jobs.copy()):
                if job not in st.session_state.completed_companies[user_id].get(date, []):
                    key = f"{date}_{job}_{i}_checkbox"  # ✅ make checkbox key unique
                    if st.checkbox(f"{job} ({date})", key=key):
                        st.session_state.completed_companies[user_id].setdefault(date, []).append(job)
                        st.session_state.placement_calendar[user_id][date].remove(job)
                        if not st.session_state.placement_calendar[user_id][date]:
                            del st.session_state.placement_calendar[user_id][date]
                        db.collection("users").document(user_id).set({
                            "completed_companies": st.session_state.completed_companies[user_id],
                            "placement_calendar": st.session_state.placement_calendar[user_id]
                        }, merge=True)
                        st.experimental_rerun()

    with col2:
        st.markdown("### ✅ Completed")
        for date, jobs in sorted(st.session_state.completed_companies[user_id].items()):
            for job in jobs:
                st.markdown(f"- {job} ({date})")

elif mode == "🧠 Aptitude Practice Generator":
    st.subheader("🧠 Aptitude Question Generator")
    topic = st.selectbox("Choose a topic", [
        "Quant - Profit & Loss", "Quant - Time & Work", "Quant - SI & CI", "Quant - Percentages",
        "Quant - Averages", "Quant - Number System", "Quant - Time Speed Distance",
        "Logical - Blood Relations", "Logical - Direction Sense", "Logical - Puzzles", "Logical - Syllogism",
        "Verbal - Synonyms", "Verbal - RC", "Verbal - Sentence Correction", "Verbal - Para Jumbles"
    ])
    num = st.slider("Number of questions", min_value=5, max_value=60, value=10)
    if st.button("📚 Generate Questions"):
        prompt = f"Generate {num} aptitude questions from the topic: {topic} with options and detailed solutions."
        model = genai.GenerativeModel("gemini-2.5-flash")
        chat = model.start_chat()
        with st.spinner("Creating practice set..."):
            response = chat.send_message(prompt)
            st.markdown(response.text)
            db.collection("users").document(user_id).set({"last_aptitude_result": response.text}, merge=True)
db.collection("users").document(user_id).set({
    "placement_calendar": st.session_state.placement_calendar[user_id],
    "completed_companies": st.session_state.completed_companies[user_id],
    "chat_log": st.session_state.chat_log[user_id],
    "chat_history": st.session_state.chat_history[user_id]
}, merge=True)
# === Sidebar History ===
st.sidebar.markdown("---")
st.sidebar.subheader("🕒 Chat History")
for name in st.session_state.chat_history[user_id]:
    if st.sidebar.button(name):
        st.session_state.chat_log[user_id] = {name: st.session_state.chat_history[user_id][name]}
        model = genai.GenerativeModel("gemini-2.5-flash")
        st.session_state.chat = model.start_chat(history=[{"role": m["role"], "parts": [m["content"]]} for m in st.session_state.chat_log[user_id][name]])
        st.session_state.current_session = name
        st.rerun()
