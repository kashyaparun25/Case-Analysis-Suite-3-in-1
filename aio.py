import streamlit as st
import os
import re
import tempfile
import logging
import time
import base64
import json
from typing import List, Dict, Any, Union, Optional, Tuple
from dotenv import load_dotenv
import io

# Document processing libraries
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import PyPDF2
from pptx import Presentation
import docx2txt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# CrewAI imports
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tasks import TaskOutput
from crewai.tools import BaseTool, tool
from pydantic import BaseModel, Field
import litellm
from langchain.tools import Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Case Study Analysis Suite",
    page_icon="📚",
    layout="wide"
)

# Initialize session state variables
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Case Breakdown"
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = ""
if 'first_file_text' not in st.session_state:
    st.session_state.first_file_text = ""
if 'breakdown_generated' not in st.session_state:
    st.session_state.breakdown_generated = False
if 'teaching_plan_generated' not in st.session_state:
    st.session_state.teaching_plan_generated = False
if 'board_plan_generated' not in st.session_state:
    st.session_state.board_plan_generated = False

# Load environment variables
load_dotenv()

# Page title and description
st.title("📚 Case Study Analysis Suite")
st.subheader("Generate comprehensive Teaching Notes, Teaching Plans, and Board Plans")
st.write("Developed for BIA 568 (Business Intelligence and Analytics) -- Management of A.I. at Stevens Institute of Technology")

st.write("---")

