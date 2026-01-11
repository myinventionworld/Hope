import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.config import SCOPES, CREDENTIALS_FILE
from src.database.session import async_session_maker
from src.database.models import User

def get_flow():
    """Creates a Flow instance for OAuth."""
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob'
    )
    return flow

async def get_user_creds(user_id: int):
    """
    Retrieves credentials for a user from the database.
    Refreshes them if expired.
    """
    async with async_session_maker() as session:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.credentials_json:
            return None
        
        creds_data = json.loads(user.credentials_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed creds
                await save_user_creds(user_id, creds)
            except Exception as e:
                print(f"Error refreshing token for {user_id}: {e}")
                return None
        
        return creds

async def save_user_creds(user_id: int, creds: Credentials):
    """Saves user credentials to the database."""
    creds_json = creds.to_json()
    
    async with async_session_maker() as session:
        # Upsert (Insert or Replace)
        stmt = sqlite_insert(User).values(
            telegram_id=user_id,
            credentials_json=creds_json
        )
        # For SQLite upsert
        stmt = stmt.on_conflict_do_update(
            index_elements=['telegram_id'],
            set_=dict(credentials_json=creds_json)
        )
        

        await session.execute(stmt)
        await session.commit()

async def get_all_authenticated_users():
    """Returns a list of all users who have credentials."""
    async with async_session_maker() as session:
        stmt = select(User).where(User.credentials_json.is_not(None))
        result = await session.execute(stmt)
        return result.scalars().all()
