from pydantic import BaseModel, Field, HttpUrl, validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, date


# =============================================================================
# Audience Persona & Content Pillar Models (Reader-Centric)
# =============================================================================


class AudiencePersona(BaseModel):
    """
    Target audience persona for content targeting.

    Personas help score content relevance for specific reader segments:
    - citizen: General public seeking personal safety advice
    - senior: 60+ individuals needing simple, clear fraud prevention
    - smb: Small business owners seeking budget-conscious security
    - professional: Security managers requiring technical depth
    - compliance: Regulatory officers tracking deadlines and policy updates
    """

    id: Literal["citizen", "senior", "smb", "professional", "compliance"]
    name: str = Field(..., description="Display name for the persona")
    complexity_level: Literal["basic", "intermediate", "advanced"] = Field(
        default="intermediate",
        description="Technical complexity appropriate for this persona",
    )
    actionability_weight: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="How much this persona values actionable content (0-1)",
    )
    preferred_pillars: List[str] = Field(
        default_factory=list,
        description="Content pillars this persona is most interested in",
    )
    description: str = Field(default="", description="Description of persona needs")


class ContentPillar(BaseModel):
    """
    Content pillar for reader-centric content organization.

    Pillars organize content by reader needs rather than industry sectors:
    - scam_watch: Real-time fraud alerts, prevention, reporting
    - economic_security: Markets, investment fraud, corporate crime
    - personal_security: Home, travel, digital, physical safety
    - senior_safety: Elder-specific threats and protection
    - business_security: Practical SMB security guides
    - sector_intelligence: Deep dives by industry
    - product_reviews: Security products and services evaluated
    """

    slug: str = Field(..., description="URL-friendly identifier")
    name: str = Field(..., description="Display name")
    priority: int = Field(
        default=5, ge=1, le=10, description="Editorial priority (1=highest)"
    )
    target_mix: float = Field(
        default=0.1, ge=0, le=1, description="Target percentage of content (0.20 = 20%)"
    )
    sources: List[str] = Field(
        default_factory=list, description="Which miners feed this pillar"
    )
    target_personas: List[str] = Field(
        default_factory=list, description="Primary audience personas for this pillar"
    )
    description: str = Field(default="", description="Pillar description")
    icon: str = Field(default="", description="Icon identifier for UI")


# =============================================================================
# Adversarial Council Models
# =============================================================================


class AgentView(BaseModel):
    """Individual agent's evaluation of a draft."""

    agent: Literal["advocate", "skeptic", "guardian"]
    score: int = Field(..., ge=0, le=100, description="0-100 evaluation score")
    reasoning: str = Field(..., description="Explanation for the score")
    key_points: List[str] = Field(default_factory=list, description="Key observations")
    concerns: List[str] = Field(default_factory=list, description="Issues raised")
    recommendations: List[str] = Field(
        default_factory=list, description="Suggested fixes"
    )


class CouncilVerdict(BaseModel):
    """The synthesized decision from the 3-agent council."""

    decision: Literal["PUBLISH", "REVISE", "KILL"]
    confidence: float = Field(..., ge=0, le=1, description="0-1 confidence score")
    advocate_score: int = Field(..., ge=0, le=100)
    skeptic_score: int = Field(..., ge=0, le=100)
    guardian_score: int = Field(..., ge=0, le=100)
    average_score: float = Field(..., ge=0, le=100)
    dissenting_views: List[str] = Field(
        default_factory=list, description="Minority opinions"
    )
    required_fixes: List[str] = Field(
        default_factory=list, description="Changes needed for REVISE"
    )
    kill_reason: Optional[str] = Field(None, description="Reason if KILL")
    debate_summary: str = Field("", description="Summary of the council debate")


# =============================================================================
# Editorial Brain Models
# =============================================================================


