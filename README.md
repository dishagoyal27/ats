🧠 ATS Resume Scanner
A FastAPI-based web application that analyzes resumes (PDF/DOCX) for **ATS (Applicant Tracking System)** compatibility. It scores resumes, provides actionable feedback, and generates a professional PDF report — enhanced with optional AI-powered suggestions using OpenRouter's DeepSeek model.

🚀 Features
* 📄 Upload `.pdf` or `.docx` resumes
* ✅ Get an ATS score (out of 100)
* 📋 Human-readable feedback on resume quality
* 🧠 AI-generated suggestions (if API key is added)
* 📄 Download a detailed PDF report
* 🌐 Simple HTML interface using Jinja2 templates


🛠️ Tech Stack
* Backend: FastAPI
* Frontend: HTML + Jinja2 Templates
* AI API: OpenRouter DeepSeek model
* PDF Generation: ReportLab / Custom code
* Environment Management: `python-dotenv`

## 📂 Project Structure
├── main.py                  # FastAPI application  
├── resume_scoring.py        # Resume scoring logic + PDF generator  
├── templates/               # HTML templates (upload.html, results.html)  
├── static/                  # CSS/images/static assets  
├── uploads/                 # Stores uploaded resumes  
├── reports/                 # Stores generated PDF reports  
├── .env                     # Stores API keys (excluded from Git)  
├── .gitignore               # Git ignore settings  
└── README.md                # You're here!


⚙️ Installation & Setup
1. Clone the Repository

```bash
git clone https://github.com/your-username/ats-resume-scanner.git
cd ats-resume-scanner
```

 2. Create a Virtual Environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
```

 3. Install Required Packages

```bash
pip install -r requirements.txt
```

4. Add Your API Key (Optional for AI Suggestions)

Create a file named `.env` in the root folder and paste:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

If not added, the app will still work, just without AI suggestions.

---

 🧪 Running the App

Run the FastAPI server:

```bash
uvicorn main:app --reload
```

Then visit in your browser:
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

📋 Usage Instructions
1. Open the app in your browser.
2. Upload a `.pdf` or `.docx` version of your resume.
3. View your ATS score and feedback.
4. Download a detailed PDF report.
5. If the AI key is configured, you'll also receive tailored suggestions from an AI resume coach.

📌 Future Improvements
* [ ] User authentication system
* [ ] Resume comparison feature
* [ ] Better mobile UI
* [ ] Export report as DOCX
* [ ] Add AI summary + skill recommendations

✅ requirements.txt (for reference)

```txt
fastapi
jinja2
python-multipart
uvicorn
python-dotenv
httpx
reportlab
```

You can save this as `requirements.txt`.

📄 License

This project is licensed under the [MIT License](LICENSE).

---

🤛️ Author

**Made with 💙 by Disha**
Let's connect on [LinkedIn](https://www.linkedin.com) | [GitHub](https://github.com)

---
