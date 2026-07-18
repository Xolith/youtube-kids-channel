"""
Pixabay Downloader for Kids YouTube Channel
Fetches royalty-free images and videos for children's content
API key should be set in .env file or PIXABAY_API_KEY environment variable
"""

import requests
import json
import os
from typing import List, Dict, Optional

PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
BASE_URL = "https://pixabay.com/api"
VIDEO_URL = "https://pixabay.com/videos/api/videos"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

def search_images(query: str, count: int = 5) -> List[Dict]:
    """Search for images on Pixabay"""
    url = f"{BASE_URL}/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "image_type": "photo",
        "orientation": "vertical",
        "per_page": count,
        "safesearch": "true",
        "order": "popular"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    for hit in data.get("hits", []):
        results.append({
            "id": hit["id"],
            "type": "image",
            "tags": hit["tags"],
            "url": hit["largeImageURL"],
            "preview": hit["previewURL"]
        })
    
    return results

def search_videos(query: str, count: int = 3) -> List[Dict]:
    """Search for videos on Pixabay"""
    url = f"{VIDEO_URL}/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": count,
        "safesearch": "true",
        "order": "popular"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    results = []
    for hit in data.get("hits", []):
        results.append({
            "id": hit["id"],
            "type": "video",
            "tags": hit.get("tags", ""),
            "url": hit["videos"]["large"]["url"],
            "duration": hit.get("duration", 0)
        })
    
    return results

def download_media(items: List[Dict], media_type: str = "image") -> List[str]:
    """Download media files to output directory"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    downloaded = []
    
    for item in items:
        url = item["url"]
        ext = "mp4" if media_type == "video" else "jpg"
        filename = f"{item['id']}.{ext}"
        filepath = os.path.join(OUTPUT_DIR, media_type + "s", filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        response = requests.get(url)
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        downloaded.append(filepath)
        print(f"Downloaded: {filename}")
    
    return downloaded

KIDS_SEARCH_QUERIES = {
    "animals": ["cute animals", "wild animals", "pets", "farm animals", "ocean animals"],
    "education": ["alphabet letters", "numbers learning", "colors rainbow", "shapes geometry", "solar system"],
    "fun_facts": ["space planets", "world wonders", "dinosaurs", "ocean life", "forest animals"],
    "activities": ["kids playing", "educational games", "art drawing", "sports kids", "dance children"],
    "nature": ["sunset landscape", "forest trees", "mountain view", "river stream", "flower garden"]
}