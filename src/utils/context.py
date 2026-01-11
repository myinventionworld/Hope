from contextvars import ContextVar
from google.oauth2.credentials import Credentials

current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
current_user_creds: ContextVar[Credentials | None] = ContextVar("current_user_creds", default=None)
