import pdfplumber  # Alternative to PyMuPDF
import docx
import os
import re
from fpdf import FPDF
from typing import Tuple, List, Dict
from collections import defaultdict

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text content from PDF file using pdfplumber"""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        # Clean up common extraction artifacts
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII chars
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Extract text content from DOCX file with improved formatting."""
    try:
        doc = docx.Document(file_path)
        full_text = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Preserve some formatting cues
                if para.style.name.lower() in ['heading 1', 'heading 2', 'heading 3']:
                    text = f"\nSECTION: {text.upper()}\n"
                elif para.style.name.lower() == 'list paragraph':
                    text = f"• {text}"
                full_text.append(text)
                
        return "\n".join(full_text)
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {str(e)}")

def analyze_sections(text: str) -> Dict[str, str]:
    """Identify and extract resume sections with improved heuristics."""
    section_patterns = {
        'contact': r'(contact\s*info|personal\s*details?|info\s*rmation)',
        'summary': r'(summary|profile|about\s*me|objective)',
        'experience': r'(experience|work\s*history|employment\s*history)',
        'education': r'(education|academic\s*background|qualifications)',
        'skills': r'(skills|technical\s*skills|competencies)',
        'projects': r'(projects|key\s*projects)',
        'certifications': r'(certifications|licenses)',
        'achievements': r'(achievements|awards|honors)'
    }
    
    sections = {}
    text_lower = text.lower()
    lines = text.split('\n')
    
    # First pass: look for section headers
    for section, pattern in section_patterns.items():
        match = re.search(rf'\n\s*{pattern}[:\s]*\n', text_lower, re.IGNORECASE)
        if match:
            start_pos = match.end()
            # Find where this section ends (next section starts)
            end_pos = len(text)
            for other_section, other_pattern in section_patterns.items():
                if other_section != section:
                    other_match = re.search(rf'\n\s*{other_pattern}[:\s]*\n', text_lower[start_pos:], re.IGNORECASE)
                    if other_match and other_match.start() < end_pos:
                        end_pos = other_match.start()
            
            sections[section] = text[start_pos:start_pos+end_pos].strip()
    
    # Second pass: for missing sections, try to infer content
    if 'experience' not in sections:
        # Look for job title patterns and dates
        exp_text = []
        for line in lines:
            if re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{4}', line.lower()):
                exp_text.append(line)
        if exp_text:
            sections['experience'] = '\n'.join(exp_text)
    
    if 'education' not in sections:
        # Look for degree patterns
        edu_text = []
        for line in lines:
            if re.search(r'(b\.?a\.?|b\.?s\.?|m\.?a\.?|m\.?s\.?|ph\.?d|bach|master|doctor)', line.lower()):
                edu_text.append(line)
        if edu_text:
            sections['education'] = '\n'.join(edu_text)
    
    return sections

def score_sections(sections: Dict[str, str]) -> Tuple[int, List[str]]:
    """Score resume sections with more nuanced criteria."""
    score = 0
    feedback = []
    section_weights = {
        'contact': (15, "Contact Information"),
        'summary': (10, "Professional Summary"),
        'experience': (25, "Work Experience"),
        'education': (15, "Education"),
        'skills': (15, "Skills Section"),
        'projects': (10, "Projects"),
        'certifications': (5, "Certifications"),
        'achievements': (5, "Achievements")
    }
    
    # Check for presence and quality of each section
    for section, (weight, display_name) in section_weights.items():
        if section in sections:
            content = sections[section]
            # Basic scoring for presence
            base_points = weight * 0.6  # 60% for just having the section
            
            # Quality scoring based on content length and structure
            quality_points = 0
            line_count = len(content.split('\n'))
            word_count = len(content.split())
            
            if section == 'experience':
                if word_count > 100:
                    quality_points = weight * 0.4  # Full points for detailed experience
                    feedback.append(f"✓ Excellent {display_name} section (+{weight} points)")
                elif word_count > 50:
                    quality_points = weight * 0.3
                    feedback.append(f"✓ Good {display_name} section (+{int(weight*0.9)} points)")
                else:
                    quality_points = weight * 0.2
                    feedback.append(f"⚠ {display_name} section is somewhat brief (+{int(weight*0.8)} points)")
                
                # Bonus for quantifiable achievements
                numbers = sum(c.isdigit() for c in content)
                if numbers >= 3:
                    score += 5
                    feedback.append("   ✓ Includes quantifiable achievements (+5 points)")
                    
            elif section == 'skills':
                # Check for skills organization
                bullets = content.count('•') + content.count('-')
                if bullets >= 5:
                    quality_points = weight * 0.4
                    feedback.append(f"✓ Well-organized {display_name} with bullet points (+{weight} points)")
                else:
                    quality_points = weight * 0.3
                    feedback.append(f"✓ {display_name} present but could be better organized (+{int(weight*0.9)} points)")
                
                # Bonus for technical skills categorization
                if ':' in content or '•' in content:
                    score += 3
                    feedback.append("   ✓ Skills are categorized (+3 points)")
            
            else:
                # Default quality scoring for other sections
                if word_count > 30 or line_count > 3:
                    quality_points = weight * 0.4
                    feedback.append(f"✓ Comprehensive {display_name} section (+{weight} points)")
                else:
                    quality_points = weight * 0.3
                    feedback.append(f"✓ {display_name} section present but brief (+{int(weight*0.9)} points)")
            
            score += base_points + quality_points
        else:
            feedback.append(f"⚠ Missing {display_name} section (could add {weight} points)")
    
    return score, feedback

