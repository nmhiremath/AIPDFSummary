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
import uuid

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    logger.info(f"Created uploads directory at {UPLOAD_DIR}")

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
genai.configure(api_key=api_key)

# Initialize Gemini model
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
async def upload_file(file: UploadFile = File(...), parser: str = "pypdf"):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique document ID
    doc_id = str(uuid.uuid4())
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create task in Redis
    task_data = {
        "doc_id": doc_id,
        "content": content.hex(),
        "parser": parser,
        "status": "processing"
    }
    
    # Add to Redis Stream
    redis_client.xadd("pdf_processing", task_data)
    
    return {"doc_id": doc_id, "status": "processing"}

@app.get("/status/{doc_id}")
async def get_status(doc_id: str):
    # Get task status from Redis
    task_key = f"task:{doc_id}"
    task_data = redis_client.hgetall(task_key)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "status": task_data.get("status", "unknown"),
        "content": task_data.get("content", ""),
        "summary": task_data.get("summary", "")
    }

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