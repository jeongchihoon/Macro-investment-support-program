from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiosqlite
from app.database import DB_PATH
from app.services import yfinance_client

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

class PortfolioItem(BaseModel):
    ticker: str
    buy_price: float
    quantity: float

@router.get("")
async def get_portfolio():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM portfolio ORDER BY created_at DESC") as cursor:
            rows = await cursor.fetchall()

    items = []
    for row in rows:
        ticker = row["ticker"]
        try:
            ov = yfinance_client.get_overview(ticker)
            current_price = ov.get("current_price") or 0
        except:
            current_price = 0

        buy_price = row["buy_price"]
        quantity = row["quantity"]
        invested = buy_price * quantity
        current_value = current_price * quantity
        profit_loss = current_value - invested
        profit_pct = (profit_loss / invested * 100) if invested else 0

        items.append({
            "id": row["id"],
            "ticker": ticker,
            "company_name": row["company_name"] or ticker,
            "buy_price": buy_price,
            "quantity": quantity,
            "current_price": current_price,
            "invested": round(invested, 2),
            "current_value": round(current_value, 2),
            "profit_loss": round(profit_loss, 2),
            "profit_pct": round(profit_pct, 2),
        })
    return {"items": items}

@router.post("")
async def add_portfolio(item: PortfolioItem):
    company_name = item.ticker
    try:
        ov = yfinance_client.get_overview(item.ticker)
        company_name = ov.get("name", item.ticker)
    except:
        pass

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO portfolio (ticker, company_name, buy_price, quantity) VALUES (?, ?, ?, ?)",
            (item.ticker.upper(), company_name, item.buy_price, item.quantity)
        )
        await db.commit()
    return {"status": "ok", "ticker": item.ticker.upper()}

@router.delete("/{item_id}")
async def delete_portfolio(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        result = await db.execute("DELETE FROM portfolio WHERE id = ?", (item_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
    return {"status": "ok"}