def analyze_keywords(text: str, job_title: str = None) -> Tuple[int, List[str]]:
    """Analyze keywords with job-specific relevance scoring."""
    # Define keyword categories with weights
    keyword_categories = {
        'technical': {
            'keywords': ["python", "java", "sql", "javascript", "c++", "git", "html", 
                        "css", "react", "node.js", "machine learning", "docker", "aws"],
            'weight': 1.5
        },
        'soft': {
            'keywords': ["teamwork", "communication", "leadership", "problem solving",
                        "critical thinking", "adaptability", "time management"],
            'weight': 1.0
        },
        'tools': {
            'keywords': ["docker", "aws", "jenkins", "kubernetes", "azure",
                        "gcp", "linux", "windows", "github", "gitlab"],
            'weight': 1.2
        },
        'methodologies': {
            'keywords': ["agile", "scrum", "kanban", "devops", "ci/cd", 
                         "test driven development", "object oriented programming"],
            'weight': 1.3
        }
    }
    
    # Job-specific keyword additions
    if job_title:
        job_title = job_title.lower()
        if 'developer' in job_title:
            keyword_categories['technical']['keywords'].extend(["debugging", "frameworks", "apis"])
        elif 'manager' in job_title:
            keyword_categories['soft']['keywords'].extend(["budgeting", "strategic planning", "team building"])
        elif 'data' in job_title:
            keyword_categories['technical']['keywords'].extend(["pandas", "numpy", "tensorflow", "pytorch"])
    
    text_lower = text.lower()
    score = 0
    feedback = []
    found_keywords = defaultdict(list)
    
    for category, data in keyword_categories.items():
        keywords_found = [kw for kw in data['keywords'] if re.search(rf'\b{kw}\b', text_lower)]
        if keywords_found:
            category_score = len(keywords_found) * data['weight']
            score += category_score
            found_keywords[category] = keywords_found
            feedback.append(
                f"✓ Found {len(keywords_found)} {category} keywords: " +
                f"{', '.join(keywords_found[:3])}" +
                ("..." if len(keywords_found) > 3 else "") +
                f" (+{int(category_score)} points)"
            )
        else:
            feedback.append(f"⚠ Missing {category} keywords (e.g.: {', '.join(data['keywords'][:3])})")
    
    # Cap keyword score at 25 to prevent over-weighting
    keyword_score = min(25, score)
    
    # Bonus for keyword density (3-5% is ideal)
    total_words = len(text.split())
    if total_words > 0:
        keyword_density = sum(len(v) for v in found_keywords.values()) / total_words
        if 0.03 <= keyword_density <= 0.05:
            keyword_score += 5
            feedback.append("✓ Ideal keyword density (+5 points)")
        elif keyword_density > 0.05:
            feedback.append("⚠ Too many keywords (may appear as keyword stuffing)")
        else:
            feedback.append("⚠ Low keyword density (consider adding more relevant keywords)")
    
    return keyword_score, feedback

