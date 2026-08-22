import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import optional_admin, require_admin
from app.database import get_db
from app.models import Lead, Product
from app.schemas import ProductCreate, ProductOut

router = APIRouter()

CATEGORIES = {"split", "vrf", "fan_coil", "kkb", "chiller", "obvyazka", "ventilation"}


def slugify_id(name: str) -> str:
    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    lowered = name.lower()
    translated = "".join(translit.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "_", translated).strip("_")[:40]
    return slug or "prod"


@router.get("", response_model=list[ProductOut])
async def list_products(
    include_inactive: bool = False,
    _admin: str | None = Depends(optional_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).order_by(Product.created_at, Product.id)
    if not include_inactive:
        query = query.where(Product.is_active.is_(True))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


def _validate(product_in: ProductCreate) -> None:
    if product_in.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Неизвестная категория")
    if product_in.type not in ("standard", "inverter"):
        raise HTTPException(status_code=400, detail="Тип должен быть standard или inverter")
    if not product_in.name.strip():
        raise HTTPException(status_code=400, detail="Укажите название")


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    payload: ProductCreate,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    _validate(payload)
    product_id = (payload.id or "").strip() or slugify_id(payload.name)
    base_id = product_id
    counter = 1
    while await db.get(Product, product_id):
        counter += 1
        product_id = f"{base_id}_{counter}"

    product = Product(
        id=product_id,
        name=payload.name.strip(),
        brand=payload.brand.strip().lower(),
        category=payload.category,
        price=payload.price,
        area=payload.area,
        type=payload.type,
        features=payload.features,
        specs=payload.specs,
        image=payload.image,
        is_active=payload.is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    payload: ProductCreate,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    _validate(payload)

    product.name = payload.name.strip()
    product.brand = payload.brand.strip().lower()
    product.category = payload.category
    product.price = payload.price
    product.area = payload.area
    product.type = payload.type
    product.features = payload.features
    product.specs = payload.specs
    product.image = payload.image
    product.is_active = payload.is_active
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    _admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    leads = await db.execute(select(Lead).where(Lead.product_id == product_id))
    for lead in leads.scalars():
        lead.product_id = None

    await db.delete(product)
    await db.commit()
