from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models import Lead, Product, utcnow
from app.schemas import DashboardStats

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    products_total = await db.scalar(select(func.count()).select_from(Product))
    products_active = await db.scalar(
        select(func.count()).select_from(Product).where(Product.is_active.is_(True))
    )
    leads_total = await db.scalar(select(func.count()).select_from(Lead))
    leads_new = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.status == "new")
    )
    leads_today = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.created_at >= today_start)
    )
    leads_week = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.created_at >= week_start)
    )

    return DashboardStats(
        products_total=products_total or 0,
        products_active=products_active or 0,
        leads_total=leads_total or 0,
        leads_new=leads_new or 0,
        leads_today=leads_today or 0,
        leads_week=leads_week or 0,
    )
