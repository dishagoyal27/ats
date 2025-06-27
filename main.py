from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from resume_scoring import score_resume, generate_pdf
import os
import shutil
import uuid
from dotenv import load_dotenv
import httpx
from pathlib import Path
from typing import Optional

# Load API key
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_ID = "deepseek/deepseek-r1-0528:free"

app = FastAPI(title="ATS Resume Scanner", 
              description="Analyze your resume's ATS compatibility")

# Static + Template setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Ensure folders exist
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"
Path(UPLOAD_DIR).mkdir(exist_ok=True)
Path(REPORT_DIR).mkdir(exist_ok=True)

# Query OpenRouter DeepSeek model
async def query_deepseek(prompt: str) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return None
        
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "You are a professional resume coach. Provide concise, actionable suggestions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions", 
                headers=headers, 
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error querying AI: {str(e)}")
        return None

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def handle_upload(request: Request, file: UploadFile = File(...)):
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.pdf', '.docx']:
        raise HTTPException(400, detail="Only PDF and DOCX files are allowed")

    # Save file
    file_id = uuid.uuid4().hex
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(500, detail=f"Error saving file: {str(e)}")

    # Score resume
    try:
        score, feedback = score_resume(file_path)
    except Exception as e:
        raise HTTPException(500, detail=f"Error analyzing resume: {str(e)}")

    # Get AI feedback if API key is available
    ai_feedback = None
    if OPENROUTER_API_KEY:
        ai_prompt = (
            f"Resume scored {score}/100 on ATS compatibility. "
            f"Here are the key sections found: {feedback[:3]}. "
            "Provide 3-5 concise bullet points for improvement."
        )
        try:
            ai_feedback = await query_deepseek(ai_prompt)
            if ai_feedback:
                feedback.append("\n🧠 AI Suggestions:\n" + ai_feedback)
        except Exception as e:
            feedback.append("\n⚠ Could not fetch AI suggestions")

    # Generate PDF report
    report_id = f"{file_id}.pdf"
    pdf_path = os.path.join(REPORT_DIR, report_id)
    try:
        generate_pdf(score, feedback, pdf_path)
    except Exception as e:
        raise HTTPException(500, detail=f"Error generating report: {str(e)}")

    return templates.TemplateResponse("results.html", {
        "request": request,
        "score": score,
        "feedback": feedback,
        "pdf_name": report_id
    })

@app.get("/download/{pdf_name}")
async def download_report(pdf_name: str):
    pdf_path = os.path.join(REPORT_DIR, pdf_name)
    if not os.path.exists(pdf_path):
        raise HTTPException(404, detail="Report not found")
    return FileResponse(
        path=pdf_path,
        filename="ATS_Resume_Report.pdf",
        media_type='application/pdf'
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8019, reload=True)