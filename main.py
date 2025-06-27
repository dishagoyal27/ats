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
import re
from pathlib import Path
from resume_scoring import extract_text_from_pdf, extract_text_from_docx

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

    # Extract text from resume
    try:
        if file_ext == '.pdf':
            text = extract_text_from_pdf(file_path)
        else:
            text = extract_text_from_docx(file_path)
    except Exception as e:
        raise HTTPException(500, detail=f"Error reading file: {str(e)}")

    if not text.strip():
        raise HTTPException(400, detail="Document appears to be empty")

    # Prepare DeepSeek prompt
    prompt = f"""
    Analyze this resume for ATS (Applicant Tracking System) compatibility and provide:
    1. A score from 0-100 based on ATS optimization
    2. Detailed feedback in bullet points with emojis (✓ for good, ⚠ for issues)
    3. Specific suggestions for improvement

    Resume Content:
    {text[:3000]}... [truncated for length]

    Evaluation Criteria:
    - Section completeness (Contact, Summary, Experience, Education, Skills)
    - Keyword optimization and relevance
    - Formatting and readability (bullet points, clear headings)
    - ATS-specific best practices (no tables, proper headers)
    - Quantifiable achievements
    - Appropriate length (1-2 pages)

    Return the response with the score first as "Score: XX/100" followed by bullet points.
    Include both positive aspects (✓) and areas for improvement (⚠).
    """

    # Get AI analysis
    try:
        ai_response = await query_deepseek(prompt)
        
        if not ai_response:
            raise HTTPException(500, detail="Failed to get AI analysis")

        # Parse the response
        score_match = re.search(r'Score:\s*(\d+)/100', ai_response)
        score = int(score_match.group(1)) if score_match else 50

        # Process feedback
        feedback = []
        for line in ai_response.split('\n'):
            line = line.strip()
            if line.startswith(('✓', '⚠', '-', '•', '*')) or (line and not line.startswith('Score:')):
                feedback.append(line)

        # Generate PDF report
        report_id = f"{file_id}.pdf"
        pdf_path = os.path.join(REPORT_DIR, report_id)
        generate_pdf(score, feedback, pdf_path)

        return templates.TemplateResponse("results.html", {
            "request": request,
            "score": score,
            "feedback": feedback,
            "pdf_name": report_id
        })

    except Exception as e:
        raise HTTPException(500, detail=f"Error processing resume: {str(e)}")

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