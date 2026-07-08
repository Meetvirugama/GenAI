import asyncio
import httpx
import socket

async def main():
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    async with httpx.AsyncClient(transport=transport) as client:
        try:
            resp = await client.get("https://oauth2.googleapis.com/token")
            print("Forced IPv4 response:", resp.status_code)
        except Exception as e:
            print("Forced IPv4 error:", e)

asyncio.run(main())
