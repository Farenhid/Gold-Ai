from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import models  # noqa: F401 - register models with Base.metadata
from routers import bank_accounts, customers, items, transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Gold and Jewelry Accounting API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bank_accounts.router, prefix="/bank_accounts", tags=["Bank Accounts"])
app.include_router(customers.router, prefix="/customers", tags=["Customers"])
app.include_router(items.router, prefix="/items", tags=["Inventory"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])


@app.get("/")
def root():
    return {"message": "Gold and Jewelry Accounting API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
