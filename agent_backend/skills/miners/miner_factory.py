"""
Miner Factory: Creates available miners based on configuration.
Handles graceful degradation when optional dependencies are missing.
"""

from typing import List
from config.manager import config
from shared.logger import get_logger

from .base_miner import BaseMiner

logger = get_logger("MinerFactory")


def create_available_miners() -> List[BaseMiner]:
    """
    Create list of miners that are enabled in config AND have dependencies installed.
    
    Returns empty list if miners.enabled is False.
    Gracefully handles missing optional dependencies.
    """
    if not config.get("miners.enabled", True):
        logger.info("miners_disabled", reason="miners.enabled=false in config")
        return []
    
    miners: List[BaseMiner] = []
    
    # PaperMiner - arXiv API, always available (no external deps)
    if config.get("miners.paper.enabled", True):
        try:
            from .paper_miner import PaperMiner
            pm = PaperMiner()
            if pm.is_available():
                miners.append(pm)
                logger.info("miner_loaded", miner="paper", source="arXiv")
        except Exception as e:
            logger.warning("miner_load_failed", miner="paper", error=str(e))
    
    # YouTubeMiner - requires youtube_transcript_api
    if config.get("miners.youtube.enabled", False):
        try:
            from .youtube_miner import YouTubeMiner
            ym = YouTubeMiner()
            if ym.is_available():
                miners.append(ym)
                logger.info("miner_loaded", miner="youtube", source="YouTube")
            else:
                logger.info("miner_skipped", miner="youtube", reason="youtube_transcript_api not installed")
        except ImportError:
            logger.info("miner_skipped", miner="youtube", reason="youtube_transcript_api not installed")
        except Exception as e:
            logger.warning("miner_load_failed", miner="youtube", error=str(e))
    
    # ArticleMiner - requires trafilatura
    if config.get("miners.article.enabled", False):
        try:
            from .article_miner import ArticleMiner
            am = ArticleMiner()
            if am.is_available():
                miners.append(am)
                logger.info("miner_loaded", miner="article", source="web")
            else:
                logger.info("miner_skipped", miner="article", reason="trafilatura not installed")
        except ImportError:
            logger.info("miner_skipped", miner="article", reason="trafilatura not installed")
        except Exception as e:
            logger.warning("miner_load_failed", miner="article", error=str(e))
    
    logger.info("miners_initialized", count=len(miners), types=[m.source_type for m in miners])
    return miners


def get_miner_status() -> dict:
    """
    Get status of all miners (for diagnostics/health checks).
    
    Returns dict with miner name -> status info.
    """
    status = {}
    
    # PaperMiner
    try:
        from .paper_miner import PaperMiner
        pm = PaperMiner()
        status["paper"] = {
            "enabled": config.get("miners.paper.enabled", True),
            "available": pm.is_available(),
            "source": "arXiv API",
            "deps_installed": True
        }
    except Exception as e:
        status["paper"] = {"enabled": False, "available": False, "error": str(e)}
    
    # YouTubeMiner
    try:
        from .youtube_miner import YouTubeMiner, YOUTUBE_TRANSCRIPT_AVAILABLE
        status["youtube"] = {
            "enabled": config.get("miners.youtube.enabled", False),
            "available": YOUTUBE_TRANSCRIPT_AVAILABLE,
            "source": "YouTube Transcripts",
            "deps_installed": YOUTUBE_TRANSCRIPT_AVAILABLE,
            "install_cmd": "pip install youtube-transcript-api" if not YOUTUBE_TRANSCRIPT_AVAILABLE else None
        }
    except Exception as e:
        status["youtube"] = {"enabled": False, "available": False, "error": str(e)}
    
    # ArticleMiner
    try:
        from .article_miner import ArticleMiner, TRAFILATURA_AVAILABLE
        status["article"] = {
            "enabled": config.get("miners.article.enabled", False),
            "available": TRAFILATURA_AVAILABLE,
            "source": "Web Articles",
            "deps_installed": TRAFILATURA_AVAILABLE,
            "install_cmd": "pip install trafilatura" if not TRAFILATURA_AVAILABLE else None
        }
    except Exception as e:
        status["article"] = {"enabled": False, "available": False, "error": str(e)}
    
    return status
