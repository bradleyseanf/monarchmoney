import hashlib
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from ..models import Transaction
from .gemini import extract_transaction_data
from .monarch import get_monarch_client, push_transaction

async def process_transaction(file: UploadFile, db: AsyncSession):
    # 1. Read and Hash
    content = await file.read()
    image_hash = hashlib.sha256(content).hexdigest()
    
    # 2. Deduplication Check
    stmt = select(Transaction).where(Transaction.image_hash == image_hash)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"DUPLICATE TRANSACTION DETECTED: Hash={image_hash}")
        print(f"Existing Data: {existing.parsed_data}")
        return {"status": "duplicate", "data": existing.parsed_data}
    
    # 3. OCR Extraction
    data = extract_transaction_data(content)
    
    # LOGGING FOR VISIBILITY
    print(f"\n\n--- EXTRACTED DATA ---\n{data}\n------------------------\n\n")
    
    
    # 3b. Currency Conversion
    
    # 3b. Currency Conversion
    raw_currency = str(data.get("currency", "")).upper().strip()
    print(f"Currency detection: Raw='{data.get('currency')}' Normalized='{raw_currency}'")
    
    if raw_currency in ["EUR", "EURO", "€"]:
        try:
            from .currency import get_eur_to_usd_rate
            rate = await get_eur_to_usd_rate(data["date"])
            original_amount = data["amount"]
            converted_amount = round(original_amount * rate, 2)
            
            print(f"Converting EUR {original_amount} to USD {converted_amount} (Rate: {rate})")
            
            # Update data for Monarch
            data["original_amount"] = original_amount
            data["original_currency"] = "EUR"
            data["amount"] = converted_amount
            data["currency"] = "USD" # Make it appear as USD to Monarch wrapper
            data["exchange_rate"] = rate
        except Exception as e:
             print(f"Conversion failed, proceeding with original currency: {e}")
    else:
        print(f"Skipping conversion: '{raw_currency}' is not EUR.")

    # Log final payload
    print(f"FINAL PAYLOAD TO MONARCH: {data}")

    if not data or "error" in data:
        error_msg = data.get("error", "Unknown OCR error") if data else "Empty OCR response"
        # If OCR fails, we shouldn't save the hash maybe? OR save it as failed?
        # For now, just raise
        raise HTTPException(status_code=500, detail=error_msg)
        
    # 4. Monarch Push
    from ..models import Credentials
    creds_result = await db.execute(select(Credentials))
    creds = creds_result.scalars().first()
    
    if not creds:
        # TODO: Better error or onboarding flow
        raise HTTPException(status_code=400, detail="No Monarch credentials configured")
        
    try:
        mm = await get_monarch_client(db, creds.id)
        await push_transaction(mm, data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Monarch Error: {str(e)}")
    
    # 5. Save Record
    new_tx = Transaction(image_hash=image_hash, parsed_data=data)
    db.add(new_tx)
    await db.commit()
    
    return data