# Sidebar for API key configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key_source = st.radio("Select API Key Provider:", 
                            ["Google (Gemini)", "OpenAI"],
                            help="Choose which AI provider to use")
    
    if api_key_source == "Google (Gemini)":
        api_key = st.text_input("Enter your Gemini API Key", type="password", 
                                help="Required for the AI model to function")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
    else:
        api_key = st.text_input("Enter your OpenAI API Key", type="password", 
                                help="Required for the AI model to function")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            
    st.divider()
    
    # Reset button
    if st.button("🔄 Reset Session", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


#---------------------------- Utility Functions ----------------------------#

def extract_text_from_pdf(file):
    """Extract text content from PDF file"""
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    """Extract text content from DOCX file"""
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    return docx2txt.process(file)

def extract_text_from_pptx(file):
    """Extract text content from PPTX file"""
    if isinstance(file, bytes):
        file = io.BytesIO(file)
    prs = Presentation(file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

def extract_text_from_any_file(file):
    """Extract text based on file type"""
    if file.name.endswith('.pdf'):
        return extract_text_from_pdf(file)
    elif file.name.endswith('.docx'):
        return extract_text_from_docx(file)
    elif file.name.endswith(('.pptx', '.ppt')):
        return extract_text_from_pptx(file)
    else:
        return "Unsupported file format"

def create_download_link(content, filename):
    """Create a download link for text content"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:text/plain;base64,{b64}" download="{filename}" class="download-button">Download {filename}</a>'
    return href

def process_files(uploaded_files):
    """Process uploaded files and extract text"""
    combined_text = ""
    first_file_text = ""
    
    temp_file_paths = []
    
    for file in uploaded_files:
        file.seek(0)  # Reset file pointer
        
        # Extract text based on file type
        if file.name.endswith('.pdf'):
            text = extract_text_from_pdf(file)
        elif file.name.endswith('.docx'):
            text = extract_text_from_docx(file)
        elif file.name.endswith(('.pptx', '.ppt')):
            text = extract_text_from_pptx(file)
        else:
            continue
        
        # Save first file's text for metadata extraction
        if not first_file_text:
            first_file_text = text
        
        combined_text += text + "\n\n"
        
        # Create temporary file for each uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.name.split('.')[-1]}") as tmp_file:
            file.seek(0)
            tmp_file.write(file.getvalue())
            temp_file_paths.append(tmp_file.name)
    
    return combined_text, first_file_text, temp_file_paths

#---------------------------- Document Generator (Case Breakdown) ----------------------------#

class DocumentGenerator:
    def __init__(self):
        self.bullet_counter = 1

    def add_toc(self, doc):
        """Add native Word table of contents"""
        paragraph = doc.add_paragraph()
        run = paragraph.add_run()

        # Start the TOC field
        fldChar1 = create_element('w:fldChar')
        create_attribute(fldChar1, 'w:fldCharType', 'begin')
        run._r.append(fldChar1)

        # Add TOC instruction text
        instrText = create_element('w:instrText')
        create_attribute(instrText, 'xml:space', 'preserve')
        instrText.text = 'TOC \\o "1-3" \\h \\z \\u'
        run._r.append(instrText)

        # End the TOC field
        fldChar2 = create_element('w:fldChar')
        create_attribute(fldChar2, 'w:fldCharType', 'end')
        run._r.append(fldChar2)

    def setup_document_styles(self, doc):
        """Set up custom styles for the document"""
        styles = doc.styles
        
        # Heading styles
        for level in range(1, 4):
            style_name = f'Heading {level}'
            if style_name not in styles:
                style = styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
                style.base_style = styles['Normal']
                style.font.size = Pt(16 - (level * 2))
                style.font.bold = True

        # Custom bullet point style
        if 'Bullet Point' not in styles:
            bullet_style = styles.add_style('Bullet Point', WD_STYLE_TYPE.PARAGRAPH)
            bullet_style.base_style = styles['Normal']
            bullet_style.font.size = Pt(11)
            bullet_style.paragraph_format.left_indent = Inches(0.25)
            bullet_style.paragraph_format.first_line_indent = Inches(-0.25)

    def add_formatted_text(self, paragraph, text):
        """Add text to paragraph with proper formatting"""
        # First handle double asterisks
        parts = re.split(r'(\*\*.*?\*\*)', text)
        
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                # Handle bold text (surrounded by double asterisks)
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            else:
                # Handle single asterisks within the remaining text
                # Split by single asterisks
                subparts = re.split(r'(\*[^\*]+\*)', part)
                for subpart in subparts:
                    if subpart.startswith('*') and subpart.endswith('*') and len(subpart) > 2:
                        # It's a bold text marked with single asterisks
                        run = paragraph.add_run(subpart[1:-1])
                        run.bold = True
                    else:
                        # Regular text
                        if subpart.strip():
                            paragraph.add_run(subpart)

    def clean_content(self, text):
        """Clean content and formatting"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove markdown headers while preserving content
        text = re.sub(r'^#+\s*(.+)$', r'\1', text, flags=re.MULTILINE)
        
        # Remove duplicate section headers
        text = re.sub(r'(?i)^(.*?)\n\*\*\1\*\*', r'\1', text, flags=re.MULTILINE)
        
        # Clean up <br> tags
        text = re.sub(r'<br\s*/?>', '\n', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Process line by line to handle bullet points and bold text
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append(line)
                continue
                
            # Check if line starts with a single asterisk (potential bullet point)
            if line.lstrip().startswith('*'):
                # Skip if it starts with double asterisks
                if line.lstrip().startswith('**'):
                    cleaned_lines.append(line)
                    continue
                    
                # Count asterisks that are not part of bold text markers
                # First, temporarily replace bold text markers
                temp_line = re.sub(r'\*\*.*?\*\*', '', line)  # Remove double-asterisk patterns
                temp_line = re.sub(r'\*[^\*]+\*', '', temp_line)  # Remove single-asterisk patterns
                
                # If there's exactly one asterisk left, it's a bullet point
                if temp_line.count('*') == 1:
                    content = line.replace('*', '', 1).strip()
                    cleaned_lines.append(f'* {content}')
                else:
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def add_section_content(self, doc, section_name, content):
        """Add a section with proper formatting"""
        # Add section heading
        heading = doc.add_heading(section_name.upper(), level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Clean and process the content
        content = self.clean_content(content)
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for bullet point line
            is_bullet = line.startswith('* ') and not line.startswith('** ')
            
            if is_bullet:
                # Create bullet point paragraph
                bullet_paragraph = doc.add_paragraph(style='Bullet Point')
                bullet_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                bullet_paragraph.paragraph_format.left_indent = Inches(0.5)
                bullet_paragraph.paragraph_format.first_line_indent = Inches(-0.25)
                
                # Add bullet character
                bullet_paragraph.add_run('• ')
                
                # Add the rest of the line with formatting
                content = line[2:].strip()
                self.add_formatted_text(bullet_paragraph, content)
            else:
                # Regular paragraph
                p = doc.add_paragraph()
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                self.add_formatted_text(p, line)

    def create_word_document(self, title, author, sections_content):
        """Create and return a formatted Word document"""
        doc = Document()
        self.setup_document_styles(doc)
        
        # Title section
        title_paragraph = doc.add_paragraph()
        title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_paragraph.add_run("CASE BREAKDOWN")
        title_run.font.size = Pt(16)
        title_run.bold = True
        
        # Case study name and author
        case_name_paragraph = doc.add_paragraph()
        case_name_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        case_name_run = case_name_paragraph.add_run(title)
        case_name_run.font.size = Pt(14)
        case_name_run.italic = True
        
        author_paragraph = doc.add_paragraph()
        author_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        author_run = author_paragraph.add_run(author)
        author_run.font.size = Pt(12)
        
        # Separator line
        separator = doc.add_paragraph()
        separator.alignment = WD_ALIGN_PARAGRAPH.CENTER
        separator_run = separator.add_run('_' * 50)
        
        # Add TOC
        toc_heading = doc.add_heading('TABLE OF CONTENTS', level=1)
        toc_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.add_toc(doc)
        doc.add_page_break()
        
        # Add sections
        for section_name, content in sections_content.items():
            self.add_section_content(doc, section_name, content)
            doc.add_paragraph()  # Add spacing between sections
        
        return doc

# Helper functions for Word document
def create_element(name):
    return OxmlElement(name)

def create_attribute(element, name, value):
    element.set(qn(name), value)

#---------------------------- Case Breakdown Generator ----------------------------#

class CaseMetadata(BaseModel):
    title: str = Field(description="The title of the case study")
    author: str = Field(description="The author(s) of the case study")

class SectionContent(BaseModel):
    content: str = Field(description="Generated content for the section")
    review: str = Field(description="Review of the content with score and feedback")

class CaseBreakdownCrew:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def create_metadata_agent(self):
        return Agent(
            role="Metadata Analyzer",
            goal="Extract title and author information from document content",
            backstory="""You specialize in analyzing document content to identify key metadata
            such as titles, authors, and other publication information. You have a keen eye for
            identifying the most important and relevant document metadata, even when it's not
            explicitly labeled.""",
            verbose=True
        )
    
    def create_content_generator_agent(self):
        return Agent(
            role="Case Study Content Generator",
            goal="Generate comprehensive case analysis content based on section requirements",
            backstory="""You are an expert business analyst specializing in case study analysis.
            You excel at breaking down complex business cases into structured, insightful content
            that highlights key learning points, strategies, and insights. You have extensive experience
            in business education and know how to create content that is valuable for teaching and learning.""",
            verbose=True
        )
    
    def create_content_reviewer_agent(self):
        return Agent(
            role="Content Quality Reviewer",
            goal="Evaluate and score content for quality, relevance, and depth",
            backstory="""You are a seasoned academic reviewer with years of experience evaluating
            business case studies and educational content. You have a strong understanding of what makes
            effective case study material and can provide constructive feedback to improve content quality.
            You carefully analyze content for relevance, clarity, depth, and educational value.""",
            verbose=True
        )
    
    def create_metadata_task(self, text):
        return Task(
            description=f"""
            Analyze the extracted text and identify the case study title and author(s).
            
            Look for information typically found at the beginning of a document, such as:
            1. The case study or article title
            2. The author name(s)
            
            Return the identified title and author in the following format:
            
            Title: [the title]
            Author: [the author(s)]
            
            If you cannot find this information with certainty, use "Untitled Case Study" for the title
            and "Unknown Author" for the author.
            
            Text to analyze:
            {text[:2000]}
            """,
            expected_output="Extracted metadata with title and author information",
            agent=self.create_metadata_agent()
        )
    
    def create_section_task(self, section_name, prompt, text):
        return Task(
            description=f"""
            Generate content for the '{section_name}' section of the case breakdown.
            
            {prompt}
            
            Formatting Requirements:
            1. Use **bold** for important terms or concepts
            2. For bullet points, start each line with "* " (asterisk followed by space)
            3. For numbered lists, use "1. ", "2. " etc.
            4. Use line breaks between paragraphs
            5. Keep paragraphs focused and concise
            
            Ensure the content is structured, well-organized, and follows proper formatting.
            
            Text to analyze:
            {text[:5000]}
            """,
            expected_output=f"A well-formatted {section_name} section",
            agent=self.create_content_generator_agent()
        )
    
    def create_review_task(self, section_name, content):
        return Task(
            description=f"""
            Review the content for the '{section_name}' section.
            
            Score it from 1-10 based on:
            1. Relevance to the section (0-3)
            2. Clarity and coherence (0-3)
            3. Depth of analysis (0-4)
            
            Provide a structured review with:
            1. Numerical score
            2. Specific strengths
            3. Areas for improvement
            
            Content to review:
            {content}
            """,
            expected_output=f"A review of the {section_name} section",
            agent=self.create_content_reviewer_agent()
        )
    
    def extract_metadata(self, text):
        metadata_task = self.create_metadata_task(text)
        crew = Crew(
            agents=[self.create_metadata_agent()],
            tasks=[metadata_task],
            process=Process.sequential,
            verbose=False
        )
        result = crew.kickoff()
        
        title = "Untitled Case Study"
        author = "Unknown Author"
        
        for line in result.raw.split('\n'):
            if line.startswith('Title:'):
                extracted_title = line.replace('Title:', '').strip()
                if extracted_title and extracted_title != "[Untitled Case Study]":
                    title = extracted_title
            elif line.startswith('Author:'):
                extracted_author = line.replace('Author:', '').strip()
                if extracted_author and extracted_author != "[Unknown Author]":
                    author = extracted_author
        
        return title, author
    
    def generate_section_content(self, text, section_name, section_prompt):
        section_task = self.create_section_task(section_name, section_prompt, text)
        crew = Crew(
            agents=[self.create_content_generator_agent()],
            tasks=[section_task],
            process=Process.sequential,
            verbose=False
        )
        result = crew.kickoff()
        return result.raw
    
    def review_content(self, content, section_name):
        review_task = self.create_review_task(section_name, content)
        crew = Crew(
            agents=[self.create_content_reviewer_agent()],
            tasks=[review_task],
            process=Process.sequential,
            verbose=False
        )
        result = crew.kickoff()
        return result.raw

#---------------------------- Teaching Plan Generator ----------------------------#

class AgentTracker:
    def __init__(self):
        self.current_agent = ""
        self.placeholder = None
    
    def set_placeholder(self, placeholder):
        self.placeholder = placeholder
    
    def update_agent(self, agent_name):
        self.current_agent = agent_name
        if self.placeholder:
            with self.placeholder:
                st.write(f"🤖 Agent in action: **{self.current_agent}**")

@tool
def extract_text(file_path: str) -> str:
    """
    Extract text from a file based on its extension.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: Extracted text content
    """
    try:
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            reader = PyPDF2.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        
        elif file_extension == 'docx':
            return docx2txt.process(file_path)
        
        elif file_extension in ['ppt', 'pptx']:
            presentation = Presentation(file_path)
            text = ""
            for slide in presentation.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            return text
        
        else:
            return f"Unsupported file format: {file_extension}"
    
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def create_teaching_plan_crew(file_paths, llm_provider="gemini"):
    # Initialize the agent tracker
    tracker = AgentTracker()
    tracker.set_placeholder(st.empty())
    
    # Initialize LLM based on provider
    if llm_provider == "gemini":
        my_llm = LLM(
            model='gemini/gemini-2.0-flash',
            api_key=os.environ.get("GEMINI_API_KEY")
        )
    else:
        my_llm = LLM(
            model='gpt-4-turbo',
            api_key=os.environ.get("OPENAI_API_KEY")
        )
    
    # Define agents with callbacks for UI updates
    pdf_analyzer = Agent(
        role='Case Study Analyzer',
        goal='Extract key concepts, objectives, and data from case study PDFs',
        backstory='You are an expert in analyzing business case studies. Identify core themes, data points, and learning objectives.',
        llm=my_llm,
        tools=[extract_text],
        verbose=True,
        step_callback=lambda *args, **kwargs: tracker.update_agent("Case Study Analyzer")
    )

    plan_generator = Agent(
        role='Teaching Plan Designer',
        goal='Create a 2-hour lesson plan based on analyzed case study data',
        backstory='You are an educator designing a structured lesson plan. Use the extracted case study data to outline activities, discussions, and assessments.',
        llm=my_llm,
        verbose=True,
        step_callback=lambda *args, **kwargs: tracker.update_agent("Teaching Plan Designer")
    )

    reviewer = Agent(
        role='Plan Reviewer',
        goal='Ensure the lesson plan is engaging and aligned with learning objectives',
        backstory='You are a curriculum reviewer. Verify the plan\'s clarity, alignment with objectives, and engagement level.',
        llm=my_llm,
        verbose=True,
        step_callback=lambda *args, **kwargs: tracker.update_agent("Plan Reviewer")
    )

    final_reporter = Agent(
        role='Teaching Plan Reporter',
        goal='Ensure to incorporate the feedback from the reviewer agent and finalize the content for the teaching plan',
        backstory=""" You are a Harvard Business School Teaching Plan Reporter with 20 years of Experience in teaching and curriculum development. 
                    You are responsible for finalizing the content for the teaching plan and ensuring it is engaging and aligned with learning objectives. 
                   You will use the feedback from the reviewer agent to make necessary revisions and finalize the content for the teaching plan.""",
        llm=my_llm,
        verbose=True,
        step_callback=lambda *args, **kwargs: tracker.update_agent("Teaching Plan Reporter")
    )

    # Combine all file contents into one text
    combined_file_path = file_paths[0]  # Use the first file path for the analyzer to begin
    
    # Define tasks
    analyze_pdf = Task(
        description=f"Extract and analyze the files at {', '.join(file_paths)} for key concepts and learning objectives.",
        config={"file_path": combined_file_path},
        expected_output="A summary of key concepts and learning objectives extracted from the files.",
        agent=pdf_analyzer
    )

    generate_plan = Task(
        description="Design a 2-hour lesson plan with introduction, analysis, group activity, and assessment.",
        expected_output="A detailed 2-hour lesson plan with clear sections and activities.",
        agent=plan_generator
    )

    review_plan = Task(
        description="Review the lesson plan for clarity, alignment with objectives, and student engagement.",
        expected_output="Feedback on the lesson plan's clarity, alignment, and engagement level.",
        agent=reviewer
    )

    final_plan = Task(
        description="Generate the final lesson plan based on the feedback.",
        expected_output="""
                        You are also responsible for ensuring the plan is clear and concise. 
                    - It should have the overall objective to start with.
                    - It should have a clear introduction
                    - It should have detailed lesson breakdowns with the time to be spent on each section and the title of the section Highlighting all the important concepts to be taught (you can use tables to highlight the concepts in a structured way)
                    - It should have one powerful visual aid which can be a tablet That can help in better understanding for the students
                    - It can have simple assessmentsthat enables class participation engagement in brainstorming activities and such that can help in better understanding of the concepts.
                    - It should have a clear conclusion that ties back to the overall objective.
                    - Overall Plan should be around 1300 - 1500 words.""",
        agent=final_reporter
    )
    
    # Create crew
    crew = Crew(
        agents=[pdf_analyzer, plan_generator, reviewer, final_reporter],
        tasks=[analyze_pdf, generate_plan, review_plan, final_plan],
        process=Process.sequential,
        verbose=True
    )
    
    return crew

#---------------------------- Board Plan Generator ----------------------------#

class BoardPlanAnalyzer:
    def __init__(self, llm_provider="gemini"):
        if llm_provider == "gemini":
            api_key = os.environ.get('GEMINI_API_KEY')
            self.model = "gemini/gemini-2.0-flash"
        else:
            api_key = os.environ.get('OPENAI_API_KEY')
            self.model = "gpt-4-turbo"
            
        if not api_key:
            raise ValueError(f"{llm_provider.capitalize()} API key not found")
            
        if llm_provider == "gemini":
            os.environ['GEMINI_API_KEY'] = api_key
        else:
            os.environ['OPENAI_API_KEY'] = api_key
            
        litellm.set_verbose = True
        
        # Create agents
        self.create_agents()

    def create_agents(self):
        """Create specialized agents for different tasks"""
        
        # PDF Processing Agent
        self.pdf_processor = Agent(
            role='PDF Processor',
            goal='Extract and clean text content from PDF case studies',
            backstory="""You are an expert at processing PDF documents and extracting 
            meaningful content. You ensure the text is properly formatted and ready 
            for analysis.""",
            tools=[Tool(
                name="extract_text",
                func=self.extract_text_from_pdf,
                description="Extracts text content from PDF files"
            )],
            allow_delegation=False,
            verbose=True
        )

        # Content Analysis Agent
        self.analyzer = Agent(
            role='Case Study Analyzer',
            goal='Analyze case studies and identify key points for board plan',
            backstory="""You are an expert business analyst skilled at analyzing case 
            studies and identifying crucial elements. You create clear, structured 
            analyses that highlight key insights.""",
            tools=[Tool(
                name="analyze_content",
                func=self.analyze_case_study,
                description="Analyzes case study and creates structured board plan"
            )],
            allow_delegation=False,
            verbose=True
        )

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF using PyPDF2"""
        try:
            # Create PDF reader object
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            # Combine all pages with proper spacing
            return "\n\n".join(text_content)
            
        except Exception as e:
            raise Exception(f"PDF extraction error: {str(e)}")

    def analyze_case_study(self, text: str) -> dict:
        """Analyze case study content using litellm with JSON response"""
        messages = [
            {
                "role": "user",
                "content": f"""Analyze this case study and create a structured board plan.
                
                Case study: {text}
                
                Create a detailed analysis with these exact sections:
                1. Main concept/technology being discussed
                2. Industry suitability and context
                3. Benefits and impact
                4. Key roles and perspectives
                5. Implementation details
                   - Data requirements
                   - Scaling considerations
                   - Performance metrics
                6. Next steps and recommendations
                
                Also include risk assessment.
                
                Format the response as a JSON object with this structure:
                {{
                    "boards": [
                        {{
                            "title": "BOARD 1: [Title]",
                            "points": ["point 1", "point 2", "point 3"]
                        }},
                        // ... other boards
                    ],
                    "risk_assessment": {{
                    "title": "WHAT IS THE RISK OF FAILURE?",
                    "points": ["risk 1", "risk 2"]
                    }}
                }}"""
            }
        ]
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the JSON response
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            if 'response' in locals():
                st.error("Raw response:")
                st.code(response.choices[0].message.content)
            raise

    def process_case_study(self, pdf_content: bytes) -> dict:
        """Process the case study using Crew AI agents"""
        try:
            # First extract text
            progress_text = st.empty()
            progress_text.text("Extracting text from PDF...")
            text_content = self.extract_text_from_pdf(pdf_content)
            
            # Show extracted text for verification
            with st.expander("View extracted text"):
                st.text(text_content[:500] + "...")
            
            # Then analyze content
            progress_text.text("Analyzing content...")
            result = self.analyze_case_study(text_content)
            
            return result
            
        except Exception as e:
            raise Exception(f"Processing error: {str(e)}")

#---------------------------- Main App Interface ----------------------------#

# File upload section - shared across all generators
if st.session_state.uploaded_files is None:
    uploaded_files = st.file_uploader(
        "Upload case study files (PDF, DOCX, PPT, PPTX)", 
        accept_multiple_files=True,
        type=['pdf', 'docx', 'ppt', 'pptx']
    )
    
    if uploaded_files:
        st.session_state.uploaded_files = uploaded_files
        
        # Process files only once and store results
        with st.spinner("Processing uploaded files..."):
            combined_text, first_file_text, temp_file_paths = process_files(uploaded_files)
            st.session_state.combined_text = combined_text
            st.session_state.first_file_text = first_file_text
            st.session_state.temp_file_paths = temp_file_paths
            
            # Show file upload summary
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded and processed successfully")
            for file in uploaded_files:
                st.write(f"- {file.name}")

# Tabs for different generators
if st.session_state.uploaded_files:
    # Use native streamlit tabs (no styling overrides)
    tab1, tab2, tab3 = st.tabs([
        "Case Breakdown Generator", 
        "Teaching Plan Generator", 
        "Board Plan Generator"
    ])
    
    #------------------ Case Breakdown Generator Tab ------------------#
    with tab1:
        st.header("Case Breakdown Generator")
        st.write("Generate a comprehensive breakdown of the case study with sections for teaching purposes.")
        
        if not st.session_state.breakdown_generated:
            if not api_key:
                st.warning("⚠️ Please enter an API key in the sidebar before proceeding.")
            else:
                # Initialize the breakdown generator
                crew_manager = CaseBreakdownCrew(api_key)
                
                # Extract metadata
                with st.spinner("Extracting document metadata..."):
                    title, author = crew_manager.extract_metadata(st.session_state.first_file_text)

                # Display extracted metadata with option to edit
                st.subheader("Extracted Document Information")
                title = st.text_input("Case Study Title:", title)
                author = st.text_input("Author:", author)
                
                # Initialize sections based on template
                sections = {
                    "Case Synopsis": """ Summarize the case in 3–4 paragraphs of a total 300 words. Explain the company's background, the industry it operates in, 
                                        and the key challenge or strategic decision it faces. Discuss any turning points or dilemmas. Why is this case relevant for 
                                        business students? 
                                        Position in Course: In 1–2 sentences, describe which type of course this case is best suited for 
                                        (e.g., Operations Strategy, AI in Business, Global Supply Chain). What key topics does it help students understand""",

                   
                    "Learning Objectives": """List 8–10 learning objectives for this case. A total of 300 words.  What should students understand after analyzing this case? Focus on 
                                            leadership decisions, operational insights, AI adoption, or ethical concerns""",
                    
                    "Teaching Strategies":
                    """
                    Describe 8–10 ways an instructor can effectively teach this case. Should they use role-playing? A total of 350 words.
                    A structured debate? Analyzing real-world examples? How can students actively engage with the material? 1st point should be Approach and second point should be Objective
                    """,
                    "Suggested Teaching Plan":
                    """
                    Outline a structured teaching plan for this case. What should be covered first? A total of 350 words.
                    When should student activities be introduced? How should the case discussion conclude?
                    """,

                    "Key Points and Insights":
                    """
                    List 10 key insights students should take from this case. What makes this case unique? A total of 300 words.
                    What are the most important strategic, operational, or ethical considerations?
                    """,

                    "Further Insights":
                    """
                    Provide additional insights that go beyond the case. How does this case relate to 
                    larger business trends? What external factors (e.g., regulation, innovation, geopolitical forces) could impact the situation? A total of 400 words.
                    """,

                    "Discussion Questions & Answers":
                    """
                    Create 8–10 discussion questions about the case. What are the key strategic dilemmas?
                     Where do trade-offs exist? How can students critically analyze the company's decisions? Provide concise answers. A total of 450 words.
                    """,

                    "Assignment Exercises":
                    """
                    List 8–10 in-depth assignments that encourage strategic thinking, data analysis, 
                    or real-world application. Include a mix of strategy proposals, financial analysis, 
                    role-playing exercises, and ethical debates. Define the expected format 
                    (e.g., business report, presentation, comparative analysis) and objective of each exercise. A total of 550- 600 words.
                    """,

                    "Automated Conversation":
                    """
                    Write an AI-generated conversation between three personas relevant to the case. A total of 650- 700 words.
                    One should be an executive making a strategic decision, another should be an expert,
                    and the third should be skeptical or resistant. The conversation should explore the challenges, risks, and strategic importance of the case.
                    """,

                    "Case Suggestions":
                    """
                    List 10 ways to make this case more interactive. Should students role-play as executives? 
                    Simulate a crisis response? Conduct a competitive market analysis? 
                    Suggest unique, hands-on ways to engage with the case. A total of 550 words.
                    """
                }
                
                # Generate button
                if st.button("Generate Case Breakdown", key="breakdown_button"):
                    # Create tabs for content and review
                    content_tab, review_tab = st.tabs(["Generated Content", "Content Review"])
                    
                    # Generate and display content
                    sections_content = {}
                    reviews = {}
                    
                    with st.spinner("Generating content... This may take several minutes."):
                        progress_bar = st.progress(0)
                        
                        with content_tab:
                            for i, (section_name, prompt) in enumerate(sections.items()):
                                # Generate content using the CrewAI agents
                                st.info(f"Generating {section_name}...")
                                content = crew_manager.generate_section_content(st.session_state.combined_text, section_name, prompt)
                                sections_content[section_name] = content
                                
                                # Generate review
                                review = crew_manager.review_content(content, section_name)
                                reviews[section_name] = review
                                
                                # Display content in preview
                                st.subheader(section_name)
                                st.markdown(content)
                                
                                # Update progress
                                progress_bar.progress((i + 1) / len(sections))
                    
                    # Store generated content in session state
                    st.session_state.sections_content = sections_content
                    st.session_state.reviews = reviews
                    st.session_state.title = title
                    st.session_state.author = author
                    st.session_state.breakdown_generated = True
                    
                    # Display reviews in review tab
                    with review_tab:
                        for section_name, review in reviews.items():
                            st.subheader(f"{section_name} Review")
                            st.markdown(review)
                    
                    # Generate and store the document for later
                    doc_generator = DocumentGenerator()
                    doc = doc_generator.create_word_document(
                        title=title,
                        author=author,
                        sections_content=sections_content
                    )
                    
                    # Save document to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                        doc.save(tmp_file.name)
                        st.session_state.doc_path = tmp_file.name
                        
                    # Allow the user to download the document
                    with open(st.session_state.doc_path, 'rb') as file:
                        st.download_button(
                            label="📥 Download Case Breakdown (DOCX)",
                            data=file,
                            file_name=f"{title.lower().replace(' ', '_')}_case_breakdown.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="download_docx_button"
                        )
                
        else:
            # If we already have generated content, display it without regenerating
            st.subheader("Extracted Document Information")
            st.text_input("Case Study Title:", value=st.session_state.title, key="title_display", disabled=True)
            st.text_input("Author:", value=st.session_state.author, key="author_display", disabled=True)
            
            # Display the generated content in tabs
            content_tab, review_tab = st.tabs(["Generated Content", "Content Review"])
            
            with content_tab:
                for section_name, content in st.session_state.sections_content.items():
                    st.subheader(section_name)
                    st.markdown(content)
            
            with review_tab:
                for section_name, review in st.session_state.reviews.items():
                    st.subheader(f"{section_name} Review")
                    st.markdown(review)
            
            # Allow the user to download the document without regenerating
            with open(st.session_state.doc_path, 'rb') as file:
                st.download_button(
                    label="📥 Download Case Breakdown (DOCX)",
                    data=file,
                    file_name=f"{st.session_state.title.lower().replace(' ', '_')}_case_breakdown.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="download_docx_button" 
                )
    
    #------------------ Teaching Plan Generator Tab ------------------#
    with tab2:
        st.header("Teaching Plan Generator")
        st.write("Generate a comprehensive 2-hour teaching plan for the case study.")
        
        if not st.session_state.teaching_plan_generated:
            if not api_key:
                st.warning("⚠️ Please enter an API key in the sidebar before proceeding.")
            else:
                # Create a button to start generation
                if st.button("Generate Teaching Plan", key="teaching_plan_button"):
                    try:
                        # Create placeholders for UI updates
                        progress_placeholder = st.empty()
                        agent_status_placeholder = st.empty()
                        
                        # Create a tracker and set its placeholder
                        tracker = AgentTracker()
                        tracker.set_placeholder(agent_status_placeholder)
                        
                        # Initialize progress bar
                        progress_bar = progress_placeholder.progress(0)
                        
                        # Select LLM provider
                        llm_provider = "gemini" if api_key_source == "Google (Gemini)" else "openai"
                        
                        # Update progress
                        progress_bar.progress(10)
                        st.info("🔍 Initializing crew and analyzing documents...")
                        
                        # Create crew
                        crew = create_teaching_plan_crew(st.session_state.temp_file_paths, llm_provider)
                        
                        # Update progress
                        progress_bar.progress(30)
                        st.info("📖 Document analysis in progress...")
                        
                        # Start the execution
                        start_time = time.time()
                        result = crew.kickoff(inputs={"file_path": st.session_state.temp_file_paths[0]})
                        result_text = str(result)  # Convert CrewOutput to string
                        
                        # Update progress
                        progress_bar.progress(90)
                        st.info("✏️ Finalizing teaching plan...")
                        
                        # Calculate execution time
                        execution_time = time.time() - start_time
                        
                        # Complete progress
                        progress_bar.progress(100)
                        agent_status_placeholder.empty()  # Clear the agent status
                        
                        # Save results to session state
                        st.session_state.teaching_plan_execution_time = execution_time
                        st.session_state.teaching_plan_result = result_text
                        st.session_state.teaching_plan_generated = True
                        
                        # Display the result
                        st.success(f"✅ Teaching plan generated successfully in {execution_time:.2f} seconds!")
                        st.subheader("📝 Generated Teaching Plan")
                        st.markdown(result_text)
                        
                        # Provide download option
                        st.download_button(
                            label="📥 Download Teaching Plan (Markdown)",
                            data=result_text,
                            file_name="teaching_plan.md",
                            mime="text/markdown",
                        )
                        
                    except Exception as e:
                        st.error(f"❌ An error occurred during processing: {str(e)}")
                
                # Show instructions
                with st.expander("ℹ️ How it works"):
                    st.write("""
                    The Teaching Plan Generator creates a comprehensive 2-hour lesson plan with:
                    
                    1. **Clear learning objectives** tied to the case study
                    2. **Structured timeline** with time allocations for each activity
                    3. **Engaging activities** for effective student learning
                    4. **Discussion questions** to promote critical thinking
                    5. **Assessment strategies** to measure understanding
                    
                    The AI uses a team of specialized agents to analyze your case study, create a draft plan, 
                    review it for quality, and finalize it into a polished teaching resource.
                    """)
        else:
            # Display the previously generated content
            st.success(f"✅ Teaching plan generated successfully in {st.session_state.teaching_plan_execution_time:.2f} seconds!")
            st.subheader("📝 Generated Teaching Plan")
            st.markdown(st.session_state.teaching_plan_result)
            
            # Provide download option
            st.download_button(
                label="📥 Download Teaching Plan (Markdown)",
                data=st.session_state.teaching_plan_result,
                file_name="teaching_plan.md",
                mime="text/markdown",
            )
    
    #------------------ Board Plan Generator Tab ------------------#
    with tab3:
        st.header("Board Plan Generator")
        st.write("Generate a structured board plan analysis for the case study.")
        
        if not st.session_state.board_plan_generated:
            if not api_key:
                st.warning("⚠️ Please enter an API key in the sidebar before proceeding.")
            else:
                # Create a button to start generation
                if st.button("Generate Board Plan", key="board_plan_button"):
                    try:
                        # Select LLM provider
                        llm_provider = "gemini" if api_key_source == "Google (Gemini)" else "openai"
                        
                        # Initialize the board plan analyzer
                        analyzer = BoardPlanAnalyzer(llm_provider=llm_provider)
                        
                        with st.spinner("Analyzing case study to generate board plan..."):
                            # Get content from first uploaded file
                            file = st.session_state.uploaded_files[0]
                            pdf_content = file.getvalue()
                            
                            # Process the case study
                            analysis_result = analyzer.process_case_study(pdf_content)
                            
                            # Store in session state
                            st.session_state.board_plan_result = analysis_result
                            st.session_state.board_plan_generated = True
                            
                            # Generate markdown for download
                            markdown_content = "# Board Plan Analysis\n\n"
                            for board in analysis_result['boards']:
                                markdown_content += f"## {board['title']}\n\n"
                                for point in board['points']:
                                    markdown_content += f"* {point}\n"
                                markdown_content += "\n"
                            
                            if 'risk_assessment' in analysis_result:
                                markdown_content += f"## {analysis_result['risk_assessment']['title']}\n\n"
                                for point in analysis_result['risk_assessment']['points']:
                                    markdown_content += f"* {point}\n"
                            
                            st.session_state.board_plan_markdown = markdown_content
                        
                        st.success("Board plan generated successfully!")
                        
                        # Display the analysis results
                        st.subheader("Board Plan Analysis")
                        for board in analysis_result['boards']:
                            with st.expander(board['title'], expanded=True):
                                for point in board['points']:
                                    st.markdown(f"• {point}")
                        
                        if 'risk_assessment' in analysis_result:
                            st.subheader("Risk Assessment")
                            for point in analysis_result['risk_assessment']['points']:
                                st.markdown(f"• {point}")
                        
                        # Provide download option
                        st.download_button(
                            label="📥 Download Board Plan (Markdown)",
                            data=st.session_state.board_plan_markdown,
                            file_name="board_plan.md",
                            mime="text/markdown",
                        )
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        st.error("Please ensure the file is not encrypted and contains extractable text.")
                
                # Show instructions
                with st.expander("ℹ️ How it works"):
                    st.write("""
                    The Board Plan Generator creates a structured analysis with these components:
                    
                    1. **Main concept/technology** being discussed in the case study
                    2. **Industry suitability and context** for application
                    3. **Benefits and impact** of implementing the solution
                    4. **Key roles and perspectives** from stakeholders
                    5. **Implementation details** including data requirements, scaling, and metrics
                    6. **Next steps and recommendations** for moving forward
                    7. **Risk assessment** to identify potential challenges
                    
                    The generator provides a structured framework perfect for teaching, presentations, 
                    or boardroom discussions.
                    """)
        else:
            # Display the previously generated content
            st.success("Board plan generated successfully!")
            
            # Display the analysis results
            st.subheader("Board Plan Analysis")
            for board in st.session_state.board_plan_result['boards']:
                with st.expander(board['title'], expanded=True):
                    for point in board['points']:
                        st.markdown(f"• {point}")
            
            if 'risk_assessment' in st.session_state.board_plan_result:
                st.subheader("Risk Assessment")
                for point in st.session_state.board_plan_result['risk_assessment']['points']:
                    st.markdown(f"• {point}")
            
            # Provide download option
            st.download_button(
                label="📥 Download Board Plan (Markdown)",
                data=st.session_state.board_plan_markdown,
                file_name="board_plan.md",
                mime="text/markdown",
            )

else:
    # Display welcome message and instructions when no files are uploaded
    st.markdown("""
    ## Welcome to the Case Study Analysis Suite
    
    This application provides three powerful tools for analyzing case studies:
    
    1. **Case Breakdown Generator**: Creates a comprehensive breakdown of the case with sections for teaching purposes, formatted as a DOCX document.
    
    2. **Teaching Plan Generator**: Develops a 2-hour lesson plan with activities, discussions, and assessments based on the case study.
    
    3. **Board Plan Generator**: Produces a structured board plan analysis with key insights and implementation details.
    
    ### Getting Started
    
    1. Choose your API provider in the sidebar (Google Gemini or OpenAI)
    2. Enter your API key
    3. Upload one or more case study files in PDF, DOCX, PPT, or PPTX format
    4. Select the generator tab you want to use
    5. Click the generate button and wait for the results
    
    Each generator produces downloadable content in an appropriate format for your use.
    """)

# Footer
st.divider()
st.caption("Created with CrewAI, Streamlit, and Gemini • Built by Arun Kashyap • © 2025")    