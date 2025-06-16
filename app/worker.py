import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv
import asyncio
import logging
import traceback
import base64
from utils import get_redis_client, REDIS_HOST, REDIS_PORT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Redis stream configuration
REDIS_STREAM = "pdf_tasks"
REDIS_GROUP = "pdf_workers"
REDIS_CONSUMER = "worker-1"

async def process_document(doc_id: str, content: str, parser: str):
    """Process a document using the specified parser."""
    redis_client = await get_redis_client(decode_responses=True)
    try:
        logger.info(f"Starting to process document {doc_id} with parser {parser}")
        
        # Update status to processing
        await redis_client.hset(
            f"document:{doc_id}",
            mapping={
                "status": "processing",
                "progress": "Starting PDF processing...",
                "current_step": "init",
                "total_steps": "5",
                "current_step_number": "0"
            }
        )
        
        # Decode base64 content
        try:
            await redis_client.hset(
                f"document:{doc_id}",
                mapping={
                    "progress": "Decoding PDF content...",
                    "current_step": "decode",
                    "current_step_number": "1"
                }
            )
            content_bytes = base64.b64decode(content)
        except Exception as e:
            logger.error(f"Error decoding base64 content: {str(e)}")
            await redis_client.hset(
                f"document:{doc_id}",
                mapping={
                    "status": "error",
                    "error": "Invalid content format in Redis",
                    "progress": "Failed to decode PDF content"
                }
            )
            raise ValueError("Invalid content format in Redis")
        
        # Process with selected parser
        if parser == "gemini":
            logger.info("Using Gemini parser")
            try:
                # Convert PDF to images
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "progress": "Converting PDF to images...",
                        "current_step": "convert",
                        "current_step_number": "2"
                    }
                )
                
                from main import process_with_gemini
                result = await process_with_gemini(content_bytes, doc_id, redis_client)
                
                # Update Redis with results
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "status": "completed",
                        "content": result["content"],
                        "summary": result["summary"],
                        "progress": "Processing completed successfully",
                        "current_step": "complete",
                        "current_step_number": "5"
                    }
                )
                logger.info(f"Successfully processed document {doc_id}")
            except ValueError as ve:
                # Handle validation errors
                logger.error(f"Validation error for document {doc_id}: {str(ve)}")
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "status": "error",
                        "error": str(ve),
                        "progress": f"Error: {str(ve)}"
                    }
                )
                raise
        elif parser == "pypdf":
            logger.info("Using PyPDF parser")
            try:
                # Process with PyPDF
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "progress": "Processing with PyPDF...",
                        "current_step": "process",
                        "current_step_number": "2"
                    }
                )
                
                from main import process_with_pypdf
                result = await process_with_pypdf(content_bytes)
                
                # Update Redis with results
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "status": "completed",
                        "content": result["content"],
                        "summary": result["summary"],
                        "progress": "Processing completed successfully",
                        "current_step": "complete",
                        "current_step_number": "5"
                    }
                )
                logger.info(f"Successfully processed document {doc_id}")
            except Exception as e:
                logger.error(f"Error processing with PyPDF: {str(e)}")
                await redis_client.hset(
                    f"document:{doc_id}",
                    mapping={
                        "status": "error",
                        "error": str(e),
                        "progress": f"Error: {str(e)}"
                    }
                )
                raise
        else:
            raise ValueError(f"Unsupported parser: {parser}")
            
    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {str(e)}")
        logger.error(f"Traceback: {e.__traceback__}")
        # Update Redis with error status
        await redis_client.hset(
            f"document:{doc_id}",
            mapping={
                "status": "error",
                "error": str(e),
                "progress": f"Error: {str(e)}"
            }
        )
        raise

async def main():
    """Main worker loop."""
    try:
        # Connect to Redis
        redis_client = await get_redis_client(decode_responses=True)
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
        
        # Create consumer group if it doesn't exist
        try:
            await redis_client.xgroup_create(REDIS_STREAM, REDIS_GROUP, mkstream=True)
            logger.info("Created Redis stream group")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info("Redis stream group already exists")
            else:
                raise
        
        logger.info("Waiting for new messages in Redis stream...")
        
        while True:
            try:
                # Read from stream with blocking
                response = await redis_client.xreadgroup(
                    REDIS_GROUP,
                    REDIS_CONSUMER,
                    {REDIS_STREAM: ">"},
                    count=1,
                    block=5000
                )
                
                if not response:
                    logger.info("No messages received, continuing...")
                    continue
                    
                # Process the message
                stream, messages = response[0]
                for message_id, message_data in messages:
                    try:
                        doc_id = message_data["doc_id"]
                        content = message_data["content"]
                        parser = message_data["parser"]
                        
                        logger.info(f"Received new message {message_id}")
                        logger.info(f"Processing message for document: {doc_id}")
                        
                        # Process the document
                        await process_document(doc_id, content, parser)
                        
                        # Acknowledge the message
                        await redis_client.xack(REDIS_STREAM, REDIS_GROUP, message_id)
                        logger.info(f"Acknowledged message {message_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {str(e)}")
                        logger.error(f"Traceback: {e.__traceback__}")
                        # Don't acknowledge the message so it can be retried
                        continue
                    
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                logger.error(f"Traceback: {e.__traceback__}")
                continue
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    asyncio.run(main()) 