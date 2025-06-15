import redis
import os
import json
from dotenv import load_dotenv
import asyncio
from main import process_with_pypdf, process_with_gemini, generate_summary
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Redis client
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

# Verify Redis connection
try:
    redis_client.ping()
    logger.info("Successfully connected to Redis")
except redis.ConnectionError as e:
    logger.error(f"Failed to connect to Redis: {str(e)}")
    raise

async def process_document(doc_id: str, content: bytes, parser: str):
    try:
        logger.info(f"Starting to process document {doc_id} with parser {parser}")
        
        # Process the document based on the chosen parser
        if parser == "pypdf":
            logger.info("Using PyPDF parser")
            text = await process_with_pypdf(content)
            logger.info(f"Generated text from PDF (length: {len(text)})")
            summary = await generate_summary(text)
            logger.info(f"Generated summary (length: {len(summary)})")
        else:  # gemini
            logger.info("Using Gemini parser")
            result = await process_with_gemini(content)
            logger.info(f"Generated result from Gemini (length: {len(result)})")
            # Split the result into markdown and summary
            parts = result.split("SUMMARY:")
            text = parts[0].replace("MARKDOWN:", "").strip()
            summary = parts[1].strip() if len(parts) > 1 else ""

        # Update the document status in Redis
        logger.info(f"Updating Redis with results for {doc_id}")
        redis_client.hset(f"task:{doc_id}", mapping={
            "status": "completed",
            "content": text,
            "summary": summary
        })
        logger.info(f"Successfully processed {doc_id}")
    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {str(e)}")
        logger.error(traceback.format_exc())
        # Update status to error if processing fails
        redis_client.hset(f"task:{doc_id}", mapping={
            "status": "error",
            "error": str(e)
        })

async def main():
    logger.info("Starting PDF processing worker...")
    last_id = "0"
    
    # Create the stream if it doesn't exist
    try:
        redis_client.xgroup_create("pdf_processing", "pdf_workers", mkstream=True)
        logger.info("Created Redis stream group: pdf_workers")
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info("Redis stream group already exists")
        else:
            logger.error(f"Error creating Redis stream group: {str(e)}")
            raise
    
    while True:
        try:
            # Read from the stream
            logger.info("Waiting for new messages in Redis stream...")
            stream_data = redis_client.xreadgroup(
                "pdf_workers",
                "worker1",
                {"pdf_processing": ">"},
                count=1,
                block=1000
            )
            
            if not stream_data:
                logger.debug("No new messages in stream")
                continue
                
            for stream_id, messages in stream_data:
                for message_id, message in messages:
                    last_id = message_id
                    logger.info(f"Received new message {message_id}")
                    
                    # Extract message data
                    doc_id = message["doc_id"]
                    content = bytes.fromhex(message["content"])
                    parser = message["parser"]
                    
                    logger.info(f"Processing message for document: {doc_id}")
                    # Process the document
                    await process_document(doc_id, content, parser)
                    
                    # Acknowledge the message
                    redis_client.xack("pdf_processing", "pdf_workers", message_id)
                    logger.info(f"Acknowledged message {message_id}")
                    
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            logger.error(traceback.format_exc())
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main()) 