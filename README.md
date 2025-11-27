# LLM-Powered-Placement-Bot

An intelligent, AI-powered chatbot designed to assist students with resume tailoring, job matching, aptitude preparation, and career guidance. Built using Google Gemini API, Streamlit, and Firebase, this tool offers personalized support for students preparing for placements and internships.

---

## 🚀 Features

- ✅ **Resume vs Job Description Comparator**  
- ✉️ **Cover Letter Generator**  
- 📊 **ATS Optimization Tips**  
- 📅 **Placement Calendar** *(Coming Soon)*  
- 🧠 **Aptitude Prep Generator** *(Coming Soon)*  
- 🗣️ **Voice Input & Output** *(Planned)*  
- 📎 **PDF/Text Upload**  
- 🔐 **User Authentication via Firebase**

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit  
- **AI Engine:** Google Gemini API  
- **Auth & Database:** Firebase Auth + Firestore (Firebase Admin SDK)  
- **OCR (Planned):** pdfplumber  
- **Deployment:** Render

---

## 📂 Folder Structure

ai_chatbot/
├── .venv/                     # Virtual environment (not committed)
├── src/                       # Source code
│   ├── main.py                # Streamlit app entry point
│   ├── utils/                 # Utility modules
│   │   ├── firebase.py        # Firebase admin setup
│   │   ├── gemini.py          # Google Gemini API interaction
│   │   └── parser.py          # Resume/Job parsing utilities
├── requirements.txt           # Python dependencies
├── README.md                  # Project README
└── .env                       # Environment variables (not committed)

## 🧪 Setup Instructions

### 1. Clone the Repository

git clone https://github.com/your-username/ai-placement-helper.git
cd ai-placement-helper

### 2. Create environment
python3 -m venv .venv
source .venv/bin/activate

### 3. Create requirements file
pip install -r requirements.txt

###4. Assign API Key
GOOGLE_APPLICATION_CREDENTIALS_JSON=<your Firebase JSON string>
GEMINI_API_KEY=<your Gemini API Key>

### 5. Render the App
streamlit run src/main.py


