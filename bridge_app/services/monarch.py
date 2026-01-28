import os
import asyncio
import pickle
import pyotp
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from monarchmoney import MonarchMoney, RequireMFAException
from ..models import Credentials
from ..utils.crypto import decrypt

# Path for session persistence - logic says store in DB, but library uses file.
# We will use DB to store/retrieve the session pickle bytes.

async def get_monarch_client(db: AsyncSession, user_id: int):
    # Fetch credentials
    creds = await db.get(Credentials, user_id)
    if not creds:
        raise ValueError("No credentials found for user")

    mm = MonarchMoney()
    
    # Try to load session from DB
    if creds.monarch_session:
        import tempfile
        try:
            # Create a temp file to hold the session pickle
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(creds.monarch_session)
                tmp_path = tmp.name
            
            # Load session using library method
            mm.load_session(tmp_path)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            # Verify session is valid
            await mm.get_subscription_details()
            return mm
            
        except Exception as e:
            print(f"Session load/Verify failed: {e}")
            # Fallthrough to error
            pass
    
    # If we get here, session is missing or invalid.
    # We do NOT allow headless login anymore per user request for manual flow.
    raise ValueError("Monarch session expired or missing. Please run 'python scripts/interactive_login.py' to login.")

async def push_transaction(mm: MonarchMoney, data: dict):
    # data: date, amount, currency, merchant
    # Find manual account
    accounts = await mm.get_accounts()
    # Logic to pick account
    # We look for a specific account named "Euro Transactions"
    target_account = None
    target_name = "Euro Transactions"
    
    for acc in accounts['accounts']:
        if acc['displayName'] == target_name:
             target_account = acc
             break
    
    if not target_account:
        raise ValueError(f"No account found with name '{target_name}'. Please create a new Manual account in Monarch named '{target_name}'.")

    # Ensure amount is negative (Expense/Debit)
    # Receipts are always expenses
    amount = -abs(float(data['amount']))
    
    # Check for original currency conversion data
    # Check for original currency conversion data
    if "original_amount" in data:
        notes = (
            f"Original Price: {data['original_currency']} {data['original_amount']:.2f}\n"
            f"Exchange Rate: {data.get('exchange_rate', '?')} USD/EUR"
        )
    elif data['currency'] != 'USD':
        # Apply notes for non-USD that wasn't converted
        notes = f"Original Price: {data['currency']} {abs(amount):.2f}"
    else:
        notes = ""

    # Fetch categories to find a valid category_id (required by API)
    # We'll default to "Uncategorized"
    category_id = None
    try:
        categories_data = await mm.get_transaction_categories()
        # Search for 'Uncategorized' in the response
        # Structure is usually categories -> [ {id, name, ...} ]
        for cat in categories_data.get('categories', []):
            if cat['name'] == 'Uncategorized':
                category_id = cat['id']
                break
        
        if not category_id and categories_data.get('categories'):
            # Fallback to first category if Uncategorized not found
            category_id = categories_data['categories'][0]['id']
            print(f"Warning: 'Uncategorized' category not found. Using fallback: {categories_data['categories'][0]['name']}")

    except Exception as e:
        print(f"Failed to fetch categories: {e}")

    if not category_id:
         raise ValueError("Could not determine a valid category_id for the transaction.")

    # Monarch API `create_transaction` date format? YYYY-MM-DD
    # LOG PAYLOAD
    payload_log = {
        "date": data['date'],
        "account_id": target_account['id'],
        "amount": amount,
        "merchant_name": data['merchant'],
        "notes": notes,
        "category_id": category_id
    }
    print(f"\n\n--- MONARCH PUSH PAYLOAD ---\n{payload_log}\n----------------------------\n")

    result = await mm.create_transaction(
        date=data['date'],
        account_id=target_account['id'],
        amount=amount, # In account currency (assuming manual is USD/EUR?)
        merchant_name=data['merchant'],
        notes=notes,
        category_id=category_id
    )
    
    # Mark as Needs Review
    # create_transaction doesn't support this flag, so we update it immediately after.
    try:
        tx_id = result['createTransaction']['transaction']['id']
        await mm.update_transaction(transaction_id=tx_id, needs_review=True)
        print(f"Marked transaction {tx_id} as 'Needs Review'")
        
        # Apply Tag
        tag_name = "Imported by MM Euro Bridge"
        tag_color = "#2196F3" # Material Blue
        tag_id = None
        
        # 1. Find existing tag
        existing_tags = await mm.get_transaction_tags()
        for tag in existing_tags.get("householdTransactionTags", []):
            if tag["name"] == tag_name:
                tag_id = tag["id"]
                break
        
        # 2. Create if missing
        if not tag_id:
            print(f"Creating new tag: {tag_name}")
            new_tag_res = await mm.create_transaction_tag(name=tag_name, color=tag_color)
            tag_id = new_tag_res["createTransactionTag"]["tag"]["id"]
            
        # 3. Apply tag
        if tag_id:
            await mm.set_transaction_tags(transaction_id=tx_id, tag_ids=[tag_id])
            print(f"Tagged transaction {tx_id} with '{tag_name}'")
            
    except Exception as e:
        print(f"Failed to apply post-creation updates (Needs Review / Tags): {e}")
