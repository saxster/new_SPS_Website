"""
Art Director 🎨
Generates visual assets for articles.
For MVP: Uses Unsplash Source for high-quality, relevant stock photos.
Future: Connect to Gemini Vision/Imagen/DALL-E.
"""

import urllib.parse
import logging

logger = logging.getLogger("ArtDirector")

class ArtDirector:
    def get_header_image(self, title: str, topic: str) -> str:
        """
        Returns a high-quality Unsplash source URL based on keywords.
        """
        # Simple keyword extraction (first 3 words of topic)
        keywords = topic.split()[:3]
        query = ",".join(keywords).lower()
        
        # Unsplash Source (Random image from search terms)
        # Format: https://source.unsplash.com/1200x630/?security,ai
        # Note: Unsplash Source is deprecated/flaky, using Placehold.co as reliable fallback 
        # OR better: use a reliable random image service like Picsum or just text
        
        # Steelman: Use a reliable service that returns real images if possible. 
        # Pexels requires API. 
        # Let's use a standard placeholder that LOOKS professional for now, 
        # or just constructing a search URL that the frontend can use or lazy verify.
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://image.pollinations.ai/prompt/{encoded_query}?width=1200&height=630&nologo=true"
        
        logger.info(f"🎨 ArtDirector selected header: {url}")
        return url
