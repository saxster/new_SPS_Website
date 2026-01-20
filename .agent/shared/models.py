from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class ArticleSource(BaseModel):
    id: str
    title: str
    url: Optional[str] = None

class ArticleImage(BaseModel):
    url: str
    alt: str

class ArticleDraft(BaseModel):
    """
    Strict Schema mirroring the Astro Content Collection Zod Schema.
    Ensures backend output is always valid for the frontend.
    """
    title: str = Field(..., max_length=70, description="SEO optimized title")
    description: str = Field(..., max_length=160, description="SEO meta description")
    pubDate: Optional[datetime] = Field(default_factory=datetime.now)
    author: str = "SPS Intelligence Team"
    
    image: Optional[ArticleImage] = None
    
    tags: List[str] = Field(default_factory=list)
    category: Literal[
        "Jewellery", "Education", "Healthcare", "Finance", 
        "Petrol", "Cyber", "Compliance", "Intelligence", "Security", "Critical",
        "Technology", "Strategic Risk", "News"
    ]
    
    contentType: Literal["Guide", "Analysis", "News", "Review", "General"] = Field("General", alias="content_type")
    draft: bool = Field(default=False)
    
    # Content Body
    body: str = Field(..., description="The full markdown content")
    
    # Quality & Metadata
    wordCount: int = Field(default=0, alias="word_count")
    qualityScore: float = 0.0
    sources: List[ArticleSource] = Field(default_factory=list)
    regulations: List[str] = Field(default_factory=list)
    revision: int = 1
    
    # Internal Review Data (not exposed to frontend directly but useful for debug)
    reviewNotes: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