class TopicEvaluation(BaseModel):
    """
    Evaluation of a single topic's newsworthiness.

    Enhanced with persona-based scoring and pillar assignment for
    reader-centric content targeting.
    """

    topic: str
    news_sense: int = Field(
        ..., ge=0, le=100, description="Is this genuinely newsworthy?"
    )
    audience_fit: int = Field(..., ge=0, le=100, description="Will our audience care?")
    competitive_angle: int = Field(
        ..., ge=0, le=100, description="Unique perspective potential"
    )
    feasibility: int = Field(
        ..., ge=0, le=100, description="Can we research and write this?"
    )
    timing: int = Field(..., ge=0, le=100, description="Is this the right moment?")
    overall_score: float = Field(..., ge=0, le=100)
    reasoning: str = Field("", description="Editorial judgment explanation")
    recommended_angle: Optional[str] = Field(None, description="Suggested approach")

    # Enhanced scoring dimensions (reader-centric)
    actionability: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Can reader take concrete action based on this content?",
    )
    india_specificity: int = Field(
        default=50,
        ge=0,
        le=100,
        description="India-specific relevance (laws, examples, costs in INR)",
    )
    evergreen_factor: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Long-term value vs time-sensitive (100=evergreen, 0=breaking)",
    )

    # Persona relevance scores
    persona_scores: Dict[str, int] = Field(
        default_factory=lambda: {
            "citizen": 50,
            "senior": 50,
            "smb": 50,
            "professional": 50,
            "compliance": 50,
        },
        description="Relevance score (0-100) for each persona",
    )

    # Pillar assignment
    primary_pillar: Optional[str] = Field(
        None, description="Primary content pillar (scam_watch, economic_security, etc.)"
    )
    secondary_pillars: List[str] = Field(
        default_factory=list, description="Secondary pillars this content also fits"
    )


class EditorialDirective(BaseModel):
    """Strategic directive from Editorial Brain."""

    action: Literal[
        "HUNT_BREAKING",
        "HUNT_TRENDING",
        "HUNT_GAP",
        "WRITE_PRIORITY",
        "WRITE_QUEUE",
        "HOLD",
    ]
    urgency: Literal["critical", "high", "medium", "low"] = "medium"
    focus_type: Optional[str] = None
    focus_topic: Optional[str] = None
    reason: str
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0, le=1)


# =============================================================================
# Learning Loop Models
# =============================================================================


class ArticlePerformance(BaseModel):
    """Performance metrics for a published article."""

    article_slug: str
    views: int = 0
    avg_time_seconds: float = 0
    shares: int = 0
    bounce_rate: float = 0
    scroll_depth: float = 0
    engagement_score: float = 0
    last_updated: Optional[datetime] = None


class LearningInsights(BaseModel):
    """Insights from performance analysis."""

    top_performing_topics: List[str] = Field(default_factory=list)
    underperforming_topics: List[str] = Field(default_factory=list)
    best_content_types: List[str] = Field(default_factory=list)
    best_sectors: List[str] = Field(default_factory=list)
    recommended_weight_adjustments: Dict[str, float] = Field(default_factory=dict)
    patterns_identified: List[str] = Field(default_factory=list)
    analysis_date: Optional[datetime] = None


# =============================================================================
# Pipeline Profile Models
# =============================================================================


class FastTrackConfig(BaseModel):
    """Configuration for fast-track publishing."""

    enabled: bool = False
    bypass_council: bool = False
    bypass_fact_check: bool = False
    max_publish_time_seconds: int = 300  # 5 minutes default


class CouncilThresholds(BaseModel):
    """Thresholds for council voting."""

    require_unanimous: bool = False
    min_advocate: int = 70
    min_skeptic: int = 60
    min_guardian: int = 70


class QualityThresholds(BaseModel):
    """Quality requirements for a profile."""

    min_score: int = 60
    min_sources: int = 2
    min_citation_density: float = 0.3
    min_regulations: int = 0


class RollbackConfig(BaseModel):
    """Configuration for rollback/correction window."""

    window_hours: int = 24
    auto_retract_on_contradiction: bool = True


class DeliberationConfig(BaseModel):
    """Configuration for deliberation delay."""

    min_hours: int = 0


class PipelineProfile(BaseModel):
    """Configuration profile for content-type specific publishing."""

    name: str
    applies_to: List[str] = Field(default_factory=list)
    fast_track: FastTrackConfig = Field(default_factory=FastTrackConfig)
    council: CouncilThresholds = Field(default_factory=CouncilThresholds)
    quality: QualityThresholds = Field(default_factory=QualityThresholds)
    rollback: RollbackConfig = Field(default_factory=RollbackConfig)
    deliberation: Optional[DeliberationConfig] = None
    gates: List[str] = Field(default_factory=list)
    label: Optional[str] = None  # Label prepended to fast-tracked articles


