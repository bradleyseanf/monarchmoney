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
                <title>Monarch Money Bridge Result</title>
                <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        padding: 2rem; 
                        text-align: center; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                        color: #333;
                    }}
                    .card {{ 
                        background: rgba(255, 255, 255, 0.95);
                        padding: 2.5rem;
                        border-radius: 20px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        max-width: 400px;
                        width: 100%;
                        backdrop-filter: blur(10px);
                    }}
                    .title {{ font-weight: bold; font-size: 1.5rem; margin-bottom: 1rem; color: {title_color}; }}
                    .btn {{ 
                        background: linear-gradient(to right, #667eea, #764ba2); 
                        color: #fff; 
                        padding: 0.8rem 2rem; 
                        border-radius: 50px; 
                        text-decoration: none; 
                        display: inline-block; 
                        margin-top: 1.5rem; 
                        cursor: pointer; 
                        border: none;
                        font-size: 1rem;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                        transition: transform 0.2s;
                    }}
                    .btn:hover {{ transform: translateY(-2px); }}
                    .detail-row {{ display: flex; justify-content: space-between; margin: 0.5rem auto; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; max-width: 260px; }}
                    .label {{ color: #666; }}
                    .value {{ font-weight: 600; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">{ "🎉" if title_class == "success" else "⚠️" }</div>
                    <p class="title">{title_text}</p>
                    
                    <div class="detail-row">
                        <span class="label">Amount</span>
                        <span class="value">{data.get('amount')} {data.get('currency')}</span>
                    </div>
                    <div class="detail-row">
                        <span class="label">Merchant</span>
                        <span class="value">{data.get('merchant')}</span>
                    </div>
                    
                    <a href="/" class="btn">Process Another</a>
                </div>

                <script>
                    if ("{title_class}" === "success") {{
                        confetti({{
                            particleCount: 100,
                            spread: 70,
                            origin: {{ y: 0.6 }}
                        }});
                    }}
                </script>
            </body>
        </html>
        """)
    except Exception as e:
         return HTMLResponse(content=f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                 <style>
                    body {{ 
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        padding: 2rem; 
                        text-align: center; 
                        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%);
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                        color: #333;
                    }}
                    .card {{ 
                        background: rgba(255, 255, 255, 0.95);
                        padding: 2.5rem;
                        border-radius: 20px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        max-width: 400px;
                        width: 100%;
                        backdrop-filter: blur(10px);
                    }}
                    .error {{ color: #e53e3e; font-weight: bold; font-size: 1.5rem; }}
                    .btn {{ 
                         background: linear-gradient(to right, #ff9a9e, #fad0c4); 
                        color: #fff; 
                        padding: 0.8rem 2rem; 
                        border-radius: 50px; 
                        text-decoration: none; 
                        display: inline-block; 
                        margin-top: 1.5rem; 
                        cursor: pointer; 
                        border: none;
                        font-size: 1rem;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🤧</div>
                    <p class="error">Oops! Something went wrong.</p>
                    <p style="color: #666; margin: 1rem 0;">{str(e)}</p>
                    <a href="/" class="btn">Try Again</a>
                </div>
            </body>
        </html>
        """, status_code=500)

app.mount("/", StaticFiles(directory="bridge_app/static", html=True), name="static")
