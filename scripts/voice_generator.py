"""
Text-to-Speech for Kids YouTube Channel
Creates child-friendly voiceovers using gTTS (Google Text-to-Speech)
"""

from gtts import gTTS
import os
from typing import Optional

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "audio")

# Accent options for different English-speaking countries
ACCENTS = {
    "us": "com",    # United States
    "uk": "co.uk",  # United Kingdom
    "au": "com.au", # Australia
    "ca": "ca"      # Canada
}

def create_voiceover(text: str, accent: str = "us", filename: str = "voiceover.mp3") -> str:
    """Create voiceover from text with specified accent"""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    tld = ACCENTS.get(accent, "com")
    tts = gTTS(text=text, lang="en", tld=tld, slow=False)
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    tts.save(filepath)
    
    return filepath

def create_intro_voiceover(channel_name: str = "Kids Fun Facts") -> str:
    """Generate channel intro voiceover"""
    text = f"Welcome to {channel_name}! Let's learn something amazing today!"
    return create_voiceover(text, "us", "intro_voice.mp3")

def create_outro_voiceover() -> str:
    """Generate video outro voiceover"""
    text = "Did you enjoy this video? Subscribe for more fun learning! See you next time!"
    return create_voiceover(text, "us", "outro_voice.mp3")

# Kids-friendly voice templates
VOICE_TEMPLATES = {
    "welcome": "Hey kids! Welcome back to our channel!",
    "top_5": "Here are our top 5 amazing {topic} facts!",
    "number": "Number {num}! {fact}",
    "fun_fact": "Wow, isn't that cool?",
    "subscribe": "Don't forget to like and subscribe!",
    "thanks": "Thanks for watching! Have a great day!"
}

def generate_template_voice(template_key: str, **kwargs) -> str:
    """Generate voiceover from predefined templates"""
    templates = {
        "fact_list": "Hey explorers! Here are {count} awesome {topic} facts just for you!",
        "countdown": "Let's count down from {start} to {end}! Ready? Go!",
        "quiz": "Can you guess what {topic} is? Let's find out together!",
        "learning": "Today we're learning about {topic}! Let's go!",
        "amazing": "Isn't that amazing? You learned something new!",
        "challenge": "Can you remember all {count} things we learned? Try it!"
    }
    
    text = templates.get(template_key, "Hello kids!").format(**kwargs)
    filename = f"{template_key}_{kwargs.get('topic', 'general')}.mp3"
    return create_voiceover(text, "us", filename)

if __name__ == "__main__":
    # Test TTS
    print("Testing TTS...")
    path = create_voiceover("Hello kids! Let's learn about animals!", "us")
    print(f"Voiceover created: {path}")
    
    # Test templates
    path2 = generate_template_voice("fact_list", count=5, topic="ocean animals")
    print(f"Template voiceover created: {path2}")