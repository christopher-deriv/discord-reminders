import asyncio
import os
from aiohttp import web
from bot import start_web_server

async def main():
    await start_web_server()
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
