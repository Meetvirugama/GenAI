import asyncio
import httpx
import time

async def main():
    t0 = time.time()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://oauth2.googleapis.com/token")
            print("HTTPX Response:", resp.status_code)
    except Exception as e:
        print(f"HTTPX Error: {type(e).__name__} - {e}")
    print(f"HTTPX took {time.time() - t0:.2f}s")

    t0 = time.time()
    import requests
    try:
        resp = requests.get("https://oauth2.googleapis.com/token")
        print("Requests Response:", resp.status_code)
    except Exception as e:
        print(f"Requests Error: {type(e).__name__} - {e}")
    print(f"Requests took {time.time() - t0:.2f}s")

asyncio.run(main())
