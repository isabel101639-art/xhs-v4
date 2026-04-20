from fastapi import FastAPI, HTTPException

from crawler_service.config import get_settings
from crawler_service.providers import build_provider
from crawler_service.schemas import (
    AccountPostsRequest,
    AccountPostsResponse,
    TrendQueryRequest,
    TrendQueryResponse,
)


app = FastAPI(
    title='xhs-v4 crawler service',
    version='0.1.0',
    description='Provide creator account sync data for xhs-v4 automation.',
)


@app.get('/healthz')
async def healthz():
    settings = get_settings()
    provider = build_provider(settings)
    return {
        'success': True,
        'service': settings.service_name,
        'provider': settings.provider,
        'health': await provider.healthcheck(),
    }


@app.post('/xhs/account_posts', response_model=AccountPostsResponse)
async def xhs_account_posts(payload: AccountPostsRequest):
    settings = get_settings()
    provider = build_provider(settings)
    try:
        result = await provider.fetch_account_posts(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result


@app.post('/xhs/trends', response_model=TrendQueryResponse)
async def xhs_trends(payload: TrendQueryRequest):
    settings = get_settings()
    provider = build_provider(settings)
    try:
        result = await provider.fetch_trends(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result
