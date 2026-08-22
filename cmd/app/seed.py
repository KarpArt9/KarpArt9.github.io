import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BASE_DIR
from app.models import Lead, Product

logger = logging.getLogger(__name__)

PRODUCTS_JSON = BASE_DIR / "products.json"


async def seed_if_empty(session: AsyncSession) -> int:
    total = await session.scalar(select(func.count()).select_from(Product))
    if total:
        return 0

    if not PRODUCTS_JSON.exists():
        logger.warning("products.json not found, skipping seed")
        return 0

    raw = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
    products = []
    for item in raw:
        products.append(
            Product(
                id=str(item["id"]),
                name=item.get("name") or str(item["id"]),
                brand=(item.get("brand") or "").lower(),
                category=item.get("category") or "split",
                price=float(item.get("price") or 0),
                area=item.get("area"),
                type=item.get("type") or "standard",
                features=list(item.get("features") or []),
                specs=dict(item.get("specs") or {}),
            )
        )
    session.add_all(products)
    await session.commit()
    logger.info("Seeded %d products from products.json", len(products))
    return len(products)


async def cleanup_orphan_leads(session: AsyncSession) -> None:
    await session.execute(
        Lead.__table__.update().where(
            Lead.product_id.notin_(select(Product.id))
        ).values(product_id=None)
    )
    await session.commit()
