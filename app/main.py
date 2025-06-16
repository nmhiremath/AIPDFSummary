from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
import os
from typing import Literal, Dict
import google.generativeai as genai
from pypdf import PdfReader
import io
from dotenv import load_dotenv
import logging
import traceback
import uuid
import asyncio
import base64
from pdf2image import convert_from_bytes
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
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

# Redis configuration
REDIS_STREAM = "pdf_tasks"
REDIS_GROUP = "pdf_workers"

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

# Define prompts for Gemini
text_extraction_prompt = """You are a PDF text extractor. Your task is to extract ALL text content from the provided image of a PDF page.

IMPORTANT:
1. Extract ONLY the actual text you see in the image
2. Preserve the exact text, including numbers, symbols, and formatting
3. Do not add any explanations or meta-commentary
4. Do not make assumptions about the content
5. If you cannot read some text clearly, indicate with [unclear text]
6. Do not include any instructions or examples in your response
7. Do not include any markdown formatting
8. Output ONLY the raw text content you see in the image

Output the raw text content only."""

markdown_conversion_prompt = """You are a text to markdown converter. Convert the following text into clean markdown format.

IMPORTANT:
1. Preserve the exact content and meaning
2. Use markdown syntax for:
   - Headers (# for main headers, ## for subheaders, etc.)
   - Lists (- for bullet points, 1. 2. 3. for numbered lists)
   - Tables (using | and -)
   - Emphasis (* for italic, ** for bold)
3. Do not add any explanations or meta-commentary
4. Do not modify the actual content
5. Keep the original structure and hierarchy
6. Do not include any instructions or examples in your response
7. Output ONLY the markdown-formatted text

Output only the markdown-formatted text."""

summary_prompt = """You are a document summarizer. Your task is to provide a concise summary of the following document.

IMPORTANT:
1. Summarize ONLY the actual content provided
2. Focus on the main points and key information
3. Do not add any meta-commentary or explanations
4. Do not make assumptions about the content
5. Keep the summary factual and based only on the provided text

Provide a clear, concise summary focusing on the main points and key information."""

async def process_with_pypdf(file_content: bytes) -> str:
    logger.info("Processing PDF with PyPDF")
    pdf_file = io.BytesIO(file_content)
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    logger.info(f"Successfully extracted text from PDF (length: {len(text)})")
    return text

async def process_with_gemini(pdf_content: bytes):
    """Process PDF content using Gemini Vision API."""
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Convert PDF to images
        logger.info("Converting PDF to images")
        images = convert_from_bytes(pdf_content)
        logger.info(f"Successfully converted PDF to {len(images)} images")
        
        if not images:
            raise ValueError("No images could be extracted from the PDF")
        
        # Process each page
        all_text = []
        all_markdown = []
        
        for i, image in enumerate(images, 1):
            logger.info(f"Processing page {i}")
            
            # Save image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            logger.info(f"Saved image for page {i}, size: {len(img_byte_arr)} bytes")
            logger.info(f"Image dimensions for page {i}: {image.size[0]}x{image.size[1]}")
            
            # Extract text using Gemini Vision
            logger.info(f"Extracting text from page {i}")
            response = await model.generate_content_async([
                "Extract all text from this image, preserving formatting and structure. Include headers, paragraphs, lists, and any other text elements. Return the text exactly as it appears in the image.",
                {"mime_type": "image/png", "data": img_byte_arr}
            ])
            
            if not response.text:
                logger.warning(f"No text extracted from page {i}")
                continue
                
            all_text.append(response.text)
            
            # Convert to markdown
            logger.info(f"Converting page {i} to markdown")
            markdown_response = await model.generate_content_async([
                "Convert this text into clean, well-formatted markdown. Preserve the structure, headers, lists, and formatting. Make it readable and properly formatted.",
                response.text
            ])
            
            if not markdown_response.text:
                logger.warning(f"Failed to convert page {i} to markdown")
                continue
                
            all_markdown.append(markdown_response.text)
        
        if not all_text:
            raise ValueError("No text could be extracted from any page")
        
        # Generate summary
        logger.info("Generating summary")
        summary_response = await model.generate_content_async([
            "Generate a concise summary of this text. Focus on the main points and key information.",
            "\n\n".join(all_text)
        ])
        
        if not summary_response.text:
            logger.warning("Failed to generate summary")
            summary = "Summary generation failed"
        else:
            summary = summary_response.text
        
        return {
            "content": "\n\n".join(all_markdown),
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise

async def generate_summary(text: str) -> str:
    logger.info("Generating summary with Gemini")
    prompt = f"""Provide a concise summary of the following text, focusing on the main points and key information:

{text}"""
    try:
        response = model.generate_content(prompt)
        logger.info(f"Successfully generated summary (length: {len(response.text)})")
        return response.text
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), parser: str = Form("pypdf")):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    logger.info(f"Received upload request with parser: {parser}")
    
    # Read file content
    content = await file.read()
    
    # Validate PDF header
    if not content.startswith(b'%PDF-'):
        raise HTTPException(status_code=400, detail="Invalid PDF file: File does not start with PDF header")
    
    # Generate unique document ID
    doc_id = str(uuid.uuid4())
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Create task in Redis
    task_data = {
        "doc_id": doc_id,
        "content": base64.b64encode(content).decode('utf-8'),  # Store as base64
        "parser": parser,
        "status": "processing"
    }
    
    logger.info(f"Sending task to Redis with parser: {parser}")
    
    # Add to Redis Stream
    redis_client.xadd(REDIS_STREAM, task_data)
    
    # Create initial task hash in Redis
    redis_client.hset(f"doc:{doc_id}", mapping={
        "status": "processing"
    })
    
    return {"doc_id": doc_id, "status": "processing"}

@app.get("/status/{doc_id}")
async def get_status(doc_id: str):
    # Get task status from Redis
    task_key = f"doc:{doc_id}"
    task_data = redis_client.hgetall(task_key)
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "status": task_data.get("status", "unknown"),
        "content": task_data.get("content", ""),
        "summary": task_data.get("summary", ""),
        "error": task_data.get("error", "")
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