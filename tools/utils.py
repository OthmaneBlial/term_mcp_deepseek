import asyncio

async def sleep(seconds: float):
    """Async sleep helper."""
    await asyncio.sleep(seconds)
