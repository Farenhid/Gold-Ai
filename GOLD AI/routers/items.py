from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from models import JewelryItem, StandardItem
from schemas import (
    JewelryItemCreate,
    JewelryItemResponse,
    StandardItemCreate,
    StandardItemResponse,
)

router = APIRouter()


# ----- Jewelry -----
@router.post("/jewelry", response_model=JewelryItemResponse)
def create_jewelry_item(
    payload: JewelryItemCreate,
    db: Session = Depends(get_db),
):
    item = JewelryItem(
        jewelry_code=payload.jewelry_code,
        name=payload.name,
        weight_grams=payload.weight_grams,
        purity=payload.purity,
        premium=payload.premium,
        status=payload.status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return JewelryItemResponse.model_validate(item)


@router.get("/jewelry", response_model=list[JewelryItemResponse])
def list_jewelry_items(db: Session = Depends(get_db)):
    items = db.query(JewelryItem).all()
    return [JewelryItemResponse.model_validate(i) for i in items]


# ----- Standard items -----
@router.post("/standard", response_model=StandardItemResponse)
def create_standard_item(
    payload: StandardItemCreate,
    db: Session = Depends(get_db),
):
    item = StandardItem(
        name=payload.name,
        weight_grams=payload.weight_grams,
        purity=payload.purity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return StandardItemResponse.model_validate(item)


@router.get("/standard", response_model=list[StandardItemResponse])
def list_standard_items(db: Session = Depends(get_db)):
    items = db.query(StandardItem).all()
    return [StandardItemResponse.model_validate(i) for i in items]
