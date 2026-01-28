import sys
import os
import getpass
from pathlib import Path

# Ensure we can import from the agent_backend directory
backend_path = os.path.join(os.path.dirname(__file__), 'agent_backend')
sys.path.append(backend_path)

# Change working directory to backend_path so relative paths (.agent/...) work
os.chdir(backend_path)

# Try to load VAULT_MASTER_KEY from .env if not in environment
if not os.getenv("VAULT_MASTER_KEY"):
    env_path = Path(".") / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("VAULT_MASTER_KEY="):
                    os.environ["VAULT_MASTER_KEY"] = line.split("=", 1)[1].strip()

from lib.credential_vault import CredentialVault, AuthoritativeSource
from config.manager import config

def setup_source(vault, id, name, base_url, login_url, user_sel, pass_sel, submit_sel):
    print(f"\n--- Configuring {name} ---")
    
    # Check if already exists
    existing = vault.get_source(id)
    if existing:
        print(f"Source '{name}' is already configured.")
        update = input("Do you want to update credentials? (y/n): ").lower()
        if update != 'y':
            return

    username = input(f"Enter Username/Email for {name}: ")
    password = getpass.getpass(f"Enter Password for {name}: ")

    source = AuthoritativeSource(
        id=id,
        name=name,
        base_url=base_url,
        login_url=login_url,
        username_selector=user_sel,
        password_selector=pass_sel,
        submit_selector=submit_sel,
        article_selector="article", # Default generic selector
        credibility_weight=10,      # High value for premium content
        sync_frequency_hours=24,
        max_articles_per_sync=10,
        enabled=True,
        last_sync=None,
        articles_ingested=0
    )

    # Add or Update Source Config
    if existing:
        vault.update_source(source)
    else:
        vault.add_source(source)

    # Store Credentials
    vault.store_credentials(id, username, password)
    print(f"✅ Successfully configured {name}!")

def main():
    if not os.getenv("VAULT_MASTER_KEY"):
        print("❌ Error: VAULT_MASTER_KEY is missing from your environment variables.")
        print("Please add it to your .env file first.")
        return

    vault = CredentialVault()

    # Define the configurations for your requested sites
    # Note: Selectors (#id, .class) may change over time and need maintenance.
    
    sources = [
        {
            "id": "nyt",
            "name": "The New York Times",
            "base_url": "https://www.nytimes.com",
            "login_url": "https://myaccount.nytimes.com/auth/login",
            "user_sel": "#email",
            "pass_sel": "#password",
            "submit_sel": "button[type='submit']"
        },
        {
            "id": "foreign_affairs",
            "name": "Foreign Affairs",
            "base_url": "https://www.foreignaffairs.com",
            "login_url": "https://www.foreignaffairs.com/user",
            "user_sel": "#edit-name",
            "pass_sel": "#edit-pass",
            "submit_sel": "#edit-submit"
        },
        {
            "id": "asis",
            "name": "ASIS Online",
            "base_url": "https://www.asisonline.org",
            "login_url": "https://www.asisonline.org/security-management/", 
            # Note: ASIS login flows can be complex (often SSO). 
            # These generic selectors might need adjustment based on the actual login page.
            "user_sel": "input[id*='Username']", 
            "pass_sel": "input[id*='Password']",
            "submit_sel": "input[type='submit']"
        }
    ]

    print("SPS Content Algorithm - Subscription Setup")
    print("------------------------------------------")

    for s in sources:
        setup_source(
            vault, 
            s['id'], s['name'], s['base_url'], s['login_url'], 
            s['user_sel'], s['pass_sel'], s['submit_sel']
        )

if __name__ == "__main__":
    main()
