import pdfplumber
import re
import spacy
from pathlib import Path
from typing import Dict, List, Optional
import logging
import json
from datetime import datetime

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.info("Downloading SpaCy model...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def verify_pdf(pdf_path: str) -> bool:
    """Verify PDF content can be read."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() + '\n'
            logger.info("PDF Content Preview (first 500 chars):")
            logger.info("-" * 50)
            logger.info(text[:500])
            logger.info("-" * 50)
            return bool(text.strip())
    except Exception as e:
        logger.error(f"Error reading PDF: {str(e)}")
        return False

class ResumeParser:
    def __init__(self):
        self.SECTIONS = {
            'summary': r'(?i)(profile|summary|objective|about)',
            'education': r'(?i)(education|academic|qualification)',
            'experience': r'(?i)(experience|employment|work history)',
            'skills': r'(?i)(skills|technical skills|competencies)',
            'projects': r'(?i)(projects|personal projects)',
            'certifications': r'(?i)(certifications|certificates)',
            'contact': r'(?i)(contact|personal details|contact information)'
        }
        
        self.EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.PHONE_PATTERN = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.LINKEDIN_PATTERN = r'linkedin\.com/in/[\w-]+'
        self.GITHUB_PATTERN = r'github\.com/[\w-]+'
        self.DATE_PATTERN = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}'
        
        self.EDUCATION_TERMS = [
            'bachelor', 'master', 'phd', 'doctorate', 'bs', 'ms', 'ba', 'ma',
            'b.tech', 'm.tech', 'b.e.', 'm.e.', 'b.sc', 'm.sc',
            'university', 'college', 'institute', 'school'
        ]

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = '\n'.join(page.extract_text() for page in pdf.pages)
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information."""
        contact_info = {
            'email': None,
            'phone': None,
            'linkedin': None,
            'github': None,
            'location': None
        }
        
        # Extract email
        email_match = re.search(self.EMAIL_PATTERN, text)
        if email_match:
            contact_info['email'] = email_match.group()
        
        # Extract phone
        phone_match = re.search(self.PHONE_PATTERN, text)
        if phone_match:
            contact_info['phone'] = phone_match.group()
        
        # Extract LinkedIn
        linkedin_match = re.search(self.LINKEDIN_PATTERN, text)
        if linkedin_match:
            contact_info['linkedin'] = linkedin_match.group()
        
        # Extract GitHub
        github_match = re.search(self.GITHUB_PATTERN, text)
        if github_match:
            contact_info['github'] = github_match.group()
        
        # Extract location using SpaCy
        doc = nlp(text[:1000])
        for ent in doc.ents:
            if ent.label_ in ['GPE', 'LOC']:
                contact_info['location'] = ent.text
                break
        
        return contact_info

    def extract_education(self, text: str) -> List[Dict[str, str]]:
        """Extract education information."""
        education_list = []
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if any(term in paragraph.lower() for term in self.EDUCATION_TERMS):
                education_info = {
                    'degree': None,
                    'institution': None,
                    'graduation_date': None,
                    'gpa': None
                }
                
                # Extract dates
                dates = re.findall(self.DATE_PATTERN, paragraph)
                if dates:
                    education_info['graduation_date'] = dates[-1]
                
                # Extract institution
                doc = nlp(paragraph)
                for ent in doc.ents:
                    if ent.label_ == 'ORG':
                        education_info['institution'] = ent.text
                        break
                
                # Extract degree
                lines = paragraph.split('\n')
                for line in lines:
                    if any(term in line.lower() for term in self.EDUCATION_TERMS):
                        education_info['degree'] = line.strip()
                        break
                
                if education_info['degree'] or education_info['institution']:
                    education_list.append(education_info)
        
        return education_list

    def extract_experience(self, text: str) -> List[Dict[str, any]]:
        """Extract work experience information."""
        experience_list = []
        paragraphs = text.split('\n\n')
        current_experience = None
        
        for paragraph in paragraphs:
            if re.search(r'(19|20)\d{2}|present|current', paragraph.lower()):
                if current_experience:
                    experience_list.append(current_experience)
                current_experience = {
                    'title': None,
                    'company': None,
                    'dates': [],
                    'description': []
                }
                
                # Extract dates
                dates = re.findall(self.DATE_PATTERN, paragraph)
                if dates:
                    current_experience['dates'] = dates
                
                # Extract company
                doc = nlp(paragraph)
                for ent in doc.ents:
                    if ent.label_ == 'ORG':
                        current_experience['company'] = ent.text
                        break
                
                # First line is usually the title
                lines = paragraph.split('\n')
                if lines:
                    current_experience['title'] = lines[0].strip()
            
            elif current_experience:
                current_experience['description'].append(paragraph.strip())
        
        if current_experience:
            experience_list.append(current_experience)
        
        return experience_list

    def parse_resume(self, pdf_path: str) -> Dict:
        """Main function to parse resume."""
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(pdf_path)
            if not text:
                raise ValueError("No text could be extracted from the PDF")

            # Parse each section
            parsed_data = {
                'contact_info': self.extract_contact_info(text),
                'education': self.extract_education(text),
                'experience': self.extract_experience(text),
                'metadata': {
                    'filename': Path(pdf_path).name,
                    'parsed_date': datetime.now().isoformat(),
                    'parser_version': '1.0.0'
                }
            }
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing resume: {str(e)}")
            return None

    def save_to_json(self, parsed_data: Dict, output_path: str):
        """Save parsed resume data to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved parsed data to {output_path}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {str(e)}")

def main():
    """Main function to run the resume parser."""
    # Set up paths
    current_dir = Path.cwd()
    input_dir = current_dir / "sample_resumes"
    output_dir = current_dir / "parsed_resumes"
    
    # Create directories if they don't exist
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Initialize parser
    parser = ResumeParser()
    
    # Get list of PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF file
    success_count = 0
    failed_count = 0
    
    for pdf_file in pdf_files:
        logger.info(f"\nProcessing: {pdf_file.name}")
        logger.info("Verifying PDF content...")
        
        if not verify_pdf(str(pdf_file)):
            logger.error(f"Could not read content from {pdf_file.name}")
            failed_count += 1
            continue
            
        try:
            parsed_data = parser.parse_resume(str(pdf_file))
            if parsed_data:
                output_path = output_dir / f"{pdf_file.stem}_parsed.json"
                parser.save_to_json(parsed_data, str(output_path))
                success_count += 1
                logger.info(f"Successfully parsed and saved to {output_path}")
            else:
                failed_count += 1
                logger.error(f"Failed to parse {pdf_file.name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {pdf_file.name}: {str(e)}")
    
    # Print summary
    logger.info("\nProcessing complete:")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failed_count}")

if __name__ == "__main__":
    main()