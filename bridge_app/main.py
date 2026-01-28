from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from .database import engine, Base, get_db
from contextlib import asynccontextmanager
from .services.orchestrator import process_transaction

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await process_transaction(file, db)
        return {"status": "success", "data": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/share")
async def handle_share(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Share Target POST request. Returns HTML for the user.
    """
    try:
        result = await process_transaction(file, db)
        if result.get("status") == "duplicate":
            # Extract nested data
            data = result.get("data", {})
            title_class = "duplicate" # We'll reuse error style or create new one
            title_text = "⚠️ Already Processed"
            bg_color = "#fff3cd" # Yellow-ish
            title_color = "#856404"
        else:
            data = result
            title_class = "success"
            title_text = "✅ Transaction Processed"
            bg_color = "#f0f2f5"
            title_color = "green"

        return HTMLResponse(content=f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: {bg_color}; }}
                    .card {{ background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }}
                    .title {{ font-weight: bold; font-size: 1.2rem; margin-bottom: 1rem; color: {title_color}; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <p class="title">{title_text}</p>
                    <p>Amount: {data.get('amount')} {data.get('currency')}</p>
                    <p>Merchant: {data.get('merchant')}</p>
                    <a href="/">Back to Home</a>
                </div>
            </body>
        </html>
        """)
    except Exception as e:
         return HTMLResponse(content=f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                 <style>
                    body {{ font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; background: #fff1f0; }}
                    .card {{ background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; }}
                    .error {{ color: red; font-weight: bold; font-size: 1.2rem; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <p class="error">❌ Failed</p>
                    <p>{str(e)}</p>
                    <a href="/">Try Again</a>
                </div>
            </body>
        </html>
        """, status_code=500)

app.mount("/", StaticFiles(directory="bridge_app/static", html=True), name="static")
