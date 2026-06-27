"""SQLAlchemy implementation of the request-log repository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from securai.shared.models import RequestLogModel


def _to_dict(m: RequestLogModel) -> dict:
    return {
        "id": m.id,
        "request_id": m.request_id,
        "org_id": m.org_id,
        "project_id": m.project_id,
        "api_key_id": m.api_key_id,
        "model": m.model,
        "provider": m.provider,
        "endpoint": m.endpoint,
        "status": m.status,
        "status_code": m.status_code,
        "streamed": m.streamed,
        "latency_ms": m.latency_ms,
        "prompt_tokens": m.prompt_tokens,
        "completion_tokens": m.completion_tokens,
        "total_tokens": m.total_tokens,
        "cost_micro_usd": m.cost_micro_usd,
        "prompt_preview": m.prompt_preview,
        "completion_preview": m.completion_preview,
        "error": m.error,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


class SqlRequestLogRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, record: dict) -> None:
        self._s.add(RequestLogModel(**record))
        await self._s.flush()

    async def list_recent(
        self, *, org_id: str, project_id: str | None, limit: int
    ) -> list[dict]:
        stmt = select(RequestLogModel).where(RequestLogModel.org_id == org_id)
        if project_id:
            stmt = stmt.where(RequestLogModel.project_id == project_id)
        stmt = stmt.order_by(RequestLogModel.created_at.desc()).limit(limit)
        res = await self._s.execute(stmt)
        return [_to_dict(m) for m in res.scalars().all()]

    async def stats(self, *, org_id: str) -> dict:
        stmt = select(
            func.count(RequestLogModel.id),
            func.coalesce(func.sum(RequestLogModel.total_tokens), 0),
            func.coalesce(func.sum(RequestLogModel.cost_micro_usd), 0),
            func.coalesce(func.avg(RequestLogModel.latency_ms), 0),
        ).where(RequestLogModel.org_id == org_id)
        res = await self._s.execute(stmt)
        count, tokens, cost, avg_latency = res.one()
        return {
            "total_requests": int(count or 0),
            "total_tokens": int(tokens or 0),
            "total_cost_micro_usd": int(cost or 0),
            "avg_latency_ms": round(float(avg_latency or 0), 2),
        }
