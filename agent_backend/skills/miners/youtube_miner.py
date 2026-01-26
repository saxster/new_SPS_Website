"""
YouTubeMiner: Extracts transcripts from YouTube videos.
Based on patterns from youtube-to-ebook repository.

Features:
- Transcript extraction via youtube_transcript_api
- Shorts detection via URL pattern
- Rate limiting (2s delay between requests)
- Channel subscription support via channels.txt
"""

import os
import re
import time
import requests
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base_miner import BaseMiner, EvidenceItem

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    YouTubeTranscriptApi = None

try:
    from googleapiclient.discovery import build
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    build = None

from config.manager import config
from shared.logger import get_logger

logger = get_logger("YouTubeMiner")


@dataclass
class VideoInfo:
    """Intermediate representation of a YouTube video."""
    video_id: str
    title: str
    channel: str
    description: str
    published_at: Optional[datetime]
    url: str


class YouTubeMiner(BaseMiner):
    """
    YouTube transcript miner for video content ingestion.
    
    Credibility weight: 5 (video sources)
    Can be elevated to 7 for authoritative channels (DEF CON, ASIS, etc.)
    """
    
    AUTHORITATIVE_CHANNELS = {
        "defcon",
        "blackhat",
        "asis international",
        "isc2",
        "sans institute",
        "rsa conference",
        "cert-in",
        "nist",
    }
    
    def __init__(self, api_key: Optional[str] = None, channels_file: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.channels_file = channels_file or config.get(
            "paths.youtube_channels_file", 
            os.path.join(os.path.dirname(__file__), "../../data/youtube_channels.txt")
        )
        self.rate_limit_delay = config.get("youtube.rate_limit_delay", 2.0)
        self.timeout = config.get("youtube.request_timeout", 10)
        self._youtube = None
        self._transcript_api = None
        
        if YOUTUBE_TRANSCRIPT_AVAILABLE:
            self._transcript_api = YouTubeTranscriptApi()
    
    @property
    def source_type(self) -> str:
        return "video"
    
    @property
    def default_credibility(self) -> int:
        return 5
    
    def is_available(self) -> bool:
        """Check if YouTube miner is properly configured."""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            logger.warning("youtube_transcript_api not installed")
            return False
        return True
    
    def _get_youtube_client(self):
        """Lazy-load YouTube API client."""
        if self._youtube is None and YOUTUBE_API_AVAILABLE and self.api_key:
            self._youtube = build("youtube", "v3", developerKey=self.api_key)
        return self._youtube
    
    def _is_youtube_short(self, video_id: str) -> bool:
        """
        Check if video is a YouTube Short via URL pattern.
        Shorts redirect to /shorts/ URL when accessed directly.
        """
        try:
            shorts_url = f"https://www.youtube.com/shorts/{video_id}"
            response = requests.head(
                shorts_url, 
                allow_redirects=True, 
                timeout=self.timeout
            )
            return "/shorts/" in response.url
        except Exception as e:
            logger.debug("shorts_check_failed", video_id=video_id, error=str(e))
            return False
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _get_transcript(self, video_id: str) -> Optional[str]:
        """
        Extract transcript from a YouTube video.
        Uses instance method as per latest youtube_transcript_api syntax.
        """
        if not self._transcript_api:
            return None
            
        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
            
            # Fetch transcript - try English first, then any available
            try:
                transcript_list = self._transcript_api.fetch(video_id)
            except Exception:
                # Try listing available transcripts
                try:
                    available = self._transcript_api.list_transcripts(video_id)
                    transcript_list = available.find_transcript(['en', 'en-US', 'en-GB']).fetch()
                except Exception:
                    # Get any available transcript
                    available = self._transcript_api.list_transcripts(video_id)
                    transcript_list = list(available)[0].fetch()
            
            # Combine all segments into full text
            full_text = " ".join([segment.get("text", "") for segment in transcript_list])
            return self._clean_transcript(full_text)
            
        except Exception as e:
            logger.warning("transcript_fetch_failed", video_id=video_id, error=str(e))
            return None
    
    def _clean_transcript(self, text: str) -> str:
        """Clean up transcript text."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove [Music], [Applause] etc.
        text = re.sub(r'\[.*?\]', '', text)
        return text.strip()
    
    def _get_credibility_for_channel(self, channel_name: str) -> int:
        """
        Determine credibility weight based on channel authority.
        Authoritative security channels get higher weight.
        """
        channel_lower = channel_name.lower()
        for authoritative in self.AUTHORITATIVE_CHANNELS:
            if authoritative in channel_lower:
                return 7  # Elevated credibility for authoritative channels
        return self.default_credibility
    
    def _search_videos(self, query: str, limit: int = 5) -> List[VideoInfo]:
        """
        Search YouTube for videos matching query.
        Falls back to web scraping if API not available.
        """
        youtube = self._get_youtube_client()
        videos = []
        
        if youtube:
            try:
                # Use YouTube Data API
                search_response = youtube.search().list(
                    q=query,
                    part="snippet",
                    type="video",
                    maxResults=limit * 2,  # Fetch extra to filter Shorts
                    order="relevance",
                    videoDuration="medium"  # Filter out very short/long videos
                ).execute()
                
                for item in search_response.get("items", []):
                    video_id = item["id"]["videoId"]
                    
                    # Skip Shorts
                    if self._is_youtube_short(video_id):
                        continue
                    
                    snippet = item["snippet"]
                    published = None
                    if snippet.get("publishedAt"):
                        try:
                            published = datetime.fromisoformat(
                                snippet["publishedAt"].replace("Z", "+00:00")
                            )
                        except Exception:
                            pass
                    
                    videos.append(VideoInfo(
                        video_id=video_id,
                        title=snippet.get("title", ""),
                        channel=snippet.get("channelTitle", ""),
                        description=snippet.get("description", ""),
                        published_at=published,
                        url=f"https://www.youtube.com/watch?v={video_id}"
                    ))
                    
                    if len(videos) >= limit:
                        break
                        
            except Exception as e:
                logger.error("youtube_api_search_failed", error=str(e))
        
        return videos
    
    def _load_subscribed_channels(self) -> List[str]:
        """Load channel handles from channels.txt file."""
        channels = []
        if os.path.exists(self.channels_file):
            try:
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            channels.append(line)
            except Exception as e:
                logger.warning("channels_file_load_failed", error=str(e))
        return channels
    
    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch video transcripts matching the query.
        
        Args:
            query: Search query (e.g., "physical security best practices")
            limit: Maximum number of videos to return
            
        Returns:
            List of EvidenceItem objects with transcripts
        """
        if not self.is_available():
            logger.error("youtube_miner_not_available")
            return []
        
        logger.info("youtube_fetch_started", query=query, limit=limit)
        
        evidence_items = []
        videos = self._search_videos(query, limit)
        
        for idx, video in enumerate(videos):
            transcript = self._get_transcript(video.video_id)
            
            if not transcript:
                logger.debug("skipping_video_no_transcript", video_id=video.video_id)
                continue
            
            credibility = self._get_credibility_for_channel(video.channel)
            
            evidence_items.append(EvidenceItem(
                id=self._make_id(len(evidence_items)),
                title=video.title,
                url=video.url,
                raw_content=transcript,
                source_type=self.source_type,
                publisher=video.channel,
                published=video.published_at,
                credibility_weight=credibility,
                domain="youtube.com",
                snippet=transcript[:500] + "..." if len(transcript) > 500 else transcript,
                identifier=video.video_id,
                metadata={
                    "description": video.description,
                    "channel": video.channel,
                    "video_id": video.video_id
                }
            ))
            
            if len(evidence_items) >= limit:
                break
        
        logger.info("youtube_fetch_complete", count=len(evidence_items))
        return evidence_items
    
    def fetch_from_video_url(self, url: str) -> Optional[EvidenceItem]:
        """
        Fetch transcript from a specific video URL.
        Useful for curated video lists.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error("invalid_youtube_url", url=url)
            return None
        
        transcript = self._get_transcript(video_id)
        if not transcript:
            return None
        
        return EvidenceItem(
            id="S1",
            title=f"Video {video_id}",  # Would need API call for actual title
            url=url,
            raw_content=transcript,
            source_type=self.source_type,
            publisher="YouTube",
            credibility_weight=self.default_credibility,
            domain="youtube.com",
            snippet=transcript[:500],
            identifier=video_id
        )


# CLI testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Miner CLI")
    parser.add_argument("--query", type=str, default="physical security best practices")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    
    miner = YouTubeMiner()
    
    if not miner.is_available():
        print("YouTubeMiner not available. Install: pip install youtube-transcript-api")
    else:
        results = miner.fetch(args.query, args.limit)
        print(f"\n📺 Found {len(results)} videos with transcripts:\n")
        for item in results:
            print(f"  [{item.id}] {item.title}")
            print(f"       Channel: {item.publisher}")
            print(f"       Credibility: {item.credibility_weight}/10")
            print(f"       Transcript: {item.snippet[:200]}...\n")
