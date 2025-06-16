# PDF Processing Application

A modern web application for processing PDF documents using FastAPI, Redis, and React. The application provides a user-friendly interface for uploading PDFs and processing them asynchronously using Redis Streams.

## Features

- PDF document upload and processing
- Asynchronous processing using Redis Streams
- Real-time status updates
- Modern React frontend with Material-UI
- FastAPI backend with comprehensive error handling
- Docker-based deployment
- Google Gemini 2.0 Flash AI integration for text extraction and summarization
- Base64 encoding for secure PDF content handling
- Improved error handling and validation

## Prerequisites

- Docker and Docker Compose
- Node.js and npm (for frontend development)
- Python 3.8+ (for local development)
- Google API Key for Gemini AI

## Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI application and API endpoints
│   └── worker.py        # Redis worker for async processing
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   └── PDFUploader.js
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   └── package-lock.json
├── requirements.txt
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pdf-processor
   ```

2. Create a `.env` file in the root directory with your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

3. Start the backend services using Docker Compose:
   ```bash
   docker compose up --build
   ```
   This will start:
   - FastAPI backend (port 8000)
   - Redis server
   - Worker process
   - React frontend (port 3000)

## Usage

1. **Main Interface (http://localhost:3000)**
   - Upload PDF documents through the interface
   - Choose between PyPDF or Gemini AI for processing
   - View real-time processing status
   - See extracted text and generated summary
   - View any processing errors

2. **Processing Options**
   - PyPDF: Basic text extraction
   - Gemini AI: Advanced text extraction with markdown formatting and summarization

## API Endpoints

- `POST /upload`: Upload a PDF file
  - Parameters:
    - `file`: PDF file
    - `parser`: Processing method ("pypdf" or "gemini")
  - Returns: Document ID and initial status

- `GET /status/{doc_id}`: Get processing status
  - Returns:
    - Status: "processing", "completed", or "error"
    - Content: Extracted text in markdown format
    - Summary: Generated summary
    - Error: Error message if processing failed

## Development

### Backend Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Development

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

## Docker Commands

- Build and start all services:
  ```bash
  docker compose up --build
  ```

- Stop all services:
  ```bash
  docker compose down
  ```

- View logs:
  ```bash
  docker compose logs -f
  ```

## Troubleshooting

1. **PDF Upload Issues**
   - Check file size (max 10MB)
   - Ensure PDF is not corrupted
   - Verify PDF header is valid
   - Check backend service is running

2. **Processing Status Issues**
   - Verify worker service is running
   - Check backend logs for errors
   - Ensure Redis connection is working
   - Verify Google API key is valid

3. **Connection Issues**
   - Ensure all services are running
   - Check port availability
   - Verify network connectivity
   - Check CORS settings if accessing from different domains

## Recent Updates

- Upgraded to Gemini 2.0 Flash model for improved text extraction
- Added base64 encoding for secure PDF content handling
- Improved error handling and validation
- Enhanced status reporting and error messages
- Fixed Redis status encoding issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 