def analyze_formatting(text: str) -> Tuple[int, List[str]]:
    """Analyze resume formatting and structure."""
    score = 0
    feedback = []
    
    # Check for clear section headings
    heading_formats = [
        r'\b[A-Z][A-Z\s]+\b',  # ALL CAPS headings
        r'\b[A-Z][a-z]+\b\s*:\s*\n',  # Title: format
        r'\n\s*[•\-*]\s*[A-Z][a-z]+',  # Bullet points
    ]
    
    heading_count = sum(
        1 for pattern in heading_formats 
        if re.search(pattern, text)
    )
    
    if heading_count >= 4:
        score += 10
        feedback.append("✓ Clear section headings (+10 points)")
    elif heading_count >= 2:
        score += 5
        feedback.append("✓ Some clear headings (+5 points)")
    else:
        feedback.append("⚠ Missing clear section headings (use ALL CAPS or 'Section:' format)")
    
    # Check for bullet points
    bullet_points = text.count('•') + text.count('- ') + text.count('* ')
    if bullet_points > 5:
        score += 10
        feedback.append("✓ Good use of bullet points (+10 points)")
    elif bullet_points > 2:
        score += 5
        feedback.append("✓ Some bullet points used (+5 points)")
    else:
        feedback.append("⚠ Needs more bullet points for readability")
    
    # Check for consistent dates
    date_formats = [
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',
        r'\b\d{1,2}/\d{4}\b',
        r'\b\d{4}\b'
    ]
    
    dates_found = sum(
        len(re.findall(pattern, text)) 
        for pattern in date_formats
    )
    
    if dates_found >= 3:
        consistent_formats = len(set(
            pattern 
            for pattern in date_formats 
            if re.search(pattern, text)
        ))
        if consistent_formats == 1:
            score += 5
            feedback.append("✓ Consistent date formatting (+5 points)")
        else:
            feedback.append("⚠ Inconsistent date formatting (stick to one format)")
    
    # Check length
    word_count = len(text.split())
    if 400 <= word_count <= 600:
        score += 10
        feedback.append(f"✓ Ideal length ({word_count} words, +10 points)")
    elif 300 <= word_count < 400 or 600 < word_count <= 800:
        score += 5
        feedback.append(f"✓ Acceptable length ({word_count} words, +5 points)")
    elif word_count < 300:
        score -= 5
        feedback.append(f"⚠ Too short ({word_count} words, -5 points)")
    else:
        feedback.append(f"⚠ Too long ({word_count} words, consider shortening)")
    
    return score, feedback

def check_ats_compatibility(text: str) -> Tuple[int, List[str]]:
    """Check for ATS-specific compatibility factors."""
    score = 0
    feedback = []
    
    # Check for contact info
    contact_info_score = 0
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        contact_info_score += 5
    if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
        contact_info_score += 5
    if re.search(r'\bhttps?://(?:www\.)?linkedin\.com/\S+\b', text, re.IGNORECASE):
        contact_info_score += 3
    if re.search(r'\bhttps?://(?:www\.)?github\.com/\S+\b', text, re.IGNORECASE):
        contact_info_score += 2
    
    if contact_info_score >= 10:
        feedback.append(f"✓ Complete contact information (+{contact_info_score} points)")
    elif contact_info_score >= 5:
        feedback.append(f"✓ Basic contact information (+{contact_info_score} points)")
    else:
        feedback.append("⚠ Missing essential contact information")
    score += contact_info_score
    
    # Check for tables (which can confuse ATS)
    if re.search(r'\b(table|row|column)\b', text.lower()):
        score -= 5
        feedback.append("⚠ Tables detected (may not parse well in ATS, -5 points)")
    
    # Check for headers/footers
    if re.search(r'\b(page \d+ of \d+|confidential)\b', text.lower()):
        score -= 3
        feedback.append("⚠ Header/footer detected (may interfere with ATS, -3 points)")
    
    # Check for proper name formatting
    if re.search(r'^\s*[A-Z][a-z]+ [A-Z][a-z]+\s*$', text.split('\n')[0]):
        score += 3
        feedback.append("✓ Name prominently displayed (+3 points)")
    
    return score, feedback