class BreakingAnalysis(BaseModel):
    """Result of breaking news detection analysis."""

    is_breaking: bool = False
    urgency: Literal["critical", "high", "medium", "low"] = "low"
    source_tier: Optional[Literal["tier_1", "tier_2", "tier_3"]] = None
    confidence: float = Field(0.0, ge=0, le=1)
    signals: List[str] = Field(default_factory=list)
    title_indicators: List[str] = Field(default_factory=list)
    recency_minutes: Optional[int] = None


# =============================================================================
# Article & Source Models
# =============================================================================


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
        "Jewellery",
        "Education",
        "Healthcare",
        "Finance",
        "Petrol",
        "Cyber",
        "Compliance",
        "Intelligence",
        "Security",
        "Critical",
        "Technology",
        "Strategic Risk",
        "News",
    ]

    contentType: Literal["Guide", "Analysis", "News", "Review", "General"] = Field(
        "General", alias="content_type"
    )
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
        json_encoders = {datetime: lambda v: v.isoformat()}


# =============================================================================
# Topic Sourcing Models
# =============================================================================


class SourcedTopic(BaseModel):
    """
    A topic discovered from external sources (think tanks, regulators, calendar).
    Used by TopicSourcer to feed the editorial pipeline.

    Enhanced with pillar assignment and persona targeting for reader-centric
    content prioritization.
    """

    id: str = Field(..., description="Unique topic identifier")
    title: str = Field(..., description="Topic title/headline")
    source_type: Literal[
        "breaking",
        "regulatory",
        "thinktank",
        "calendar",
        "gap",
        "scam",
        "market",
        "consumer",
    ] = Field(..., description="Type of source that generated this topic")
    source_id: str = Field(
        "", description="Source identifier (e.g., 'orf', 'rbi', 'cert_in')"
    )
    urgency: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="Urgency level for publishing"
    )
    content_type: Literal["News", "Analysis", "Guide", "Review"] = Field(
        default="News", description="Recommended content type"
    )
    source_url: Optional[str] = Field(None, description="URL of the source material")
    timeliness_score: int = Field(
        default=50, ge=0, le=100, description="How time-sensitive (0-100)"
    )
    authority_score: int = Field(
        default=50, ge=0, le=100, description="Source credibility (0-100)"
    )
    gap_score: int = Field(
        default=50, ge=0, le=100, description="Coverage gap in our content (0-100)"
    )
    overall_score: float = Field(
        default=50.0, ge=0, le=100, description="Weighted overall score"
    )
    suggested_angle: str = Field(default="", description="Suggested editorial angle")
    key_points: List[str] = Field(
        default_factory=list, description="Key points to cover"
    )
    tags: List[str] = Field(default_factory=list, description="Topic tags")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.now, description="When topic was sourced"
    )

    # Pillar and persona targeting (reader-centric)
    primary_pillar: Optional[str] = Field(
        None, description="Primary content pillar (scam_watch, economic_security, etc.)"
    )
    secondary_pillars: List[str] = Field(
        default_factory=list, description="Secondary pillars this topic also fits"
    )
    target_personas: List[str] = Field(
        default_factory=list,
        description="Target audience personas (citizen, senior, smb, etc.)",
    )
    actionability_score: int = Field(
        default=50, ge=0, le=100, description="How actionable for readers (0-100)"
    )
    india_specificity: int = Field(
        default=50, ge=0, le=100, description="India-specific relevance (0-100)"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CalendarEvent(BaseModel):
    """
    A calendar-driven event that can generate topics.
    Examples: annual reports, compliance deadlines, conferences, anniversaries.
    """

    id: str = Field(..., description="Unique event identifier")
    title: str = Field(..., description="Event title")
    event_type: Literal["report", "deadline", "conference", "anniversary"] = Field(
        ..., description="Type of calendar event"
    )
    event_date: date = Field(..., description="Date of the event")
    recurring: Optional[Literal["annual", "quarterly", "monthly"]] = Field(
        None, description="Recurrence pattern"
    )
    source: str = Field(default="", description="Source organization")
    content_type: Literal["News", "Analysis", "Guide"] = Field(
        default="Analysis", description="Best content type for this event"
    )
    priority: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="Editorial priority"
    )
    lead_days: int = Field(
        default=7, ge=0, description="Days before event to start coverage"
    )
    tags: List[str] = Field(default_factory=list, description="Event tags")
    description: str = Field(default="", description="Event description")
    last_triggered: Optional[datetime] = Field(
        None, description="When this event last generated a topic"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }
