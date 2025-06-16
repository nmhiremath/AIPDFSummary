# AI PDF Summary

A web application that processes PDF documents using either PyPDF or Google's Gemini Vision API to extract and summarize content.

## Features

- Upload and process PDF documents
- Choose between two parsers:
  - **PyPDF**: Fast text extraction with basic formatting
  - **Gemini Vision**: Advanced AI-powered extraction with better formatting preservation
- Real-time processing status updates
- Markdown-formatted content display
- Concise document summaries

## Parser Comparison

### PyPDF Parser
- Faster processing
- Basic text extraction
- Simple markdown formatting
- Best for text-heavy documents
- No image processing

### Gemini Vision Parser
- AI-powered text extraction
- Preserves document formatting:
  - Maintains heading hierarchy
  - Preserves hyperlinks and URLs
  - Keeps contact information as clickable links
  - Maintains relative text sizes
  - Preserves lists and indentation
- Processes both text and images
- Better handling of complex layouts
- More accurate representation of the original document structure

## Summary Format

Both parsers generate summaries in a consistent format:
1. Concise overview
2. Key points in bullet format
3. Important details or insights

## Getting Started

1. Clone the repository
2. Create a `.env` file with your Google API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```
3. Start the services:
   ```bash
   docker compose up --build
   ```
4. Access the application at http://localhost:3000

## Requirements

- Docker and Docker Compose
- Google API key for Gemini Vision API
- Python 3.9+
- Node.js 14+

## Architecture

- Frontend: React with Material-UI
- Backend: FastAPI
- Worker: Python with Redis for task queue
- Database: Redis for document storage

## Development

The application uses a microservices architecture:
- `frontend/`: React application
- `app/`: FastAPI backend
- `worker/`: PDF processing worker
- `redis/`: Redis instance for task queue and storage

## License

MIT 