import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import SessionLocal, get_db
from app.models import Lead, Product
from app.schemas import LeadCreate, LeadOut, LeadStatusUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_STATUSES = ("new", "in_progress", "done")


async def notify_lead(lead_id: int) -> None:
    from app.services.telegram import notify_new_lead

    try:
        async with SessionLocal() as session:
            lead = await session.get(Lead, lead_id)
            if not lead:
                return
            product_name = None
            if lead.product_id:
                product_name = await session.scalar(
                    select(Product.name).where(Product.id == lead.product_id)
                )
            await notify_new_lead(lead, product_name)
    except Exception:
        logger.exception("Failed to send telegram notification for lead %s", lead_id)


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    payload: LeadCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Укажите номер телефона")

    kind = payload.kind if payload.kind in ("callback", "order") else "callback"

    product_id = None
    comment = payload.comment
    if payload.product_id:
        product = await db.get(Product, payload.product_id)
        if product:
            product_id = product.id
            order_comment = f"Заказ товара: {product.name}"
            comment = f"{order_comment}\n{comment}" if comment else order_comment

    lead = Lead(
        kind=kind,
        name=payload.name.strip()[:255] or "Не указано",
        phone=phone[:64],
        product_id=product_id,
        comment=comment,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    background_tasks.add_task(notify_lead, lead.id)
    return lead


@router.get("", response_model=list[LeadOut])
async def list_leads(
    status_filter: str | None = None,
    limit: int = 500,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()).limit(min(limit, 1000))
    if status_filter and status_filter != "all":
        if status_filter not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Недопустимый статус")
        query = query.where(Lead.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead_status(
    lead_id: int,
    payload: LeadStatusUpdate,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Недопустимый статус")
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    lead.status = payload.status
    await db.commit()
    await db.refresh(lead)
    return lead
