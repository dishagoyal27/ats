import pdfplumber
import docx
import os
import re
from fpdf import FPDF
from typing import Tuple, List, Dict
from collections import defaultdict

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF files with error handling"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        text = re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")
    return text

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX files with formatting hints"""
    try:
        doc = docx.Document(file_path)
        return "\n".join(para.text.strip() for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        raise Exception(f"DOCX extraction failed: {str(e)}")

def clean_text_for_pdf(text: str) -> str:
    """Convert special characters to ASCII-friendly equivalents"""
    char_map = {
        '✓': '[PASS]', '⚠': '[WARN]', '🧠': '[AI]',
        '→': '->', '•': '-', '–': '-', '—': '-',
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '👍': '[GOOD]', '👎': '[BAD]', '⭐': '[STAR]',
        '…': '...', '£': 'GBP', '€': 'EUR', '°': 'deg'
    }
    for char, replacement in char_map.items():
        text = text.replace(char, replacement)
    return text.encode('ascii', 'ignore').decode('ascii')

def analyze_sections(text: str) -> Dict[str, str]:
    """Identify resume sections with robust pattern matching"""
    patterns = {
        'contact': r'(contact|personal\s*details)',
        'summary': r'(summary|profile|objective)',
        'experience': r'(experience|work\s*history)',
        'education': r'(education|academic)',
        'skills': r'(skills|technical\s*skills)',
        'projects': r'(projects|portfolio)',
        'certifications': r'(certifications|licenses)',
        'achievements': r'(achievements|awards)'
    }
    
    sections = {}
    for section, pattern in patterns.items():
        match = re.search(rf'(?i)\b{pattern}\b[:\s]*\n(.+?)(?=\n\b\w+\b[:\s]*\n|\Z)', 
                         text, re.DOTALL)
        if match:
            sections[section] = match.group(1).strip()
    return sections

def score_sections(sections: Dict[str, str]) -> Tuple[int, List[str]]:
    """Score resume sections with weighted evaluation"""
    weights = {
        'contact': 15, 'summary': 10, 'experience': 25,
        'education': 15, 'skills': 15, 'projects': 10,
        'certifications': 5, 'achievements': 5
    }
    
    score = 0
    feedback = []
    for section, weight in weights.items():
        if section in sections:
            content = sections[section]
            score += weight
            quality = min(len(content.split())//10, weight//5)
            score += quality
            feedback.append(
                f"✓ {section.title()} section (+{weight+quality} points): "
                f"{content[:50]}{'...' if len(content)>50 else ''}"
            )
        else:
            feedback.append(f"⚠ Missing {section} section (-{weight} potential points)")
    
    return min(score, 40), feedback  # Section score capped at 40

def analyze_keywords(text: str, job_title: str = None) -> Tuple[int, List[str]]:
    """Analyze keywords with job-specific scoring"""
    keyword_groups = {
        'technical': ["python", "java", "sql", "javascript", "c++", "git"],
        'soft': ["communication", "teamwork", "leadership"],
        'tools': ["docker", "aws", "linux"]
    }
    
    if job_title and 'data' in job_title.lower():
        keyword_groups['technical'].extend(["pandas", "numpy", "tensorflow"])
    
    score = 0
    feedback = []
    text_lower = text.lower()
    
    for category, keywords in keyword_groups.items():
        found = [kw for kw in keywords if re.search(rf'\b{kw}\b', text_lower)]
        points = len(found) * 2
        score += points
        if found:
            feedback.append(f"✓ Found {len(found)} {category} keywords (+{points} points)")
        else:
            feedback.append(f"⚠ Missing {category} keywords")
    
    return min(score, 30), feedback  # Keyword score capped at 30

def analyze_formatting(text: str) -> Tuple[int, List[str]]:
    """Evaluate resume formatting quality"""
    score = 0
    feedback = []
    
    # Bullet points scoring
    bullets = text.count('•') + text.count('- ')
    if bullets > 5:
        score += 10
        feedback.append("✓ Excellent bullet point usage (+10 points)")
    elif bullets > 0:
        score += 5
        feedback.append("✓ Some bullet points used (+5 points)")
    else:
        feedback.append("⚠ Needs bullet points for readability")
    
    # Length scoring
    words = len(text.split())
    if 400 <= words <= 600:
        score += 10
        feedback.append(f"✓ Ideal length ({words} words, +10 points)")
    elif words > 800:
        feedback.append(f"⚠ Too long ({words} words, consider shortening)")
    
    return min(score, 20), feedback  # Formatting score capped at 20

def check_ats_compatibility(text: str) -> Tuple[int, List[str]]:
    """Check ATS-specific requirements"""
    score = 0
    feedback = []
    
    # Contact info check
    has_email = bool(re.search(r'\S+@\S+\.\S+', text))
    has_phone = bool(re.search(r'(\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]?\d{4})', text))
    
    if has_email and has_phone:
        score += 10
        feedback.append("✓ Complete contact information (+10 points)")
    elif has_email or has_phone:
        score += 5
        feedback.append("✓ Partial contact information (+5 points)")
    else:
        feedback.append("⚠ Missing contact information")
    
    # Name formatting check
    if re.search(r'^[A-Z][a-z]+ [A-Z][a-z]+$', text.split('\n')[0]):
        score += 5
        feedback.append("✓ Proper name formatting (+5 points)")
    
    return min(score, 15), feedback  # ATS score capped at 15

def generate_pdf(score: int, feedback: List[str], path: str) -> None:
    """Generate PDF report with Unicode character handling"""
    pdf = FPDF()
    pdf.add_page()
    
    # Clean feedback text
    clean_feedback = [clean_text_for_pdf(item) for item in feedback]
    
    # Header
    pdf.set_fill_color(59, 89, 152)
    pdf.rect(0, 0, 210, 25, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 25, "ATS Resume Evaluation Report", 0, 1, 'C')
    
    # Score display
    pdf.set_text_color(0)
    pdf.ln(10)
    color = (0, 128, 0) if score >= 70 else (255, 165, 0) if score >= 50 else (255, 0, 0)
    pdf.set_font('Arial', 'B', 36)
    pdf.set_text_color(*color)
    pdf.cell(0, 20, f"{score}/100", 0, 1, 'C')
    
    # Score visualization
    pdf.set_draw_color(200)
    pdf.rect(30, pdf.get_y(), 150, 10, 'D')
    pdf.set_fill_color(*color)
    pdf.rect(30, pdf.get_y(), 150*(score/100), 10, 'F')
    pdf.ln(20)
    
    # Feedback section
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(59, 89, 152)
    pdf.cell(0, 10, "Detailed Feedback:", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    pdf.set_font('Arial', '', 10)
    for item in clean_feedback:
        if '[PASS]' in item or '[GOOD]' in item:
            pdf.set_text_color(0, 128, 0)
        elif '[WARN]' in item or '[BAD]' in item:
            pdf.set_text_color(255, 165, 0)
        else:
            pdf.set_text_color(0)
        pdf.multi_cell(0, 6, item)
        pdf.ln(2)
    
    # Footer
    pdf.set_y(-15)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(150)
    pdf.cell(0, 10, "Generated by ATS Resume Scanner", 0, 0, 'C')
    pdf.output(path)

def score_resume(file_path: str, job_title: str = None) -> Tuple[int, List[str]]:
    """Main function to analyze and score a resume"""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        text = extract_text_from_pdf(file_path) if ext == '.pdf' else extract_text_from_docx(file_path)
        
        if not text.strip():
            return 0, ["Error: Empty document or failed text extraction"]
        
        sections = analyze_sections(text)
        section_score, section_fb = score_sections(sections)
        keyword_score, keyword_fb = analyze_keywords(text, job_title)
        format_score, format_fb = analyze_formatting(text)
        ats_score, ats_fb = check_ats_compatibility(text)
        
        total_score = min(section_score + keyword_score + format_score + ats_score, 100)
        all_feedback = section_fb + keyword_fb + format_fb + ats_fb
        
        # Add overall assessment
        if total_score >= 80:
            all_feedback.append("🧠 AI: Excellent ATS optimization")
        elif total_score >= 60:
            all_feedback.append("🧠 AI: Good but could be improved")
        else:
            all_feedback.append("🧠 AI: Needs significant improvements")
        
        return total_score, all_feedback
        
    except Exception as e:
        return 0, [f"Error processing resume: {str(e)}"]