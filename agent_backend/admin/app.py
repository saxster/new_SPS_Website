"""
Admin Panel: Web UI for Managing Authoritative Sources

Provides a simple web interface to:
- Add/Edit/Delete premium news sources
- Store credentials securely
- Test source connectivity
- Trigger manual syncs
- View sync status and exemplar counts

Security:
- Token-based authentication
- Rate limiting (5 failed attempts = 15 min lockout)
- Audit logging
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict
from collections import defaultdict

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from lib.credential_vault import CredentialVault, AuthoritativeSource
from skills.taste_anchors import TasteAnchors
from shared.logger import get_logger

logger = get_logger("AdminPanel")


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    Simple in-memory rate limiter for login attempts.
    
    Security:
    - 5 failed attempts = 15 minute lockout
    - Tracks by IP address
    - Audit logs all failed attempts
    """
    
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_minutes)
        self.attempts: Dict[str, list] = defaultdict(list)
        self.lockouts: Dict[str, datetime] = {}
    
    def is_locked_out(self, ip: str) -> bool:
        """Check if IP is currently locked out."""
        if ip in self.lockouts:
            if datetime.now() < self.lockouts[ip]:
                return True
            else:
                # Lockout expired, clear it
                del self.lockouts[ip]
                self.attempts[ip] = []
        return False
    
    def get_lockout_remaining(self, ip: str) -> int:
        """Get remaining lockout time in seconds."""
        if ip in self.lockouts:
            remaining = (self.lockouts[ip] - datetime.now()).total_seconds()
            return max(0, int(remaining))
        return 0
    
    def record_attempt(self, ip: str, success: bool) -> bool:
        """
        Record a login attempt.
        
        Returns True if attempt is allowed, False if locked out.
        """
        if self.is_locked_out(ip):
            logger.warning("login_attempt_while_locked", ip=ip)
            return False
        
        if success:
            # Clear attempts on success
            self.attempts[ip] = []
            logger.info("login_success", ip=ip)
            return True
        
        # Record failed attempt
        now = datetime.now()
        self.attempts[ip].append(now)
        
        # Clean old attempts (only keep last hour)
        cutoff = now - timedelta(hours=1)
        self.attempts[ip] = [t for t in self.attempts[ip] if t > cutoff]
        
        # Check if should lock out
        if len(self.attempts[ip]) >= self.max_attempts:
            self.lockouts[ip] = now + self.lockout_duration
            logger.warning(
                "login_lockout_triggered",
                ip=ip,
                attempts=len(self.attempts[ip]),
                lockout_until=self.lockouts[ip].isoformat()
            )
            return False
        
        logger.warning(
            "login_failed",
            ip=ip,
            attempts=len(self.attempts[ip]),
            remaining=self.max_attempts - len(self.attempts[ip])
        )
        return True


# Initialize rate limiter
rate_limiter = RateLimiter(max_attempts=5, lockout_minutes=15)

# Initialize FastAPI app
app = FastAPI(
    title="SPS Newsroom Admin",
    description="Manage authoritative sources for taste development",
    version="1.0.0"
)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Initialize services
vault = CredentialVault()
anchors = TasteAnchors()

# Simple auth token (in production, use proper auth)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "newsroom-admin-2026")


def verify_token(request: Request):
    """Simple token verification for admin access."""
    token = request.cookies.get("admin_token") or request.query_params.get("token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


def get_client_ip(request: Request) -> str:
    """Get client IP, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# =============================================================================
# Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to sources list."""
    return RedirectResponse(url="/admin/sources")


@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    ip = get_client_ip(request)
    
    # Check if locked out
    if rate_limiter.is_locked_out(ip):
        remaining = rate_limiter.get_lockout_remaining(ip)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Too many failed attempts. Try again in {remaining // 60} minutes."
        })
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/admin/login")
async def login(request: Request, token: str = Form(...)):
    """Handle login with rate limiting."""
    ip = get_client_ip(request)
    
    # Check if locked out
    if rate_limiter.is_locked_out(ip):
        remaining = rate_limiter.get_lockout_remaining(ip)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Too many failed attempts. Try again in {remaining // 60} minutes."
        })
    
    # Verify token
    if token == ADMIN_TOKEN:
        rate_limiter.record_attempt(ip, success=True)
        response = RedirectResponse(url="/admin/sources", status_code=302)
        response.set_cookie("admin_token", token, httponly=True)
        return response
    
    # Failed attempt
    rate_limiter.record_attempt(ip, success=False)
    
    # Check if now locked out
    if rate_limiter.is_locked_out(ip):
        remaining = rate_limiter.get_lockout_remaining(ip)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Too many failed attempts. Locked out for {remaining // 60} minutes."
        })
    
    attempts_remaining = rate_limiter.max_attempts - len(rate_limiter.attempts.get(ip, []))
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": f"Invalid token. {attempts_remaining} attempts remaining."
    })


@app.get("/admin/sources", response_class=HTMLResponse)
async def list_sources(request: Request, token: str = Depends(verify_token)):
    """List all authoritative sources."""
    sources = vault.list_sources()
    stats = anchors.get_stats()
    
    # Add credential status to each source
    sources_with_status = []
    for source in sources:
        has_creds = vault.has_credentials(source.id)
        sources_with_status.append({
            "source": source,
            "has_credentials": has_creds,
            "exemplar_count": next(
                (s["count"] for s in stats["by_source"] if s["source_id"] == source.id),
                0
            )
        })
    
    return templates.TemplateResponse("sources.html", {
        "request": request,
        "sources": sources_with_status,
        "total_exemplars": stats["total_exemplars"]
    })


