import asyncio
import httpx
async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={"test": "data"})
        print(resp.status_code)
asyncio.run(main())
