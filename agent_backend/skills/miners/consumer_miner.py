"""
ConsumerMiner: Product reviews and consumer intelligence.

Provides security product evaluations, certification tracking, and
consumer intelligence for SMBs and professionals.

Features:
- Security product category tracking
- BIS certification status checking
- Industry test result aggregation
- Consumer review analysis
- Product comparison generation

Categories:
- CCTV systems
- Access control
- Alarm systems
- Safes/lockers
- Cybersecurity tools
- Security services
- Fire safety equipment
- Personal safety devices
"""

import os
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from urllib.parse import urlparse

from .base_miner import BaseMiner, EvidenceItem
from config.manager import config
from shared.logger import get_logger

logger = get_logger("ConsumerMiner")

# Check for SerpAPI dependency
try:
    from serpapi import GoogleSearch

    SERPAPI_AVAILABLE = True
except ImportError:
    SERPAPI_AVAILABLE = False
    GoogleSearch = None


# Product categories
ProductCategory = Literal[
    "cctv_systems",
    "access_control",
    "alarm_systems",
    "safes_lockers",
    "cybersecurity_tools",
    "security_services",
    "fire_safety_equipment",
    "personal_safety_devices",
]


class ConsumerMiner(BaseMiner):
    """
    Security product and consumer intelligence miner.

    Tracks security products, certifications, and consumer reviews
    to help SMBs and professionals make informed decisions.

    Target pillars: product_reviews, business_security
    Target personas: smb, professional
    """

    # Product categories with search terms
    CATEGORY_TERMS = {
        "cctv_systems": [
            "cctv camera",
            "ip camera",
            "surveillance system",
            "nvr",
            "dvr",
            "security camera",
            "hikvision",
            "cp plus",
            "dahua",
            "godrej security camera",
        ],
        "access_control": [
            "access control system",
            "biometric attendance",
            "fingerprint scanner",
            "rfid access",
            "door lock system",
            "time attendance",
            "essl",
            "biomax",
        ],
        "alarm_systems": [
            "burglar alarm",
            "intrusion detection",
            "security alarm",
            "motion sensor",
            "pir sensor",
            "siren system",
        ],
        "safes_lockers": [
            "home safe",
            "electronic safe",
            "fireproof safe",
            "godrej safe",
            "gun safe",
            "locker",
            "cash box",
        ],
        "cybersecurity_tools": [
            "antivirus india",
            "endpoint security",
            "firewall",
            "password manager",
            "vpn india",
            "backup solution",
        ],
        "security_services": [
            "security guard service",
            "security agency",
            "security consultant",
            "risk assessment service",
            "security audit",
            "psara license",
        ],
        "fire_safety_equipment": [
            "fire extinguisher",
            "smoke detector",
            "fire alarm",
            "sprinkler system",
            "fire blanket",
            "fire suppression",
        ],
        "personal_safety_devices": [
            "personal alarm",
            "pepper spray",
            "gps tracker",
            "dashcam india",
            "body camera",
            "stun device",
        ],
    }

    # Rating criteria for products
    RATING_CRITERIA = [
        "certification_status",
        "build_quality",
        "reliability",
        "value_for_money",
        "after_sales_support",
        "india_availability",
    ]

    # Trusted review/comparison sources
    TRUSTED_SOURCES = {
        "bis.gov.in": 10,
        "amazon.in": 6,
        "flipkart.com": 6,
        "91mobiles.com": 7,
        "digit.in": 7,
        "gadgets360.com": 7,
        "techradar.com": 7,
        "securityworldmarket.com": 8,
        "asmag.com": 8,
    }

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        self.config = config.get("consumer_miner", {})
        self.enabled = self.config.get("enabled", True)
        self.categories = self.config.get(
            "categories", list(self.CATEGORY_TERMS.keys())
        )

    @property
    def source_type(self) -> str:
        return "consumer"

    @property
    def default_credibility(self) -> int:
        return 6  # Consumer reviews need verification

    def is_available(self) -> bool:
        """Check if miner is available."""
        return self.enabled

    def fetch(self, query: str, limit: int = 5) -> List[EvidenceItem]:
        """
        Fetch product/consumer evidence.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of EvidenceItem objects
        """
        results: List[EvidenceItem] = []

        # Add product review context
        if not any(kw in query.lower() for kw in ["review", "best", "comparison"]):
            query = f"{query} review comparison India"

        if SERPAPI_AVAILABLE and self.api_key:
            results = self._fetch_product_reviews(query, limit)

        logger.info("consumer_fetch_complete", count=len(results), query=query[:50])
        return results[:limit]

    def fetch_by_category(
        self, category: ProductCategory, limit: int = 10
    ) -> List[EvidenceItem]:
        """
        Fetch products and reviews for a specific category.

        Args:
            category: Product category
            limit: Maximum results

        Returns:
            List of product-related evidence
        """
        if category not in self.CATEGORY_TERMS:
            logger.warning("unknown_category", category=category)
            return []

        terms = self.CATEGORY_TERMS[category]
        query = f"best {' OR '.join(terms[:3])} India 2024 review"

        results = self._fetch_product_reviews(query, limit)

        for result in results:
            result.metadata["category"] = category
            result.metadata["pillar"] = "product_reviews"
            result.metadata["target_personas"] = ["smb", "professional"]

        logger.info("category_products_fetched", category=category, count=len(results))
        return results

    def fetch_product_comparisons(
        self, product_type: str, limit: int = 5
    ) -> List[EvidenceItem]:
        """
        Fetch product comparison articles.

        Args:
            product_type: Type of product to compare
            limit: Maximum results

        Returns:
            List of comparison articles
        """
        query = f"best {product_type} India comparison review 2024"

        results = self._fetch_product_reviews(query, limit)

        for result in results:
            result.metadata["content_type"] = "comparison"

        return results

    def fetch_certification_info(
        self, product_type: str, limit: int = 5
    ) -> List[EvidenceItem]:
        """
        Fetch BIS/ISI certification information.

        Args:
            product_type: Type of product
            limit: Maximum results

        Returns:
            List of certification-related evidence
        """
        query = f"{product_type} BIS certification ISI mark India standard"

        results = self._fetch_product_reviews(query, limit)

        for result in results:
            result.metadata["content_type"] = "certification"

            # Boost credibility for official sources
            if "bis.gov.in" in result.url:
                result.credibility_weight = 10

        return results

    def get_category_overview(self, category: ProductCategory) -> Dict:
        """
        Get an overview of a product category.

        Args:
            category: Product category

        Returns:
            Dictionary with category overview
        """
        products = self.fetch_by_category(category, limit=10)

        return {
            "category": category,
            "terms": self.CATEGORY_TERMS.get(category, []),
            "product_count": len(products),
            "sources": list(set(p.publisher for p in products)),
            "top_products": [
                {
                    "title": p.title,
                    "source": p.publisher,
                    "url": p.url,
                    "credibility": p.credibility_weight,
                }
                for p in products[:5]
            ],
            "rating_criteria": self.RATING_CRITERIA,
        }

    def get_trending_products(self, limit: int = 10) -> List[Dict]:
        """
        Get trending security products across categories.

        Args:
            limit: Maximum number of products

        Returns:
            List of trending product dictionaries
        """
        all_products = []

        # Sample from each major category
        priority_categories = [
            "cctv_systems",
            "access_control",
            "cybersecurity_tools",
            "fire_safety_equipment",
        ]

        for category in priority_categories:
            products = self.fetch_by_category(category, limit=3)
            for product in products:
                all_products.append(
                    {
                        "category": category,
                        "title": product.title,
                        "source": product.publisher,
                        "url": product.url,
                        "snippet": product.snippet,
                        "credibility": product.credibility_weight,
                    }
                )

        return all_products[:limit]

    def generate_review_template(self, category: ProductCategory) -> Dict:
        """
        Generate a review template for a product category.

        Args:
            category: Product category

        Returns:
            Review template dictionary
        """
        category_specific = {
            "cctv_systems": {
                "specs": ["Resolution", "Night Vision", "Storage", "Remote Access"],
                "pros_to_check": ["Image quality", "Mobile app", "Installation"],
                "cons_to_check": ["Power backup", "Storage cost", "Support"],
            },
            "access_control": {
                "specs": ["Capacity", "Connectivity", "Software", "Integration"],
                "pros_to_check": ["Speed", "Accuracy", "Reports"],
                "cons_to_check": ["Software updates", "Support response"],
            },
            "cybersecurity_tools": {
                "specs": ["Protection level", "System impact", "Updates"],
                "pros_to_check": ["Detection rate", "UI/UX", "Price"],
                "cons_to_check": ["False positives", "Resource usage"],
            },
        }

        return {
            "category": category,
            "rating_criteria": self.RATING_CRITERIA,
            "category_specific": category_specific.get(
                category,
                {
                    "specs": ["Key Features", "Build Quality", "Price"],
                    "pros_to_check": ["Quality", "Support", "Value"],
                    "cons_to_check": ["Limitations", "Issues"],
                },
            ),
            "structure": [
                "Overview",
                "Key Specifications",
                "Pros",
                "Cons",
                "Who Should Buy",
                "Verdict",
            ],
        }

    def _fetch_product_reviews(self, query: str, limit: int) -> List[EvidenceItem]:
        """Fetch product reviews via SerpAPI."""
        if not SERPAPI_AVAILABLE or not self.api_key:
            logger.debug("serpapi_unavailable_for_consumer")
            return []

        try:
            params = {
                "engine": "google",
                "q": query,
                "gl": "in",
                "hl": "en",
                "num": limit,
                "api_key": self.api_key,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            items = []
            organic_results = results.get("organic_results", [])

            for idx, item in enumerate(organic_results[:limit]):
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")

                if not link:
                    continue

                domain = self._extract_domain(link)
                credibility = self._get_source_credibility(domain)

                evidence = EvidenceItem(
                    id=self._make_id(idx),
                    title=title,
                    url=link,
                    raw_content=snippet,
                    source_type="consumer",
                    publisher=domain,
                    credibility_weight=credibility,
                    domain=domain,
                    snippet=snippet[:500] if snippet else "",
                    metadata={
                        "source": "consumer_miner",
                        "pillar": "product_reviews",
                    },
                )
                items.append(evidence)

            return items

        except Exception as e:
            logger.error("product_review_fetch_error", error=str(e))
            return []

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _get_source_credibility(self, domain: str) -> int:
        """Get credibility score for source domain."""
        if domain in self.TRUSTED_SOURCES:
            return self.TRUSTED_SOURCES[domain]

        # Government/official sources
        if ".gov" in domain:
            return 9

        return self.default_credibility


if __name__ == "__main__":
    # Quick test
    miner = ConsumerMiner()

    print(f"ConsumerMiner available: {miner.is_available()}")

    print("\nProduct categories:")
    for category in miner.CATEGORY_TERMS.keys():
        print(f"  - {category}")

    print("\nFetching CCTV overview...")
    overview = miner.get_category_overview("cctv_systems")
    print(f"Found {overview['product_count']} products")
