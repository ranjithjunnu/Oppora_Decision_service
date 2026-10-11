"""Paginated local directory search for the discovery workspace."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from scoring.discovery import search

router = APIRouter(prefix='/v1/discovery', tags=['Local discovery'])


@router.get('/{kind}')
def discover(kind: Literal['companies', 'people'], query: str = Query('', max_length=200),
             location: str = Query('', max_length=150), company_id: str | None = Query(None, max_length=100),
             offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    try:
        return search(kind, query, location, company_id, offset, limit)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, 'The local directory is unavailable. Add datasets/company_directory.json and restart the backend.') from exc
