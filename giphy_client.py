import aiohttp
import logging
import os

GIPHY_API_KEY = os.getenv("GIPHY_API_KEY")

async def search_gifs(query, limit=25):
    """
    Search Giphy for GIFs matching the query.
    Returns a list of tuples: (gif_url, title)
    """
    if not GIPHY_API_KEY:
        logging.error("GIPHY_API_KEY not set in environment.")
        return []

    url = "https://api.giphy.com/v1/gifs/search"
    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "rating": "pg-13",
        "lang": "en"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    for item in data.get("data", []):
                        # Get the original image URL
                        gif_url = item["images"]["original"]["url"]
                        title = item["title"] or "GIF Result"
                        results.append((gif_url, title))
                    return results
                else:
                    logging.error(f"Giphy API error: {response.status}")
                    return []
    except Exception as e:
        logging.error(f"Failed to fetch GIFs: {e}")
        return []
