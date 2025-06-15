# PDF Processing Application

A modern web application for processing PDF documents using FastAPI, Redis, and React. The application provides a user-friendly interface for uploading PDFs, processing them asynchronously, and viewing the results.

## Features

- PDF document upload and processing
- Asynchronous processing using Redis and Celery
- Real-time status updates
- Redis content viewer for monitoring and debugging
- Modern React frontend with Material-UI
- FastAPI backend with comprehensive error handling
- Docker-based deployment

## Prerequisites

- Docker and Docker Compose
- Node.js and npm (for frontend development)
- Python 3.8+ (for local development)

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── worker.py
│   │   └── utils.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.js
│   │   ├── PDFUploader.js
│   │   └── RedisViewer.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Setup and Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pdf-processor
   ```

2. Start the backend services using Docker Compose:
   ```bash
   docker compose up --build
   ```
   This will start:
   - FastAPI backend (port 8000)
   - Redis server
   - Celery worker

3. Start the frontend development server:
   ```bash
   cd frontend
   npm install
   npm start
   ```
   The frontend will be available at http://localhost:3000

## Usage

1. **Main Interface (http://localhost:3000)**
   - Upload PDF documents through the drag-and-drop interface
   - View processing status and results
   - Download processed documents

2. **Redis Viewer (http://localhost:3000/redis)**
   - Monitor Redis contents in real-time
   - View task statuses and results
   - Debug processing issues

## API Endpoints

- `POST /upload/`: Upload a PDF file
- `GET /status/{task_id}`: Get processing status
- `GET /redis/contents`: Get Redis contents (for monitoring)

## Development

### Backend Development

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   cd backend
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
   - Verify backend service is running

2. **Processing Status Issues**
   - Check Redis viewer for task status
   - Verify worker service is running
   - Check backend logs for errors

3. **Connection Issues**
   - Ensure all services are running
   - Check port availability
   - Verify network connectivity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 