# backend/api/routes/credits.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import json, os, uuid

router = APIRouter()

CREDITS_FILE = "data/credits.json"
TRANSACTIONS_FILE = "data/transactions.json"
os.makedirs("data", exist_ok=True)

for f in [CREDITS_FILE, TRANSACTIONS_FILE]:
    if not os.path.exists(f):
        with open(f, "w") as file:
            json.dump({}, file)

# ─────────────────────────────────────────────────────
# FREE LAUNCH MODE - No payments needed!
# Everyone gets unlimited credits for now
# ─────────────────────────────────────────────────────
FREE_LAUNCH_MODE = True
FREE_CREDITS_PER_USER = 1000  # Give everyone 1000 free credits

# Credit packages (for display only during free mode)
CREDIT_PACKAGES = [
    {
        "id": "free",
        "name": "Launch Special",
        "credits": 1000,
        "price_cents": 0,
        "price_display": "FREE",
        "per_credit": "Free during beta!",
        "badge": "Limited Time",
        "color": "green",
    }
]

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────
def load_credits():
    try:
        with open(CREDITS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_credits(data):
    with open(CREDITS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_transactions():
    try:
        with open(TRANSACTIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_transactions(data):
    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_balance(uid: str) -> int:
    credits = load_credits()
    return credits.get(uid, {}).get("balance", 0)

def add_transaction(uid: str, tx_type: str, amount: int, description: str, balance_after: int, payment_id: str = None):
    transactions = load_transactions()
    if uid not in transactions:
        transactions[uid] = []
    
    transactions[uid].append({
        "id": f"tx_{int(datetime.now().timestamp() * 1000)}",
        "type": tx_type,
        "amount": amount,
        "description": description,
        "balance_after": balance_after,
        "payment_id": payment_id,
        "created_at": datetime.now().isoformat()
    })
    save_transactions(transactions)

# ─────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────
class UseCreditsRequest(BaseModel):
    uid: str
    amount: int = 1
    description: str = "AI image generated"

class InitUserRequest(BaseModel):
    uid: str

# ─────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────

@router.get("/packages")
async def get_packages():
    """Get available credit packages"""
    if FREE_LAUNCH_MODE:
        return {
            "success": True,
            "free_mode": True,
            "message": "🎉 Launch Special! All features FREE during beta.",
            "packages": CREDIT_PACKAGES
        }
    
    # Later when you add payments, show real packages
    return {"success": True, "packages": CREDIT_PACKAGES}

@router.get("/balance/{uid}")
async def get_user_balance(uid: str):
    """Get current credit balance"""
    balance = get_balance(uid)
    
    if FREE_LAUNCH_MODE and balance == 0:
        # Auto-initialize with free credits
        await init_user_credits(InitUserRequest(uid=uid))
        balance = FREE_CREDITS_PER_USER
    
    return {
        "success": True,
        "uid": uid,
        "balance": balance,
        "free_mode": FREE_LAUNCH_MODE
    }

@router.post("/init")
async def init_user_credits(req: InitUserRequest):
    """Initialize new user with free credits"""
    credits = load_credits()
    
    if req.uid in credits:
        return {
            "success": True,
            "message": "User already initialized",
            "balance": credits[req.uid]["balance"]
        }
    
    # Give generous free credits for launch
    credits[req.uid] = {
        "balance": FREE_CREDITS_PER_USER,
        "total_purchased": 0,
        "total_used": 0,
        "created_at": datetime.now().isoformat()
    }
    save_credits(credits)
    
    add_transaction(
        uid=req.uid,
        tx_type="free",
        amount=FREE_CREDITS_PER_USER,
        description=f"🎉 Launch Special - {FREE_CREDITS_PER_USER} free credits!",
        balance_after=FREE_CREDITS_PER_USER
    )
    
    return {
        "success": True,
        "message": f"Welcome! You got {FREE_CREDITS_PER_USER} free credits!",
        "balance": FREE_CREDITS_PER_USER
    }

@router.post("/use")
async def use_credits(req: UseCreditsRequest):
    """
    Deduct credits for AI generation
    During FREE_LAUNCH_MODE: doesn't actually deduct, just logs usage
    """
    credits = load_credits()
    
    if req.uid not in credits:
        # Auto-init
        await init_user_credits(InitUserRequest(uid=req.uid))
        credits = load_credits()
    
    current_balance = credits[req.uid]["balance"]
    
    if FREE_LAUNCH_MODE:
        # FREE MODE: Don't actually deduct credits!
        # Just log the usage for analytics
        add_transaction(
            uid=req.uid,
            tx_type="usage",
            amount=-req.amount,
            description=f"{req.description} (FREE during beta)",
            balance_after=current_balance  # Balance stays the same!
        )
        
        return {
            "success": True,
            "credits_used": req.amount,
            "new_balance": current_balance,  # Unchanged!
            "message": f"✨ Image generated! (Free during beta - credits not deducted)",
            "free_mode": True
        }
    
    # PAID MODE (after launch):
    if current_balance < req.amount:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Have {current_balance}, need {req.amount}."
        )
    
    new_balance = current_balance - req.amount
    credits[req.uid]["balance"] = new_balance
    credits[req.uid]["total_used"] = credits[req.uid].get("total_used", 0) + req.amount
    save_credits(credits)
    
    add_transaction(
        uid=req.uid,
        tx_type="usage",
        amount=-req.amount,
        description=req.description,
        balance_after=new_balance
    )
    
    return {
        "success": True,
        "credits_used": req.amount,
        "new_balance": new_balance,
        "message": f"{req.amount} credit(s) used. Balance: {new_balance}"
    }

@router.get("/history/{uid}")
async def get_transaction_history(uid: str):
    """Get transaction history"""
    transactions = load_transactions()
    user_transactions = transactions.get(uid, [])
    user_transactions.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "success": True,
        "transactions": user_transactions,
        "total": len(user_transactions),
        "free_mode": FREE_LAUNCH_MODE
    }

@router.get("/status")
async def credit_system_status():
    """Check if payment system is active"""
    return {
        "free_mode": FREE_LAUNCH_MODE,
        "free_credits": FREE_CREDITS_PER_USER,
        "message": "Launch mode: All features free!" if FREE_LAUNCH_MODE else "Paid mode active",
        "payments_enabled": not FREE_LAUNCH_MODE
    }