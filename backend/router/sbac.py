from backend.supabase import AsyncClient

from typing import cast
from fastapi import Request

def get_sbac(request: Request):
    return cast(AsyncClient, request.app.state.supabase_client)
