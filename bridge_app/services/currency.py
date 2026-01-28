import httpx

async def get_eur_to_usd_rate(date_str: str) -> float:
    """
    Fetch the EUR to USD exchange rate for a specific date using Frankfurter API.
    date_str: YYYY-MM-DD
    """
    url = f"https://api.frankfurter.app/{date_str}?from=EUR&to=USD"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data["rates"]["USD"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                 # Date might be today/weekend/future. Fallback to latest.
                 # Frankfurter returns 404 for weekends sometimes? Or just previous date?
                 # Actually frankfurter handles weekends by rolling back usually, but let's be safe.
                 print(f"Frankfurter 404 for {date_str}, trying without date (latest)")
                 return await get_latest_rate()
            raise e
        except Exception as e:
            print(f"Currency conversion error: {e}")
            raise e

async def get_latest_rate() -> float:
    url = "https://api.frankfurter.app/latest?from=EUR&to=USD"
    async with httpx.AsyncClient() as client:
         response = await client.get(url)
         data = response.json()
         return data["rates"]["USD"]
