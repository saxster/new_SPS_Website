"""
Autonomous Runner: The Heartbeat of the Autopoietic Newsroom.
Runs continuously: Discover → Write → Observe → Learn → Reflect → Repeat
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

# Allow running from any directory
AGENT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AGENT_ROOT not in sys.path:
    sys.path.insert(0, AGENT_ROOT)

from config.manager import config
from shared.logger import get_logger, setup_logging
from skills.content_brain import ContentBrain
from skills.gemini_client import GeminiAgent
from skills.ghost_writer import GhostWriterV2
from skills.agents.topic_proposer import TopicProposer
from skills.taste_model import TasteModel
from skills.taste_memory import ArticleFeedback

setup_logging()
logger = get_logger("AutonomousRunner")


class AutonomousRunner:
    """
    The heartbeat of the Autopoietic Newsroom.
    
    Orchestrates the full autonomous loop:
    1. DISCOVER: Find topics to write about
    2. SELECT: Filter through taste model
    3. WRITE: Create articles using GhostWriter
    4. OBSERVE: Record outcomes
    5. LEARN: Update taste weights
    6. REFLECT: Periodic self-analysis
    """
    
    def __init__(
        self,
        brain: Optional[ContentBrain] = None,
        llm: Optional[GeminiAgent] = None,
        dry_run: bool = False
    ):
        self.brain = brain or ContentBrain()
        self.llm = llm or GeminiAgent()
        self.dry_run = dry_run
        
        # Core components
        self.proposer = TopicProposer(brain=self.brain, llm=self.llm)
        self.taste = TasteModel()
        self.writer = GhostWriterV2(client=self.llm, brain=self.brain) if not dry_run else None
        
        # Configuration
        self.interval_minutes = config.get("autonomous.interval_minutes", 60)
        self.max_articles_per_cycle = config.get("autonomous.max_articles_per_cycle", 3)
        self.reflection_interval_hours = config.get("autonomous.reflection_interval_hours", 24)
        
        # State
        self.running = True
        self.cycles_completed = 0
        self.articles_written = 0
        self.last_reflection = datetime.now()
        
        # Graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info("autonomous_runner_initialized",
                   interval_minutes=self.interval_minutes,
                   max_per_cycle=self.max_articles_per_cycle,
                   dry_run=dry_run)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info("shutdown_requested", signal=signum)
        self.running = False
    
    # =========================================================================
    # Main Loop
    # =========================================================================
    
    def run_forever(self):
        """Run the autonomous loop indefinitely."""
        logger.info("autonomous_loop_started")
        print("\n🤖 Autonomous Newsroom is LIVE")
        print(f"   Interval: {self.interval_minutes} minutes")
        print(f"   Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                self.run_cycle()
                self.cycles_completed += 1
                
                # Check for reflection
                if self._should_reflect():
                    self._reflect()
                
                # Wait for next cycle
                if self.running:
                    logger.info("cycle_complete", 
                              cycles=self.cycles_completed,
                              articles=self.articles_written,
                              next_in_minutes=self.interval_minutes)
                    time.sleep(self.interval_minutes * 60)
                    
            except Exception as e:
                logger.error("cycle_failed", error=str(e))
                if self.running:
                    time.sleep(60)  # Brief pause before retry
        
        print("\n✅ Autonomous Newsroom stopped gracefully")
        self._print_summary()
    
    def run_cycle(self):
        """Run a single discovery-write-learn cycle."""
        cycle_start = time.monotonic()
        logger.info("cycle_started", cycle=self.cycles_completed + 1)
        
        # PHASE 1: DISCOVER
        print(f"\n📡 Cycle {self.cycles_completed + 1}: Discovering topics...")
        proposals = self.proposer.discover_topics()
        logger.info("discovery_complete", proposals=len(proposals))
        
        if not proposals:
            print("   No new topics found")
            return
        
        # PHASE 2: SELECT (filter through taste)
        selected = self.taste.filter_proposals(
            proposals, 
            max_count=self.max_articles_per_cycle
        )
        print(f"   Selected {len(selected)} topics (taste-filtered)")
        
        for p in selected:
            adjusted = getattr(p, 'adjusted_score', p.score)
            print(f"   • [{p.priority}] {p.topic[:50]}... (score: {adjusted:.2f})")
        
        if self.dry_run:
            print("   [DRY RUN] Skipping article creation")
            return
        
        # PHASE 3: WRITE
        for proposal in selected:
            print(f"\n📝 Writing: {proposal.topic[:50]}...")
            start_time = time.monotonic()
            
            try:
                topic_dict = {
                    'topic': proposal.topic,
                    'content_type': proposal.content_type,
                    'target_audience': proposal.target_audience
                }
                
                result = self.writer.create_article(topic_dict)
                write_time = time.monotonic() - start_time
                
                # PHASE 4: OBSERVE
                if result:
                    print(f"   ✓ Published (quality: {result.get('qualityScore', 0)})")
                    self._record_success(proposal, result, write_time)
                    self.articles_written += 1
                else:
                    print(f"   ✗ Blocked (trust/quality violation)")
                    self._record_failure(proposal, write_time, "blocked")
                    
            except Exception as e:
                write_time = time.monotonic() - start_time
                print(f"   ✗ Error: {e}")
                self._record_failure(proposal, write_time, str(e))
        
        cycle_time = time.monotonic() - cycle_start
        logger.info("cycle_finished", duration_s=round(cycle_time, 1))
    
    # =========================================================================
    # Feedback Recording
    # =========================================================================
    
    def _record_success(self, proposal, result: dict, write_time: float):
        """Record a successful article outcome."""
        feedback = ArticleFeedback(
            topic_id=proposal.id,
            topic=proposal.topic,
            sector=self._infer_sector(proposal),
            content_type=proposal.content_type,
            proposal_score=proposal.score,
            quality_score=result.get('qualityScore', 70),
            was_published=True,
            was_blocked=False,
            block_reason=None,
            time_to_write_seconds=write_time,
            sources_found=len(result.get('reviewNotes', {}).get('evidence', [])),
            sources_used=len(result.get('sources', [])),
            trust_score=result.get('reviewNotes', {}).get('claims', {}).get('metrics', {}).get('average_confidence', 5)
        )
        
        # PHASE 5: LEARN
        self.taste.update(feedback)
    
    def _record_failure(self, proposal, write_time: float, reason: str):
        """Record a failed/blocked article outcome."""
        feedback = ArticleFeedback(
            topic_id=proposal.id,
            topic=proposal.topic,
            sector=self._infer_sector(proposal),
            content_type=proposal.content_type,
            proposal_score=proposal.score,
            quality_score=0,
            was_published=False,
            was_blocked=True,
            block_reason=reason,
            time_to_write_seconds=write_time,
            sources_found=0,
            sources_used=0,
            trust_score=0
        )
        
        # PHASE 5: LEARN
        self.taste.update(feedback)
    
    def _infer_sector(self, proposal) -> str:
        """Infer sector from proposal."""
        topic = proposal.topic.lower()
        if 'cyber' in topic or 'breach' in topic:
            return 'cybersecurity'
        if 'fire' in topic:
            return 'fire_safety'
        if 'cctv' in topic or 'surveillance' in topic:
            return 'physical_security'
        if 'compliance' in topic or 'regulation' in topic:
            return 'compliance'
        return 'general'
    
    # =========================================================================
    # Reflection
    # =========================================================================
    
    def _should_reflect(self) -> bool:
        """Check if it's time for reflection."""
        hours_since = (datetime.now() - self.last_reflection).total_seconds() / 3600
        return hours_since >= self.reflection_interval_hours
    
    def _reflect(self):
        """Run self-reflection on performance."""
        print("\n🤔 Reflecting on performance...")
        logger.info("reflection_started")
        
        try:
            reflection = self.taste.reflect(self.llm)
            self.last_reflection = datetime.now()
            
            print(f"\n💭 Reflection:\n{reflection}\n")
            logger.info("reflection_complete", reflection=reflection[:200])
            
        except Exception as e:
            logger.error("reflection_failed", error=str(e))
    
    def _print_summary(self):
        """Print final summary."""
        summary = self.taste.get_taste_summary()
        
        print("\n" + "="*50)
        print("📊 Session Summary")
        print("="*50)
        print(f"Cycles completed: {self.cycles_completed}")
        print(f"Articles written: {self.articles_written}")
        print(f"Success rate (30d): {summary['overall_success_rate']:.1%}")
        print(f"Favorite sector: {summary['favorite_sector']} ({summary['favorite_sector_weight']:.2f}x)")
        print(f"Favorite type: {summary['favorite_content_type']} ({summary['favorite_type_weight']:.2f}x)")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Newsroom Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python autonomous_runner.py                    # Run forever
  python autonomous_runner.py --dry-run          # Test without writing
  python autonomous_runner.py --cycles 5         # Run 5 cycles then stop
  python autonomous_runner.py --interval 30      # 30 minute intervals
        """
    )
    parser.add_argument("--dry-run", action="store_true", 
                       help="Discover topics but don't write articles")
    parser.add_argument("--cycles", type=int, default=0,
                       help="Number of cycles to run (0 = forever)")
    parser.add_argument("--interval", type=int, default=60,
                       help="Minutes between cycles")
    parser.add_argument("--reflect", action="store_true",
                       help="Run reflection only and exit")
    
    args = parser.parse_args()
    
    runner = AutonomousRunner(dry_run=args.dry_run)
    
    if args.interval:
        runner.interval_minutes = args.interval
    
    if args.reflect:
        # Reflection-only mode
        runner._reflect()
        return
    
    if args.cycles > 0:
        # Limited cycles mode
        print(f"🤖 Running {args.cycles} cycles...")
        for i in range(args.cycles):
            if not runner.running:
                break
            runner.run_cycle()
            runner.cycles_completed += 1
            if i < args.cycles - 1 and runner.running:
                time.sleep(runner.interval_minutes * 60)
        runner._print_summary()
    else:
        # Forever mode
        runner.run_forever()


if __name__ == "__main__":
    main()
