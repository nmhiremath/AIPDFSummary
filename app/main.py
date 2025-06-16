from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import os
from typing import Dict
import google.generativeai as genai
from pypdf import PdfReader
from dotenv import load_dotenv
import logging
import traceback
import uuid
import base64
from pdf2image import convert_from_bytes
from utils import get_redis_client
from io import BytesIO

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

async def process_with_pypdf(content: bytes) -> dict:
    """Process PDF content using PyPDF."""
    try:
        logger.info("Processing PDF with PyPDF")
        
        # Create a BytesIO object from the content
        pdf_file = BytesIO(content)
        
        # Create PDF reader
        pdf_reader = PdfReader(pdf_file)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        logger.info(f"Successfully extracted text from PDF (length: {len(text)})")
        
        # Generate summary using Gemini
        prompt = f"""Please analyze the following text and provide a plain text summary (no markdown formatting) with:
just a single paragraph of a concise summary (2-5 sentences)

Text:
{text[:10000]}  # Limit to first 10000 chars to avoid token limits
"""
        
        response = await model.generate_content_async(prompt)
        summary = response.text
        
        # Convert the content to markdown format
        markdown_content = f"""

{text}

---
*This content was extracted using PyPDF and formatted in markdown.*"""
        
        return {
            "content": markdown_content,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error in process_with_pypdf: {str(e)}")
        raise

async def process_with_gemini(pdf_content: bytes, doc_id: str, redis_client) -> dict:
    """Process PDF content using Google's Gemini Vision API."""
    try:
        # Convert PDF to images
        images = convert_from_bytes(pdf_content)
        total_pages = len(images)
        
        # Process each page
        all_text = []
        for i, image in enumerate(images, 1):
            # Update progress
            await redis_client.hset(
                f"document:{doc_id}",
                mapping={
                    "progress": f"Processing page {i}/{total_pages}",
                    "current_step": "process",
                    "current_step_number": "3"
                }
            )
            
            # Convert image to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Process with Gemini
            response = await model.generate_content_async([
                """Extract and format the text from this image while preserving the exact structure and formatting of the original document. Follow these guidelines:

1. Preserve all original formatting:
   - Keep exact text alignment and spacing
   - Maintain original line breaks and paragraphs
   - Preserve any special characters or symbols
   - Keep original indentation and lists
   - Maintain relative text sizes and proportions
   - Preserve all hyperlinks and URLs exactly as they appear

2. Use markdown formatting to represent the structure:
   - For headings, observe the visual hierarchy and use appropriate # levels:
     * Main title (largest): Use # (h1)
     * Major section: Use ## (h2)
     * Subsection: Use ### (h3)
     * Minor section: Use #### (h4)
     * Small section: Use ##### (h5)
     * Smallest heading: Use ###### (h6)
   - For hyperlinks and URLs:
     * Use [text](url) format for all links
     * Preserve email addresses as mailto: links
     * Preserve phone numbers as tel: links
     * Keep all URLs exactly as they appear
   - Use - or * for bullet points
   - Use 1. 2. 3. for numbered lists
   - Use > for blockquotes
   - Use ** for bold and * for italic text
   - Use ``` for code blocks
   - Use | and - for tables

3. Important:
   - Do not add any commentary or instructions
   - Do not modify or interpret the content
   - Keep the exact text as it appears
   - Preserve the visual hierarchy of the document
   - If text is unclear, mark it as [unclear text]
   - If there are images, describe them as [image: description]
   - Pay special attention to heading sizes and their relative proportions
   - Use heading levels that match the visual importance in the original document
   - If a heading is visually smaller than the main title, use a higher number of # symbols
   - For contact information (email, phone, website):
     * Always preserve as clickable links
     * Keep the exact format of the original
     * Include all protocol prefixes (http://, https://, mailto:, tel:)
   - For sections like "Professional Summary" or "Work Experience":
     * Use appropriate heading level based on visual size
     * Do not make them larger than they appear in the original
     * Maintain the same relative size compared to other headings

Output only the formatted text without any additional commentary.""",
                {
                    "mime_type": "image/png",
                    "data": img_str
                }
            ])
            
            # Clean up the response text
            text = response.text.strip()
            if text:
                all_text.append(text)
        
        # Combine all text and format as markdown
        content = "\n\n".join(all_text)
        
        # Add markdown header and footer
        markdown_content = f"""

{content}

---
*This content was extracted using Google's Gemini Vision API and formatted in markdown.*"""
        
        # Generate summary
        await redis_client.hset(
            f"document:{doc_id}",
            mapping={
                "progress": "Generating summary...",
                "current_step": "summary",
                "current_step_number": "4"
            }
        )
        
        summary_prompt = f"""Please analyze the following text and provide a plain text summary (no markdown formatting) with:
just a single paragraph of a concise summary (2-5 sentences)

Text:
{content[:10000]}  # Limit to first 10000 chars to avoid token limits
"""
        
        summary_response = await model.generate_content_async(summary_prompt)
        summary = summary_response.text
        
        return {
            "content": markdown_content,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error in process_with_gemini: {str(e)}")
        raise

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), parser: str = Form("pypdf")):
    """Upload a PDF file and process it."""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        logger.info(f"Received upload request with parser: {parser}")
        
        # Read file content
        content = await file.read()
        
        # Validate PDF header
        if not content.startswith(b'%PDF-'):
            raise HTTPException(status_code=400, detail="Invalid PDF file: File does not start with PDF header")
        
        # Generate a unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Encode content as base64
        content_b64 = base64.b64encode(content).decode('utf-8')
        
        # Get Redis client
        redis_client = await get_redis_client(decode_responses=True)
        
        # Create task data
        task_data = {
            "doc_id": doc_id,
            "content": content_b64,
            "parser": parser
        }
        
        # Send task to Redis stream
        logger.info(f"Sending task to Redis with parser: {parser}")
        await redis_client.xadd(REDIS_STREAM, task_data)
        
        # Set initial status
        await redis_client.hset(f"document:{doc_id}", mapping={
            "status": "queued",
            "progress": "Task queued for processing",
            "current_step": "init",
            "total_steps": "5",
            "current_step_number": "0"
        })
        
        return {"message": "File uploaded successfully", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{document_id}")
async def get_status(document_id: str):
    """Get the status of a document processing task."""
    try:
        redis_client = await get_redis_client(decode_responses=True)
        task_data = await redis_client.hgetall(f"document:{document_id}")
        
        if not task_data:
            raise HTTPException(status_code=404, detail="Document not found")
            
        return {
            "status": task_data.get("status", "unknown"),
            "content": task_data.get("content", ""),
            "summary": task_data.get("summary", ""),
            "error": task_data.get("error", ""),
            "progress": task_data.get("progress", ""),
            "current_step": task_data.get("current_step", ""),
            "total_steps": task_data.get("total_steps", "0"),
            "current_step_number": task_data.get("current_step_number", "0")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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