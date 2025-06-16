import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv
import asyncio
from main import process_with_pypdf, process_with_gemini, generate_summary
import logging
import traceback
import base64

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Redis client
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_STREAM = "pdf_tasks"
REDIS_GROUP = "pdf_workers"
REDIS_CONSUMER = "worker-1"

async def get_redis_client(decode_responses=True):
    """Get a Redis client with the specified configuration."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=decode_responses
    )

async def process_document(doc_id: str, content: str, parser: str):
    """Process a document using the specified parser."""
    redis_client = await get_redis_client(decode_responses=True)
    try:
        logger.info(f"Starting to process document {doc_id} with parser {parser}")
        
        # Decode base64 content
        try:
            content_bytes = base64.b64decode(content)
        except Exception as e:
            logger.error(f"Error decoding base64 content: {str(e)}")
            await redis_client.hset(
                f"doc:{doc_id}",
                mapping={
                    "status": "error",
                    "error": "Invalid content format in Redis"
                }
            )
            raise ValueError("Invalid content format in Redis")
        
        # Process with Gemini
        if parser == "gemini":
            logger.info("Using Gemini parser")
            try:
                result = await process_with_gemini(content_bytes)
                
                # Update Redis with results
                await redis_client.hset(
                    f"doc:{doc_id}",
                    mapping={
                        "status": "completed",
                        "content": result["content"],
                        "summary": result["summary"]
                    }
                )
                logger.info(f"Successfully processed document {doc_id}")
            except ValueError as ve:
                # Handle validation errors
                logger.error(f"Validation error for document {doc_id}: {str(ve)}")
                await redis_client.hset(
                    f"doc:{doc_id}",
                    mapping={
                        "status": "error",
                        "error": str(ve)
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
            f"doc:{doc_id}",
            mapping={
                "status": "error",
                "error": str(e)
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