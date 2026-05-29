import os
import logging
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from app.database import get_db, init_db, Customer, Order, OrderItem, RefundHistory
from app.seed import seed_data
from app.agent import run_agent_chat, agent_logger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    init_db()
    db = next(get_db())
    if db.query(Customer).count() == 0:
        logger.info("Database is empty. Running initial seed...")
        seed_data(db)
except Exception as db_err:
    logger.error(f"Failed to initialize database tables: {db_err}")

app = FastAPI(
    title="NoonSupport Refund Agent Backend",
    description="Local FastAPI server hosting the AI Customer Support Agent and mock database queries.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    logs: List[Dict[str, Any]]


@app.get("/api/health")
def health_check():
    """
    Basic health check to verify backend server status.
    """
    return {
        "status": "healthy",
        "api_keys_configured": {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY"))
        }
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Processes a customer chat message through the support agent loop (LLM or Safe-Mock).
    Returns the agent's response along with the real-time reasoning logs.
    """
    session_id = payload.session_id.strip()
    message = payload.message.strip()
    
    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required.")
        
    try:
        response_text = run_agent_chat(session_id, message, db)
        
        session_logs = agent_logger.get_logs(session_id)
        
        return ChatResponse(
            response=response_text,
            logs=session_logs
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        agent_logger.log(session_id, "error", "Endpoint Crash", str(e))
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")

@app.get("/api/logs/{session_id}")
def get_session_logs(session_id: str):
    """
    Retrieve the step-by-step reasoning log traces for a specific session ID.
    """
    logs = agent_logger.get_logs(session_id)
    return {"session_id": session_id, "logs": logs}

@app.get("/api/logs")
def get_all_logs():
    """
    Retrieve reasoning traces for all active sessions.
    """
    return agent_logger.get_all_logs()

@app.get("/api/crm")
def get_crm_data(db: Session = Depends(get_db)):
    """
    Retrieve a clean, detailed list of all customer records, their order history,
    and refund transactions. Allows transparent admin monitoring.
    """
    try:
        customers = db.query(Customer).all()
        result = []
        
        for c in customers:
            orders = []
            for o in c.orders:
                items = []
                for item in o.items:
                    items.append({
                        "id": item.id,
                        "product_name": item.product_name,
                        "price": item.price,
                        "quantity": item.quantity,
                        "is_final_sale": item.is_final_sale,
                        "is_refunded": item.is_refunded
                    })
                
                orders.append({
                    "id": o.id,
                    "purchase_date": o.purchase_date.isoformat() if o.purchase_date else None,
                    "delivery_date": o.delivery_date.isoformat() if o.delivery_date else None,
                    "total_amount": o.total_amount,
                    "status": o.status,
                    "payment_method": o.payment_method,
                    "items": items
                })
                
            result.append({
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "tier": c.tier,
                "orders": orders
            })
            
        refunds = db.query(RefundHistory).order_by(RefundHistory.processed_at.desc()).all()
        refund_list = []
        for r in refunds:
            refund_list.append({
                "id": r.id,
                "order_id": r.order_id,
                "item_id": r.item_id,
                "product_name": r.item.product_name if r.item else "Full Order",
                "amount": r.amount,
                "status": r.status,
                "reason": r.reason,
                "decision_reason": r.decision_reason,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None
            })
            
        return {
            "customers": result,
            "refunds": refund_list
        }
    except Exception as e:
        logger.error(f"Error fetching CRM data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
def reset_database(db: Session = Depends(get_db)):
    """
    Completely resets the database schema, wipes existing tables,
    re-seeds with mock records, and clears all agent execution traces.
    """
    try:
        logger.info("Admin triggered database reset and seed...")
        seed_data(db)
        for k in list(agent_logger.traces.keys()):
            agent_logger.clear(k)
        return {"status": "success", "message": "Database and execution traces have been reset successfully!"}
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise HTTPException(status_code=500, detail=str(e))
