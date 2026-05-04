import os
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, DECIMAL, Integer, String, Text, func
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/bedrock_legacy")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price = Column(DECIMAL(10, 2), nullable=False)
    stock = Column(Integer, default=0)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))


class ShoppingCart(Base):
    __tablename__ = "shopping_carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)


class ProductCreate(BaseModel):
    name: str = Field(..., example="Dell XPS 15")
    description: Optional[str] = Field(None, example="Powerful Windows laptop")
    category: Optional[str] = Field(None, example="laptops")
    price: float = Field(..., example=1999.99)
    stock: int = Field(0, example=15)


class ProductRead(ProductCreate):
    id: int

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str = Field(..., example="alice")
    email: str = Field(..., example="alice@example.com")
    full_name: Optional[str] = Field(None, example="Alice Johnson")


class UserRead(UserCreate):
    id: int

    class Config:
        orm_mode = True


class CartAddRequest(BaseModel):
    user_id: int = Field(..., example=1)
    product_id: int = Field(..., example=1)
    quantity: int = Field(1, example=1)


class CartItemRead(BaseModel):
    product_id: int
    quantity: int

    class Config:
        orm_mode = True


class CartRead(BaseModel):
    user_id: int
    items: List[CartItemRead]


app = FastAPI(title="Legacy E-commerce System", version="0.1")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/products", response_model=List[ProductRead])
def list_products(
    category: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query_set = db.query(Product)
    if category:
        query_set = query_set.filter(func.lower(Product.category) == category.lower())
    if max_price is not None:
        query_set = query_set.filter(Product.price <= max_price)
    if query:
        search = f"%{query.lower()}%"
        query_set = query_set.filter(func.lower(Product.name).like(search) | func.lower(Product.description).like(search))
    return query_set.order_by(Product.id).all()


@app.post("/api/products", response_model=ProductRead, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/api/users", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@app.post("/api/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(**payload.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/cart/add")
def add_to_cart(payload: CartAddRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    existing = (
        db.query(ShoppingCart)
        .filter(ShoppingCart.user_id == payload.user_id, ShoppingCart.product_id == payload.product_id)
        .first()
    )
    if existing:
        existing.quantity += payload.quantity
        db.add(existing)
    else:
        cart_item = ShoppingCart(**payload.dict())
        db.add(cart_item)
    db.commit()
    return {"status": "ok", "user_id": payload.user_id, "product_id": payload.product_id, "quantity": payload.quantity}


@app.get("/api/cart/{user_id}", response_model=CartRead)
def get_cart(user_id: int, db: Session = Depends(get_db)):
    items = (
        db.query(ShoppingCart)
        .filter(ShoppingCart.user_id == user_id)
        .order_by(ShoppingCart.id)
        .all()
    )
    return {"user_id": user_id, "items": items}
