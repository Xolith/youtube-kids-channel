"""
YouTube Kids Channel - Main Pipeline
Orchestrates content creation: Pixabay downloads + Voice generation + Video creation
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from pixabay_downloader import search_images, search_videos, download_media, KIDS_SEARCH_QUERIES
from voice_generator import create_voiceover, generate_template_voice
from video_creator import create_short_video, create_intro, create_outro

# Output directories
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
VIDEOS_DIR = os.path.join(OUTPUT_DIR, "videos")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")

# Sample content topics for kids
KIDS_TOPICS = {
    "animals": {
        "title": "Amazing Animal Facts",
        "queries": ["cute animals", "wild animals", "ocean animals", "farm animals"],
        "facts_template": "Did you know {animal} can {amazing_fact}?"
    },
    "space": {
        "title": "Space Adventures",
        "queries": ["solar system", "planets", "space universe", "galaxy"],
        "facts_template": "Space fact: {planet} is {amazing_fact}!"
    },
    "nature": {
        "title": "Nature Wonders",
        "queries": ["forest", "mountains", "ocean life", "rainbow"],
        "facts_template": "Nature is amazing: {natural_phenomenon}!"
    },
    "geography": {
        "title": "World Explorer",
        "queries": ["world map", "countries", "landmarks", "continents"],
        "facts_template": "Country fact: {country} is known for {amazing_fact}!"
    }
}

def create_content_pack(topic: str, num_facts: int = 5) -> dict:
    """Create a complete content pack for a video"""
    
    if topic not in KIDS_TOPICS:
        print(f"Topic '{topic}' not found. Available: {list(KIDS_TOPICS.keys())}")
        return None
    
    config = KIDS_TOPICS[topic]
    
    # Search and download background images
    all_images = []
    for query in config["queries"][:num_facts]:
        images = search_images(query, count=2)
        all_images.extend(images)
        if len(all_images) >= num_facts:
            break
    
    downloaded_images = download_media(all_images[:num_facts], "image")
    
    # Generate voiceovers
    intro_audio = generate_template_voice(
        "fact_list", 
        count=num_facts, 
        topic=topic.replace("_", " ")
    )
    
    outro_audio = generate_template_voice(
        "thanks", 
        topic=topic.replace("_", " ")
    )
    
    return {
        "topic": topic,
        "title": config["title"],
        "backgrounds": downloaded_images,
        "intro_audio": intro_audio,
        "outro_audio": outro_audio
    }

def main():
    """Interactive content creator"""
    print("\n🇺🇸 🇨🇦 🇦🇺 YouTube Kids Channel Creator")
    print("=" * 50)
    
    # Show available topics
    print("\nAvailable topics:")
    for i, (topic, config) in enumerate(KIDS_TOPICS.items(), 1):
        print(f"{i}. {config['title']}")
    
    # For now, auto-generate for demo
    print("\nCreating sample content pack for 'animals' topic...")
    content = create_content_pack("animals", 5)
    
    if content:
        print(f"\nGenerated for: {content['title']}")
        print(f"Backgrounds: {len(content['backgrounds'])} images")
        print(f"Intro audio: {content['intro_audio']}")
        
        # Sample facts
        sample_facts = [
            "Dolphins sleep with one eye open!",
            "Honey never spoils!",
            "Octopuses have 3 hearts!",
            "Bananas grow on giant herbs!",
            "Sea otters hold hands while sleeping!"
        ]
        
        # Create video
        output = create_short_video(
            facts=sample_facts,
            background_videos=content["backgrounds"],
            intro_audio=content["intro_audio"],
            outro_audio=content["outro_audio"],
            output_name=f"{content['topic']}_short_{hash(str(sample_facts)) % 10000}.mp4"
        )
        print(f"\n✅ Video created: {output}")
    
    print("\n🔧 To install dependencies run:")
    print("   pip install -r requirements.txt")

if __name__ == "__main__":
    main()