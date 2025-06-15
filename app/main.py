from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import os
from typing import Literal
import google.generativeai as genai
from pypdf import PdfReader
import io
from dotenv import load_dotenv
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Verify Redis connection
try:
    redis_client.ping()
    logger.info("Successfully connected to Redis")
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    raise

# Initialize Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

async def process_with_pypdf(file_content: bytes) -> str:
    logger.info("Processing PDF with PyPDF")
    pdf_file = io.BytesIO(file_content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    logger.info(f"Successfully extracted text from PDF (length: {len(text)})")
    return text

async def process_with_gemini(file_content: bytes) -> str:
    logger.info("Processing PDF with Gemini")
    pdf_file = io.BytesIO(file_content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    # Use Gemini to convert to markdown and summarize
    prompt = f"""Convert the following text to markdown format and provide a concise summary:

{text}

Please format the response as:
MARKDOWN:
[markdown formatted text]

SUMMARY:
[concise summary]"""
    
    try:
        response = model.generate_content(prompt)
        logger.info(f"Successfully generated markdown and summary with Gemini (length: {len(response.text)})")
        return response.text
    except Exception as e:
        logger.error(f"Error generating content with Gemini: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def generate_summary(text: str) -> str:
    logger.info("Generating summary with Gemini")
    prompt = f"Provide a concise summary of the following text:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        logger.info(f"Successfully generated summary (length: {len(response.text)})")
        return response.text
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    parser: Literal["pypdf", "gemini"] = "pypdf"
):
    logger.info(f"Received upload request for file: {file.filename} with parser: {parser}")
    
    if not file.filename.endswith('.pdf'):
        logger.error(f"Invalid file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    content = await file.read()
    logger.info(f"Read {len(content)} bytes from file")
    
    # Generate a unique ID for this document
    doc_id = f"doc:{file.filename}"
    
    try:
        # Store initial status
        redis_client.hset(doc_id, mapping={
            "status": "processing",
            "filename": file.filename,
            "parser": parser
        })
        logger.info(f"Stored initial status in Redis for {doc_id}")
        
        # Add to Redis Stream for processing
        stream_data = {
            "doc_id": doc_id,
            "content": content.hex(),  # Store binary content as hex
            "parser": parser
        }
        stream_id = redis_client.xadd("pdf_processing", stream_data)
        logger.info(f"Added {doc_id} to processing stream with ID: {stream_id}")
        
        return {"doc_id": doc_id, "status": "processing"}
    except Exception as e:
        logger.error(f"Error storing document in Redis: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error processing document")

@app.get("/status/{doc_id}")
async def get_status(doc_id: str):
    logger.info(f"Checking status for {doc_id}")
    try:
        doc_data = redis_client.hgetall(doc_id)
        if not doc_data:
            logger.error(f"Document not found: {doc_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        status = doc_data.get(b"status", b"").decode()
        logger.info(f"Status for {doc_id}: {status}")
        
        return {
            "status": status,
            "filename": doc_data.get(b"filename", b"").decode(),
            "content": doc_data.get(b"content", b"").decode() if b"content" in doc_data else None,
            "summary": doc_data.get(b"summary", b"").decode() if b"summary" in doc_data else None
        }
    except Exception as e:
        logger.error(f"Error retrieving status for {doc_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error retrieving document status")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info"
    ) 