@app.get("/admin/sources/add", response_class=HTMLResponse)
async def add_source_form(request: Request, token: str = Depends(verify_token)):
    """Show add source form."""
    return templates.TemplateResponse("source_form.html", {
        "request": request,
        "source": None,
        "action": "add"
    })


@app.post("/admin/sources/add")
async def add_source(
    request: Request,
    token: str = Depends(verify_token),
    name: str = Form(...),
    base_url: str = Form(...),
    login_url: str = Form(""),
    username_selector: str = Form(""),
    password_selector: str = Form(""),
    submit_selector: str = Form(""),
    article_selector: str = Form(""),
    credibility_weight: int = Form(5),
    sync_frequency_hours: int = Form(24),
    max_articles_per_sync: int = Form(10),
    username: str = Form(""),
    password: str = Form("")
):
    """Handle source creation."""
    import hashlib
    
    # Generate ID from name
    source_id = hashlib.md5(name.lower().encode()).hexdigest()[:12]
    
    source = AuthoritativeSource(
        id=source_id,
        name=name,
        base_url=base_url,
        login_url=login_url,
        username_selector=username_selector,
        password_selector=password_selector,
        submit_selector=submit_selector,
        article_selector=article_selector,
        credibility_weight=credibility_weight,
        sync_frequency_hours=sync_frequency_hours,
        max_articles_per_sync=max_articles_per_sync,
        enabled=True,
        last_sync=None,
        articles_ingested=0
    )
    
    vault.add_source(source)
    
    # Store credentials if provided
    if username and password:
        vault.store_credentials(source_id, username, password)
    
    logger.info("source_added_via_admin", source_id=source_id, name=name)
    
    return RedirectResponse(url="/admin/sources", status_code=302)


@app.get("/admin/sources/{source_id}", response_class=HTMLResponse)
async def edit_source_form(
    request: Request, 
    source_id: str,
    token: str = Depends(verify_token)
):
    """Show edit source form."""
    source = vault.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    has_credentials = vault.has_credentials(source_id)
    
    return templates.TemplateResponse("source_form.html", {
        "request": request,
        "source": source,
        "has_credentials": has_credentials,
        "action": "edit"
    })


@app.post("/admin/sources/{source_id}")
async def update_source(
    request: Request,
    source_id: str,
    token: str = Depends(verify_token),
    name: str = Form(...),
    base_url: str = Form(...),
    login_url: str = Form(""),
    username_selector: str = Form(""),
    password_selector: str = Form(""),
    submit_selector: str = Form(""),
    article_selector: str = Form(""),
    credibility_weight: int = Form(5),
    sync_frequency_hours: int = Form(24),
    max_articles_per_sync: int = Form(10),
    enabled: bool = Form(False),
    username: str = Form(""),
    password: str = Form("")
):
    """Handle source update."""
    existing = vault.get_source(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source = AuthoritativeSource(
        id=source_id,
        name=name,
        base_url=base_url,
        login_url=login_url,
        username_selector=username_selector,
        password_selector=password_selector,
        submit_selector=submit_selector,
        article_selector=article_selector,
        credibility_weight=credibility_weight,
        sync_frequency_hours=sync_frequency_hours,
        max_articles_per_sync=max_articles_per_sync,
        enabled=enabled,
        last_sync=existing.last_sync,
        articles_ingested=existing.articles_ingested
    )
    
    vault.update_source(source)
    
    # Update credentials if provided
    if username and password:
        vault.store_credentials(source_id, username, password)
    
    logger.info("source_updated_via_admin", source_id=source_id)
    
    return RedirectResponse(url="/admin/sources", status_code=302)


@app.post("/admin/sources/{source_id}/delete")
async def delete_source(
    source_id: str,
    token: str = Depends(verify_token)
):
    """Delete a source."""
    vault.delete_source(source_id)
    logger.info("source_deleted_via_admin", source_id=source_id)
    return RedirectResponse(url="/admin/sources", status_code=302)


@app.post("/admin/sources/{source_id}/toggle")
async def toggle_source(
    source_id: str,
    token: str = Depends(verify_token)
):
    """Toggle source enabled status."""
    source = vault.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source.enabled = not source.enabled
    vault.update_source(source)
    
    return RedirectResponse(url="/admin/sources", status_code=302)


# =============================================================================
# API Endpoints (for programmatic access)
# =============================================================================

@app.get("/api/sources")
async def api_list_sources(token: str = Depends(verify_token)):
    """List all sources (JSON)."""
    sources = vault.list_sources()
    return [s.to_dict() for s in sources]


@app.get("/api/stats")
async def api_stats(token: str = Depends(verify_token)):
    """Get system stats."""
    sources = vault.list_sources()
    anchor_stats = anchors.get_stats()
    
    return {
        "sources": {
            "total": len(sources),
            "enabled": sum(1 for s in sources if s.enabled),
            "with_credentials": sum(1 for s in sources if vault.has_credentials(s.id))
        },
        "exemplars": anchor_stats,
        "audit_recent": vault.get_audit_log(limit=10)
    }


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("SPS Newsroom Admin Panel")
    print("="*60)
    print(f"URL: http://localhost:8080/admin/sources")
    print(f"Token: {ADMIN_TOKEN}")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
