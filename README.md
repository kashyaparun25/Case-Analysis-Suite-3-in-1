# Case Study Analysis Suite - README

This project provides a comprehensive suite of tools for analyzing case studies, designed to assist educators and business professionals in extracting key insights, creating teaching materials, and generating structured analyses. The application is built using Streamlit for the user interface, CrewAI for agent orchestration, and supports both Google Gemini and OpenAI for language model capabilities.

## Table of Contents

1.  [Introduction](#introduction)
2.  [Features](#features)
3.  [Architecture Overview](#architecture-overview)
    *   [System Diagram](#system-diagram)
    *   [Component Breakdown](#component-breakdown)
4.  [Agent Descriptions](#agent-descriptions)
    *   [Case Breakdown Generator Agents](#case-breakdown-generator-agents)
    *   [Teaching Plan Generator Agents](#teaching-plan-generator-agents)
    *   [Board Plan Generator Agents](#board-plan-generator-agents)
5.  [Installation and Setup](#installation-and-setup)
    *   [Prerequisites](#prerequisites)
    *   [Installation Steps](#installation-steps)
    *   [API Key Configuration](#api-key-configuration)
6.  [Usage Guide](#usage-guide)
    *   [File Upload](#file-upload)
    *   [Case Breakdown Generator](#case-breakdown-generator)
    *   [Teaching Plan Generator](#teaching-plan-generator)
    *   [Board Plan Generator](#board-plan-generator)
    *   [Session Reset](#session-reset)
7.  [Code Structure](#code-structure)
    *   [Utility Functions](#utility-functions)
    *   [Document Generator (Case Breakdown)](#document-generator-case-breakdown)
    *   [Case Breakdown Generator](#case-breakdown-generator-1)
    *   [Teaching Plan Generator](#teaching-plan-generator-1)
    *   [Board Plan Generator](#board-plan-generator-1)
    *   [Main App Interface](#main-app-interface)
8.  [Dependencies](#dependencies)
9.  [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)
12. [Future Enhancements](#future-enhancements)
13. [Author](#author)

## 1. Introduction

The Case Study Analysis Suite is designed to streamline the process of analyzing business case studies and generating various types of related documents. It leverages the power of AI to automate many of the tedious tasks involved in dissecting case studies, creating teaching materials, and preparing board-level analyses.  The suite supports multiple file formats (PDF, DOCX, PPT, PPTX) and provides downloadable outputs in relevant formats (DOCX, Markdown).

## 2. Features

*   **Case Breakdown Generator:**
    *   Automatically extracts metadata (title, author) from the case study.
    *   Generates a comprehensive Word document (.docx) with predefined sections: Synopsis, Learning Objectives, Teaching Strategies, Suggested Teaching Plan, Key Points, Further Insights, Discussion Questions & Answers, Assignment Exercises, Automated Conversation, and Case Suggestions.
    *   Provides content review and scoring for each section.
    *   Offers a structured, formatted, and customizable output.

*   **Teaching Plan Generator:**
    *   Creates a detailed 2-hour teaching plan based on the uploaded case study.
    *   Includes sections for objectives, introduction, detailed lesson breakdowns, visual aids, assessments, and conclusion.
    *   Provides feedback and iterative refinement of the teaching plan.
    *   Outputs a Markdown (.md) file for easy editing and use.

*   **Board Plan Generator:**
    *   Analyzes the case study and creates a structured board plan suitable for presentations.
    *   Identifies key concepts, industry suitability, benefits, implementation details, and risk assessment.
    *   Outputs a structured JSON and presents it in a user-friendly way.  Generates a Markdown (.md) file for download.

*   **File Handling:**
    *   Supports multiple file uploads (PDF, DOCX, PPT, PPTX).
    *   Combines text from multiple files for comprehensive analysis.
    *   Handles temporary file storage and cleanup.

*   **API Key Management:**
    *   Supports both Google Gemini and OpenAI API keys.
    *   Allows users to switch between providers.
    *   Provides clear instructions for key configuration.

*   **User Interface:**
    *   Intuitive Streamlit-based web interface.
    *   Tabbed layout for easy navigation between generators.
    *   Progress indicators and status updates during processing.
    *   Session reset functionality for starting fresh.

*   **Error Handling:**
     *   Handles different types of errors like API errors, file format errors, and analysis errors.
     *   Displays informative error messages to the user.
     *   Handles cases with encrypted pdf files.

## 3. Architecture Overview

### 3.1. System Diagram

```mermaid
graph TD
    subgraph User Interface [Streamlit Web Application]
        A[User] --> B(File Upload)
        B --> C{File Processing}
        C --> D[Text Extraction]
        D --> E[Session Storage]
        E --> F(Generator Selection: Case Breakdown, Teaching Plan, Board Plan)
        F --> G[Case Breakdown Generator]
        F --> H[Teaching Plan Generator]
        F --> I[Board Plan Generator]
    end

    subgraph CrewAI Orchestration
        G --> G1(Metadata Agent)
        G --> G2(Content Generator Agent)
        G --> G3(Content Reviewer Agent)
        H --> H1(Case Study Analyzer Agent)
        H --> H2(Teaching Plan Designer Agent)
        H --> H3(Plan Reviewer Agent)
        H --> H4(Teaching Plan Reporter Agent)
        I --> I1(PDF Processor Agent)
        I --> I2(Case Study Analyzer Agent)
    end

    subgraph LLM Interaction
        G1 -.-> K(LLM: Gemini/OpenAI)
        G2 -.-> K
        G3 -.-> K
        H1 -.-> K
        H2 -.-> K
        H3 -.-> K
        H4 -.-> K
        I1 -.-> K
        I2 -.-> K
    end
	
	subgraph Output
		G3 --> L[DOCX Output]
		H4 --> M[Markdown Output]
		I2 --> N[Markdown/JSON Output]
	end

    B --> O[API Key Configuration]
    O -.-> K
    
    style K fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#ccf,stroke:#333,stroke-width:2px
    style H fill:#ccf,stroke:#333,stroke-width:2px
    style I fill:#ccf,stroke:#333,stroke-width:2px
