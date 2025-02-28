# 📚 Case Study Analysis Suite

Welcome to the **Case Study Analysis Suite**, an integrated application designed to streamline the creation of comprehensive case study materials. This suite offers three primary functionalities:

1. **Case Breakdown Generator**: Produces detailed teaching notes, also known as case breakdowns, in a well-structured DOCX format.
2. **Teaching Plan Generator**: Develops a 2-hour lesson plan complete with introductions, analyses, group activities, and assessments, presented in Markdown format.
3. **Board Plan Generator**: Generates a structured board plan analysis highlighting key insights and implementation details, also in Markdown format.

## Features

- **User-Friendly Interface**: Built with Streamlit for an intuitive and responsive user experience.
- **Multi-Format Support**: Accepts case study files in PDF, DOCX, PPT, and PPTX formats.
- **Automated Content Generation**: Utilizes AI agents to analyze content and generate comprehensive teaching materials.
- **Downloadable Outputs**: Provides outputs in DOCX and Markdown formats for easy integration into your teaching resources.

## Application Architecture

The application is structured around specialized AI agents, each assigned specific roles and tasks to ensure a smooth and efficient workflow.

### 1. Case Breakdown Generator

This module involves three key agents:

- **Metadata Analyzer Agent**: Extracts essential metadata, such as the case study title and author(s), from the uploaded documents.
- **Case Study Content Generator Agent**: Generates detailed content for each section of the case breakdown based on predefined templates.
- **Content Quality Reviewer Agent**: Evaluates the generated content for quality, relevance, and depth, providing structured feedback for improvements.

**Tasks Assigned:**

- **Create Metadata Task**: Analyzes the extracted text to identify the case study title and author(s).
- **Create Section Task**: Generates content for each section of the case breakdown using the provided templates.
- **Create Review Task**: Reviews the content of each section, offering feedback and scoring based on predefined criteria.

### 2. Teaching Plan Generator

This module comprises four agents:

- **Case Study Analyzer Agent**: Extracts key concepts, objectives, and data from the case study files.
- **Teaching Plan Designer Agent**: Crafts a detailed 2-hour lesson plan incorporating introductions, analyses, group activities, and assessments.
- **Plan Reviewer Agent**: Reviews the lesson plan for clarity, alignment with learning objectives, and student engagement, providing constructive feedback.
- **Teaching Plan Reporter Agent**: Incorporates feedback to finalize and format the teaching plan, ensuring it meets educational standards.

**Tasks Assigned:**

- **Analyze PDF Task**: Extracts and analyzes the content of the uploaded files to identify key concepts and learning objectives.
- **Generate Plan Task**: Designs a comprehensive 2-hour lesson plan with structured activities and assessments.
- **Review Plan Task**: Evaluates the lesson plan's clarity, alignment with objectives, and engagement level, offering feedback for enhancements.
- **Final Plan Task**: Integrates reviewer feedback to produce a polished and well-structured teaching plan.

### 3. Board Plan Generator

This module includes two agents:

- **PDF Processor Agent**: Extracts and cleans text content from the uploaded case study files.
- **Case Study Analyzer Agent**: Analyzes the cleaned content to identify key points and insights for the board plan.

**Tasks Assigned:**

- **Extract Text Task**: Processes the uploaded files to extract and clean text content.
- **Analyze Case Study Task**: Evaluates the extracted content to create a structured board plan highlighting main concepts, industry context, benefits, key roles, implementation details, and risk assessments.

## Getting Started

To utilize the Case Study Analysis Suite:

1. **API Configuration**: Enter your API key in the sidebar to enable AI functionalities.
2. **File Upload**: Upload your case study files in PDF, DOCX, PPT, or PPTX formats.
3. **Select Module**: Choose the desired generator tab (Case Breakdown, Teaching Plan, or Board Plan).
4. **Generate Content**: Click the generate button and allow the application to process the files and produce the desired outputs.
5. **Download Outputs**: Once generated, download the outputs in DOCX or Markdown formats as needed.

## Dependencies

The application relies on the following libraries:

- `streamlit`: For building the web interface.
- `python-docx`: For creating and manipulating Word documents.
- `PyPDF2`: For extracting text from PDF files.
- `python-pptx`: For handling PowerPoint files.
- `docx2txt`: For extracting text from DOCX files.
- `dotenv`: For loading environment variables.
- `litellm`: For interacting with language models.
- `langchain`: For managing AI agents and tasks.
- `crewai`: For orchestrating AI agents and workflows.

Ensure these dependencies are installed in your environment to run the application successfully.

## Contributing

Contributions to the Case Study Analysis Suite are welcome. If you have suggestions for improvements or encounter any issues, please submit them via the GitHub repository's issue tracker.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

*Created with CrewAI, Streamlit, and Gemini • Built by Arun Kashyap • © 2025*
