"""
Credential Vault: Secure Encrypted Storage for Premium Source Credentials

Security:
- Fernet symmetric encryption (AES-128-CBC)
- Master key from VAULT_MASTER_KEY environment variable
- Credentials never logged or exposed in API responses
- Audit logging for all access
"""

import os
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from config.manager import config
from shared.logger import get_logger

# Cryptography is optional - graceful degradation
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None
    CRYPTO_AVAILABLE = False

logger = get_logger("CredentialVault")


@dataclass
class AuthoritativeSource:
    """Configuration for a premium news source."""
    id: str
    name: str
    base_url: str
    login_url: str
    username_selector: str
    password_selector: str
    submit_selector: str
    article_selector: str
    credibility_weight: int  # 1-10
    sync_frequency_hours: int
    max_articles_per_sync: int
    enabled: bool
    last_sync: Optional[datetime]
    articles_ingested: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "login_url": self.login_url,
            "credibility_weight": self.credibility_weight,
            "sync_frequency_hours": self.sync_frequency_hours,
            "max_articles_per_sync": self.max_articles_per_sync,
            "enabled": self.enabled,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "articles_ingested": self.articles_ingested
        }


class CredentialVault:
    """
    Secure encrypted storage for premium source credentials.
    
    Security Model:
    - Master key from VAULT_MASTER_KEY env var
    - Fernet (AES-128) encryption for credentials
    - SQLite for encrypted blobs and source config
    - Audit logging for all access
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.get(
            "premium_sources.vault_path",
            ".agent/credential_vault.db"
        )
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        self._fernet = self._init_encryption()
        
        # Initialize database
        self._init_db()
        
        logger.info(
            "credential_vault_initialized",
            db_path=self.db_path,
            encryption_available=CRYPTO_AVAILABLE
        )
    
    def _init_encryption(self) -> Optional[Any]:
        """Initialize Fernet encryption with master key."""
        if not CRYPTO_AVAILABLE:
            logger.warning("cryptography_not_installed", 
                          message="Credentials will be stored in plaintext")
            return None
        
        master_key = os.getenv("VAULT_MASTER_KEY")
        if not master_key:
            # Generate a key for development (not for production!)
            logger.warning("vault_master_key_not_set",
                          message="Using derived key - set VAULT_MASTER_KEY in production")
            # Derive a key from a fixed seed (dev only)
            seed = "newsroom-dev-key-not-for-production"
            master_key = hashlib.sha256(seed.encode()).digest()[:32]
            master_key = Fernet.generate_key()  # Base64 encoded
        else:
            # Ensure key is properly formatted
            if len(master_key) == 32:
                # Raw 32-byte key, encode for Fernet
                import base64
                master_key = base64.urlsafe_b64encode(master_key.encode()[:32])
            elif len(master_key) == 44:
                # Already base64 encoded
                master_key = master_key.encode()
            else:
                # Hash to get consistent length
                import base64
                hashed = hashlib.sha256(master_key.encode()).digest()
                master_key = base64.urlsafe_b64encode(hashed)
        
        return Fernet(master_key)
    
    def _init_db(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    login_url TEXT,
                    username_selector TEXT,
                    password_selector TEXT,
                    submit_selector TEXT,
                    article_selector TEXT,
                    credibility_weight INTEGER DEFAULT 5,
                    sync_frequency_hours INTEGER DEFAULT 24,
                    max_articles_per_sync INTEGER DEFAULT 10,
                    enabled INTEGER DEFAULT 1,
                    last_sync TEXT,
                    articles_ingested INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS credentials (
                    source_id TEXT PRIMARY KEY,
                    encrypted_username BLOB,
                    encrypted_password BLOB,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    action TEXT NOT NULL,
                    source_id TEXT,
                    details TEXT
                )
            """)
            
            conn.commit()
    
    # =========================================================================
    # Source Management
    # =========================================================================
    
    def add_source(self, source: AuthoritativeSource) -> bool:
        """Add a new authoritative source."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO sources (
                        id, name, base_url, login_url,
                        username_selector, password_selector, submit_selector,
                        article_selector, credibility_weight, sync_frequency_hours,
                        max_articles_per_sync, enabled, articles_ingested
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source.id, source.name, source.base_url, source.login_url,
                    source.username_selector, source.password_selector,
                    source.submit_selector, source.article_selector,
                    source.credibility_weight, source.sync_frequency_hours,
                    source.max_articles_per_sync, 1 if source.enabled else 0,
                    source.articles_ingested
                ))
                conn.commit()
            
            self._log_audit("source_added", source.id, f"Added source: {source.name}")
            return True
            
        except sqlite3.IntegrityError:
            logger.warning("source_already_exists", source_id=source.id)
            return False
    
    def get_source(self, source_id: str) -> Optional[AuthoritativeSource]:
        """Get a source by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sources WHERE id = ?", 
                (source_id,)
            ).fetchone()
            
            if row:
                return self._row_to_source(row)
            return None
    
    def list_sources(self, enabled_only: bool = False) -> List[AuthoritativeSource]:
        """List all sources."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM sources"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY credibility_weight DESC"
            
            rows = conn.execute(query).fetchall()
            return [self._row_to_source(row) for row in rows]
    
    def update_source(self, source: AuthoritativeSource) -> bool:
        """Update an existing source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sources SET
                    name = ?, base_url = ?, login_url = ?,
                    username_selector = ?, password_selector = ?,
                    submit_selector = ?, article_selector = ?,
                    credibility_weight = ?, sync_frequency_hours = ?,
                    max_articles_per_sync = ?, enabled = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                source.name, source.base_url, source.login_url,
                source.username_selector, source.password_selector,
                source.submit_selector, source.article_selector,
                source.credibility_weight, source.sync_frequency_hours,
                source.max_articles_per_sync, 1 if source.enabled else 0,
                source.id
            ))
            conn.commit()
        
        self._log_audit("source_updated", source.id)
        return True
    
    def delete_source(self, source_id: str) -> bool:
        """Delete a source and its credentials."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM credentials WHERE source_id = ?", (source_id,))
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            conn.commit()
        
        self._log_audit("source_deleted", source_id)
        return True
    
    def update_sync_status(self, source_id: str, articles_count: int):
        """Update last sync time and article count."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sources SET
                    last_sync = ?,
                    articles_ingested = articles_ingested + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (datetime.now().isoformat(), articles_count, source_id))
            conn.commit()
    
    # =========================================================================
    # Credential Management
    # =========================================================================
    
    def store_credentials(
        self, 
        source_id: str, 
        username: str, 
        password: str
    ) -> bool:
        """Store encrypted credentials for a source."""
        encrypted_username = self._encrypt(username)
        encrypted_password = self._encrypt(password)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO credentials 
                (source_id, encrypted_username, encrypted_password, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (source_id, encrypted_username, encrypted_password))
            conn.commit()
        
        self._log_audit("credentials_stored", source_id)
        logger.info("credentials_stored", source_id=source_id)
        return True
    
    def get_credentials(self, source_id: str) -> Optional[Tuple[str, str]]:
        """Retrieve decrypted credentials for a source."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT encrypted_username, encrypted_password FROM credentials WHERE source_id = ?",
                (source_id,)
            ).fetchone()
            
            if row:
                self._log_audit("credentials_accessed", source_id)
                username = self._decrypt(row[0])
                password = self._decrypt(row[1])
                return (username, password)
            
            return None
    
    def delete_credentials(self, source_id: str) -> bool:
        """Delete credentials for a source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM credentials WHERE source_id = ?", (source_id,))
            conn.commit()
        
        self._log_audit("credentials_deleted", source_id)
        return True
    
    def has_credentials(self, source_id: str) -> bool:
        """Check if credentials exist for a source."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM credentials WHERE source_id = ?",
                (source_id,)
            ).fetchone()
            return row is not None
    
    # =========================================================================
    # Encryption Helpers
    # =========================================================================
    
    def _encrypt(self, plaintext: str) -> bytes:
        """Encrypt a string."""
        if self._fernet:
            return self._fernet.encrypt(plaintext.encode())
        # Fallback: base64 encode (NOT SECURE - dev only)
        import base64
        return base64.b64encode(plaintext.encode())
    
    def _decrypt(self, ciphertext: bytes) -> str:
        """Decrypt bytes to string."""
        if self._fernet:
            return self._fernet.decrypt(ciphertext).decode()
        # Fallback: base64 decode
        import base64
        return base64.b64decode(ciphertext).decode()
    
    # =========================================================================
    # Audit & Helpers
    # =========================================================================
    
    def _log_audit(self, action: str, source_id: str, details: str = ""):
        """Log an audit entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_log (action, source_id, details) VALUES (?, ?, ?)",
                (action, source_id, details)
            )
            conn.commit()
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    def _row_to_source(self, row: sqlite3.Row) -> AuthoritativeSource:
        """Convert database row to AuthoritativeSource."""
        last_sync = None
        if row["last_sync"]:
            try:
                last_sync = datetime.fromisoformat(row["last_sync"])
            except:
                pass
        
        return AuthoritativeSource(
            id=row["id"],
            name=row["name"],
            base_url=row["base_url"],
            login_url=row["login_url"] or "",
            username_selector=row["username_selector"] or "",
            password_selector=row["password_selector"] or "",
            submit_selector=row["submit_selector"] or "",
            article_selector=row["article_selector"] or "",
            credibility_weight=row["credibility_weight"],
            sync_frequency_hours=row["sync_frequency_hours"],
            max_articles_per_sync=row["max_articles_per_sync"],
            enabled=bool(row["enabled"]),
            last_sync=last_sync,
            articles_ingested=row["articles_ingested"]
        )


# =============================================================================
# CLI for Testing
# =============================================================================

if __name__ == "__main__":
    vault = CredentialVault()
    
    # Add a test source
    source = AuthoritativeSource(
        id="economist",
        name="The Economist",
        base_url="https://www.economist.com",
        login_url="https://www.economist.com/login",
        username_selector="input[name='email']",
        password_selector="input[name='password']",
        submit_selector="button[type='submit']",
        article_selector="article.article-body",
        credibility_weight=10,
        sync_frequency_hours=24,
        max_articles_per_sync=10,
        enabled=True,
        last_sync=None,
        articles_ingested=0
    )
    
    print("Adding source...")
    vault.add_source(source)
    
    print("Storing credentials...")
    vault.store_credentials("economist", "test@example.com", "secretpassword")
    
    print("\nRetrieving credentials...")
    creds = vault.get_credentials("economist")
    if creds:
        print(f"  Username: {creds[0]}")
        print(f"  Password: {'*' * len(creds[1])}")
    
    print("\nListing sources...")
    for s in vault.list_sources():
        print(f"  - {s.name} (weight: {s.credibility_weight})")
