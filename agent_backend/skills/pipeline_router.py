"""
Pipeline Router - Routes content to appropriate pipeline profiles.

Determines the correct publishing pipeline based on:
- Content type (News, Analysis, Review, Guide)
- Urgency signals from EditorialBrain
- Source credibility tier
"""

import os
import sys
from typing import Dict, Optional, List
from urllib.parse import urlparse

# Allow running from repo root without PYTHONPATH
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger
from shared.models import (
    ArticleDraft,
    PipelineProfile,
    FastTrackConfig,
    CouncilThresholds,
    QualityThresholds,
    RollbackConfig,
    DeliberationConfig,
)

logger = get_logger("PipelineRouter")


class PipelineRouter:
    """
    Routes content to appropriate pipeline profiles based on content type,
    urgency, and source credibility.
    """

    def __init__(self):
        self.profiles: Dict[str, PipelineProfile] = {}
        self.trusted_sources: Dict[str, List[str]] = {}
        self._load_profiles()
        self._load_trusted_sources()

    def _load_profiles(self):
        """Load pipeline profiles from configuration."""
        profile_configs = config.get("pipeline_profiles", {})

        for name, cfg in profile_configs.items():
            try:
                # Build FastTrackConfig
                fast_track_cfg = cfg.get("fast_track", {})
                fast_track = FastTrackConfig(
                    enabled=fast_track_cfg.get("enabled", False),
                    bypass_council=fast_track_cfg.get("bypass_council", False),
                    bypass_fact_check=fast_track_cfg.get("bypass_fact_check", False),
                    max_publish_time_seconds=fast_track_cfg.get(
                        "max_publish_time_seconds", 300
                    ),
                )

                # Build CouncilThresholds
                council_cfg = cfg.get("council", {})
                council = CouncilThresholds(
                    require_unanimous=council_cfg.get("require_unanimous", False),
                    min_advocate=council_cfg.get("min_advocate", 70),
                    min_skeptic=council_cfg.get("min_skeptic", 60),
                    min_guardian=council_cfg.get("min_guardian", 70),
                )

                # Build QualityThresholds
                quality_cfg = cfg.get("quality", {})
                quality = QualityThresholds(
                    min_score=quality_cfg.get("min_score", 60),
                    min_sources=quality_cfg.get("min_sources", 2),
                    min_citation_density=quality_cfg.get("min_citation_density", 0.3),
                    min_regulations=quality_cfg.get("min_regulations", 0),
                )

                # Build RollbackConfig
                rollback_cfg = cfg.get("rollback", {})
                rollback = RollbackConfig(
                    window_hours=rollback_cfg.get("window_hours", 24),
                    auto_retract_on_contradiction=rollback_cfg.get(
                        "auto_retract_on_contradiction", True
                    ),
                )

                # Build DeliberationConfig (optional)
                deliberation = None
                deliberation_cfg = cfg.get("deliberation")
                if deliberation_cfg:
                    deliberation = DeliberationConfig(
                        min_hours=deliberation_cfg.get("min_hours", 0)
                    )

                # Build PipelineProfile
                profile = PipelineProfile(
                    name=name,
                    applies_to=cfg.get("applies_to", []),
                    fast_track=fast_track,
                    council=council,
                    quality=quality,
                    rollback=rollback,
                    deliberation=deliberation,
                    gates=cfg.get("gates", []),
                    label=cfg.get("label"),
                )

                self.profiles[name] = profile
                logger.debug("profile_loaded", name=name)

            except Exception as e:
                logger.error("profile_load_error", name=name, error=str(e))

        logger.info("profiles_loaded", count=len(self.profiles))

    def _load_trusted_sources(self):
        """Load trusted sources from configuration."""
        trusted_cfg = config.get("trusted_sources", {})

        for tier, sources in trusted_cfg.items():
            self.trusted_sources[tier] = sources if isinstance(sources, list) else []

        logger.info(
            "trusted_sources_loaded",
            tier_1=len(self.trusted_sources.get("tier_1", [])),
            tier_2=len(self.trusted_sources.get("tier_2", [])),
            tier_3=len(self.trusted_sources.get("tier_3", [])),
        )

    def get_source_tier(self, url: str) -> Optional[str]:
        """
        Determine the trust tier of a source URL.

        Args:
            url: The source URL

        Returns:
            "tier_1", "tier_2", "tier_3", or None if not trusted
        """
        if not url:
            return None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]

            # Check each tier
            for tier in ["tier_1", "tier_2", "tier_3"]:
                sources = self.trusted_sources.get(tier, [])
                for trusted_domain in sources:
                    # Match if domain ends with trusted domain (handles subdomains)
                    if domain == trusted_domain or domain.endswith(
                        "." + trusted_domain
                    ):
                        return tier

            return None

        except Exception as e:
            logger.warning("source_tier_parse_error", url=url, error=str(e))
            return None

    def get_profile(self, draft: ArticleDraft, signals: Dict) -> PipelineProfile:
        """
        Determine the appropriate pipeline profile for a draft.

        Args:
            draft: The article draft to route
            signals: Signal dict with urgency, source info, etc.

        Returns:
            The appropriate PipelineProfile
        """
        content_type = draft.contentType

        # Check for breaking news fast-track
        if content_type == "News":
            if self._should_fast_track(draft, signals):
                return self.profiles.get("news_breaking", self._get_default_profile())

        # Route by content type
        profile_name = self._get_profile_name_for_content_type(content_type)
        return self.profiles.get(profile_name, self._get_default_profile())

    def _should_fast_track(self, draft: ArticleDraft, signals: Dict) -> bool:
        """
        Determine if a news article should be fast-tracked.

        Requires both:
        1. High urgency signal (critical or high)
        2. Source from tier_1 or tier_2
        """
        # Check urgency
        urgency = signals.get("urgency", "low")
        if urgency not in ["critical", "high"]:
            return False

        # Check source tier
        if not draft.sources:
            return False

        # Check first source's tier
        first_source = draft.sources[0]
        source_url = first_source.url if first_source.url else ""
        source_tier = self.get_source_tier(source_url)

        # Only tier_1 and tier_2 qualify for fast-track
        if source_tier not in ["tier_1", "tier_2"]:
            return False

        logger.info(
            "fast_track_eligible",
            title=draft.title[:50],
            urgency=urgency,
            source_tier=source_tier,
        )
        return True

    def _get_profile_name_for_content_type(self, content_type: str) -> str:
        """
        Get the profile name for a given content type.

        Mapping:
        - News -> news_standard
        - Analysis, Review -> views
        - Guide -> research
        - General, other -> news_standard (default)
        """
        content_type_map = {
            "News": "news_standard",
            "Analysis": "views",
            "Review": "views",
            "Guide": "research",
            "General": "news_standard",
        }
        return content_type_map.get(content_type, "news_standard")

    def _content_type_matches_profile(
        self, content_type: str, profile: PipelineProfile
    ) -> bool:
        """Check if a content type matches a profile's applies_to list."""
        return content_type in profile.applies_to

    def _get_default_profile(self) -> PipelineProfile:
        """Get the default profile (news_standard) or create a minimal one."""
        if "news_standard" in self.profiles:
            return self.profiles["news_standard"]

        # Fallback: create minimal profile
        return PipelineProfile(
            name="default",
            applies_to=["News", "General"],
            fast_track=FastTrackConfig(enabled=False),
            council=CouncilThresholds(),
            quality=QualityThresholds(),
        )


if __name__ == "__main__":
    # Quick test
    from shared.models import ArticleSource

    router = PipelineRouter()

    print(f"Loaded profiles: {list(router.profiles.keys())}")
    print(f"Trusted sources tier_1: {router.trusted_sources.get('tier_1', [])}")

    # Test source tier detection
    test_urls = [
        "https://pib.gov.in/press/123",
        "https://reuters.com/article/123",
        "https://economictimes.indiatimes.com/news/123",
        "https://random-blog.com/post",
    ]
    for url in test_urls:
        tier = router.get_source_tier(url)
        print(f"{url} -> {tier}")

    # Test profile routing
    test_draft = ArticleDraft(
        title="Test Breaking News",
        description="Test description",
        category="Security",
        contentType="News",
        body="Test body content",
        wordCount=500,
        sources=[
            ArticleSource(id="1", title="PIB", url="https://pib.gov.in/press/123")
        ],
    )
    profile = router.get_profile(test_draft, {"urgency": "critical"})
    print(f"\nBreaking news profile: {profile.name}")
    print(f"Fast-track enabled: {profile.fast_track.enabled}")