def score_resume(file_path: str, job_title: str = None) -> Tuple[int, List[str]]:
    """Score a resume with ATS-compatible criteria."""
    # Get file extension
    ext = os.path.splitext(file_path)[1].lower()
    
    # Extract text based on file type
    try:
        if ext == '.pdf':
            text = extract_text_from_pdf(file_path)
        elif ext == '.docx':
            text = extract_text_from_docx(file_path)
        else:
            return 0, ["Unsupported file format. Please upload PDF or DOCX."]
    except Exception as e:
        return 0, [f"Error reading file: {str(e)}"]
    
    if not text.strip():
        return 0, ["Document appears to be empty or couldn't extract text"]
    
    total_score = 0
    all_feedback = []
    
    # Analyze sections
    sections = analyze_sections(text)
    section_score, section_feedback = score_sections(sections)
    total_score += section_score
    all_feedback.extend(section_feedback)
    
    # Analyze keywords
    keyword_score, keyword_feedback = analyze_keywords(text, job_title)
    total_score += keyword_score
    all_feedback.extend(keyword_feedback)
    
    # Analyze formatting
    format_score, format_feedback = analyze_formatting(text)
    total_score += format_score
    all_feedback.extend(format_feedback)
    
    # Check ATS compatibility
    ats_score, ats_feedback = check_ats_compatibility(text)
    total_score += ats_score
    all_feedback.extend(ats_feedback)
    
    # Ensure score is between 0-100
    total_score = max(0, min(100, total_score))
    
    # Add overall assessment with more nuanced suggestions
    if total_score >= 85:
        assessment = (
            "\n🧠 AI Suggestion: Excellent resume! Well-optimized for ATS systems. "
            "Consider tailoring for specific job descriptions to maximize impact."
        )
    elif total_score >= 70:
        assessment = (
            "\n🧠 AI Suggestion: Good resume that should pass most ATS systems. "
            "Focus on adding more quantifiable achievements and ensuring keyword "
            "alignment with target job descriptions."
        )
    elif total_score >= 50:
        assessment = (
            "\n🧠 AI Suggestion: Resume needs improvements for better ATS performance. "
            "Add missing sections, increase keyword density, and improve formatting. "
            "Consider using a simpler template if currently using columns/tables."
        )
    else:
        assessment = (
            "\n🧠 AI Suggestion: Significant improvements needed. The resume is unlikely "
            "to perform well in ATS systems. Consider a complete rewrite using a "
            "single-column format with clear headings and bullet points."
        )
    
    all_feedback.append(assessment)
    
    return int(total_score), all_feedback

def generate_pdf(score: int, feedback: List[str], path: str) -> None:
    """Generate PDF report with improved formatting and Unicode support."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header with colored background
    pdf.set_fill_color(59, 89, 152)  # Dark blue
    pdf.rect(0, 0, 210, 25, style='F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 25, txt="ATS Resume Evaluation Report", ln=True, align='C')
    
    # Score display
    pdf.set_text_color(0, 0, 0)
    pdf.ln(15)
    
    # Determine score color
    if score >= 80:
        score_color = (0, 128, 0)  # Green
    elif score >= 60:
        score_color = (255, 165, 0)  # Orange
    else:
        score_color = (255, 0, 0)  # Red
    
    pdf.set_font('Arial', 'B', 36)
    pdf.set_text_color(*score_color)
    pdf.cell(0, 20, txt=f"{score}/100", ln=True, align='C')
    
    # Score meter
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(30, pdf.get_y(), 150, 10, style='D')
    pdf.set_fill_color(*score_color)
    pdf.rect(30, pdf.get_y(), 150 * (score/100), 10, style='F')
    pdf.ln(20)
    
    # Feedback section header
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(59, 89, 152)  # Dark blue
    pdf.cell(0, 10, txt="Detailed Analysis", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    # Feedback items with proper formatting
    pdf.set_font('Arial', '', 10)
    for item in feedback:
        if '[AI]' in item or '🧠' in item:
            # AI suggestion
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(59, 89, 152)  # Dark blue
            pdf.multi_cell(0, 6, txt=item.replace('🧠', '[AI]'))
            pdf.ln(4)
            pdf.set_font('Arial', '', 10)
        elif '[PASS]' in item or '✓' in item:
            # Positive feedback
            pdf.set_text_color(0, 128, 0)  # Green
            pdf.multi_cell(0, 6, txt=item.replace('✓', '[PASS]'))
            pdf.ln(2)
        elif '[WARN]' in item or '⚠' in item:
            # Warning feedback
            pdf.set_text_color(255, 165, 0)  # Orange
            pdf.multi_cell(0, 6, txt=item.replace('⚠', '[WARN]'))
            pdf.ln(2)
        else:
            # Neutral feedback
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, txt=item)
            pdf.ln(2)
    
    # Footer
    pdf.set_y(-15)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, txt="Generated by Advanced ATS Resume Scanner", align='C')
    pdf.output(path)