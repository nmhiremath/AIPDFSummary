import asyncio
from worker import main

if __name__ == "__main__":
    print("Starting PDF processing worker...")
    asyncio.run(main()) 