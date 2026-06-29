import sys
import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

print("1. Importing app.main")
from app.main import app
print("2. Starting lifespan")
import asyncio

async def main():
    async with app.router.lifespan_context(app):
        print("3. Lifespan context initialized successfully")

asyncio.run(main())
print("4. Done")
