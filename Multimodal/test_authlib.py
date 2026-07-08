import asyncio
from authlib.integrations.httpx_client import AsyncOAuth2Client

async def main():
    try:
        client = AsyncOAuth2Client()
        resp = await client.get('https://accounts.google.com/.well-known/openid-configuration')
        print(resp.status_code)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
