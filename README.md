---
title: HireBox
emoji: 🚀
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# HireBox - AI-Powered Interview & Proctoring Platform

HireBox is a comprehensive AI-driven recruitment platform designed to streamline the hiring process. It automates resume screening, conducts secure AI-led interviews with real-time proctoring, and provides detailed candidate performance analysis.

## Key Features

### 🤖 AI-Powered Interviewer
- Generates dynamic, context-aware interview questions based on the candidate's resume and job description.
- Utilizes Google's Gemini AI to analyze answers for technical accuracy, clarity, and relevance.
- Supports voice interaction with live speech-to-text transcription.

### 👁️ Advanced Monitoring & Proctoring
- **Real-time Computer Vision**: Uses YOLOv8 and Haar Cascades to detect cheating behaviors.
- **Violation Logging**: Automatically flags:
    - Multiple faces in frame.
    - No face detected (absence).
    - Mobile phone usage (expanded object detection).
    - Tab switching/Window minimization.
- **Secure Environment**: Enforces fullscreen and blocks right-clicks.

### 📄 Intelligent Resume Parsing
- Extracts skills, experience, and contact details from PDF/DOCX resumes.
- Ranks candidates automatically based on semantic matching with job descriptions.

### 📊 Comprehensive Reporting
- Generates detailed scorecards for HR.
- Provides emotional analysis and behavioral insights.
- Tracks violation history with timestamps.

## Technology Stack

- **Backend**: Python, Flask, SQLAlchemy (SQLite)
- **AI/ML**: 
    - Google Gemini (GenAI) for Logic & Q/A
    - YOLOv8 (Ultralytics) for Object Detection
    - OpenCV for Video Processing
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), TailwindCSS (for some components)
- **Database**: SQLite

## Setup & Installation

The project includes automated scripts for easy setup on Windows.

1.  **Initialize the Project**
    Run `init.bat` to create the virtual environment, install dependencies, and run database migrations.
    ```cmd
    .\init.bat
    ```

2.  **Run the Application**
    Start the server using `run.bat`.
    ```cmd
    .\run.bat
    ```
    Access the application at `http://localhost:5000`.

## Usage Guide

1.  **HR Dashboard**: Login to create jobs and upload candidate resumes.
2.  **Ranking**: View auto-ranked candidates based on job fit.
3.  **Interview Setup**: Configure interview parameters (time limit, question count) and generate a secure link.
4.  **Candidate Interview**: Candidates access the link to take the proctored interview.
5.  **Review**: Check detailed reports and proctoring logs after completion.

## Project Structure

- `app/`: Core application logic (Routes, Models, Services).
- `migrations/`: Database migration scripts.
- `uploads/`: Storage for candidate resumes.
- `test_resumes/`: Sample data for testing.
- `yolov8n.pt`: Pre-trained YOLO model weights.

---
