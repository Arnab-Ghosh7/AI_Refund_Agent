import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import Customer, Order, OrderItem, RefundHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== Core Tools ====================

def get_customer_profile(email_or_phone: str, db: Session) -> dict:
    """
    Search for a customer profile by email address or phone number.
    Returns customer details if found, or an error message.
    """
    logger.info(f"Tool invoked: get_customer_profile with target: {email_or_phone}")
    cleaned_target = email_or_phone.strip()
    
    customer = db.query(Customer).filter(
        (Customer.email == cleaned_target) | (Customer.phone == cleaned_target)
    ).first()
    
    if not customer:
        return {"error": f"No customer found matching identifier: '{email_or_phone}'"}
        
    return {
        "customer_id": customer.id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "tier": customer.tier,
        "created_at": customer.created_at.strftime("%Y-%m-%d") if customer.created_at else None
    }

def get_order_history(customer_id: int, db: Session) -> list:
    """
    Retrieve the full order history and product items for a specific customer ID.
    """
    logger.info(f"Tool invoked: get_order_history for customer_id: {customer_id}")
    
    orders = db.query(Order).filter(Order.customer_id == customer_id).all()
    if not orders:
        return {"message": f"No order history found for customer_id: {customer_id}"}
        
    result = []
    for order in orders:
        items = []
        for item in order.items:
            items.append({
                "item_id": item.id,
                "product_name": item.product_name,
                "price": item.price,
                "quantity": item.quantity,
                "is_final_sale": item.is_final_sale,
                "is_refunded": item.is_refunded
            })
            
        result.append({
            "order_id": order.id,
            "purchase_date": order.purchase_date.strftime("%Y-%m-%d %H:%M:%S") if order.purchase_date else None,
            "delivery_date": order.delivery_date.strftime("%Y-%m-%d %H:%M:%S") if order.delivery_date else "Not Delivered Yet (In Transit)",
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_method": order.payment_method,
            "items": items
        })
    return result

def get_refund_policy() -> str:
    """
    Read and return the strict corporate refund policy rules.
    """
    logger.info("Tool invoked: get_refund_policy")
    policy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "refund_policy.md")
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading refund policy: {str(e)}"

def request_refund(order_id: int, item_id: int, reason: str, amount: float, db: Session) -> dict:
    """
    Process a refund request programmatically.
    Validates rules: Order existence, 30 days limit, Final sale, duplicate check, value limits (> $500 escalation), remorse window.
    If valid, marks the database item as refunded and logs to history.
    """
    logger.info(f"Tool invoked: request_refund for order {order_id}, item {item_id}, amount {amount}, reason: '{reason}'")
    
    # 1. Verify order exists
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"status": "Denied", "message": f"Order #{order_id} does not exist in the database."}
        
    # 2. Verify item exists in this order
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        return {"status": "Denied", "message": f"Item ID {item_id} is not part of Order #{order_id}."}
        
    # 3. Check for previous refunds (duplicate protection)
    if item.is_refunded:
        return {
            "status": "Denied", 
            "message": f"Refund blocked: Product '{item.product_name}' (Item #{item_id}) has already been refunded."
        }
        
    # 4. Check for Final Sale / Clearance
    if item.is_final_sale:
        return {
            "status": "Denied",
            "message": f"Refund blocked: Product '{item.product_name}' was purchased on clearance/final sale and is strictly non-refundable."
        }
        
    # 5. Check Timeframe Limit (30-day window)
    if not order.delivery_date:
        # If item was never delivered, check purchase date
        delivery_date = order.purchase_date
    else:
        delivery_date = order.delivery_date
        
    now = datetime.utcnow()
    days_since_delivery = (now - delivery_date).days
    
    if days_since_delivery > 30:
        return {
            "status": "Denied",
            "message": f"Refund blocked: Delivery was {days_since_delivery} days ago. Refund window closed after 30 days."
        }
        
    # 6. Check Buyer's Remorse Reason limit (14-day window)
    is_remorse = reason.lower().strip() in ["buyer's remorse", "buyers remorse", "changed mind", "don't want it", "dont want it", "changed my mind", "wrong size"]
    if is_remorse and days_since_delivery > 14:
        return {
            "status": "Denied",
            "message": f"Refund blocked: Buyer's Remorse refunds are strictly capped at 14 days after delivery. Delivery was {days_since_delivery} days ago."
        }
        
    # 7. Check Value & strict Human Escalation Threshold (> $500)
    # Check if single item price exceeds 500 or requested amount exceeds 500
    if amount > 500.00 or item.price > 500.00:
        # Programmatically force escalation
        return escalate_to_human(
            order_id=order_id, 
            reason=f"Refund amount (${amount:.2f}) exceeds the auto-approval limit of $500.00.", 
            db=db,
            item_id=item_id,
            amount=amount
        )
        
    # 8. Success: Process the refund!
    # Update item state
    item.is_refunded = True
    
    # Check if all items in order are now refunded, and if so update order status
    all_refunded = True
    for o_item in order.items:
        if not o_item.is_refunded and o_item.id != item_id:
            all_refunded = False
            break
    if all_refunded:
        order.status = "Returned"
        
    # Log refund history
    refund_record = RefundHistory(
        order_id=order_id,
        item_id=item_id,
        amount=amount,
        status="Approved",
        reason=reason,
        decision_reason=f"Programmatic checks passed. Refund auto-approved under 30-day limit (Day {days_since_delivery}) for ${amount:.2f}."
    )
    db.add(refund_record)
    db.commit()
    
    return {
        "status": "Approved",
        "message": f"Refund of ${amount:.2f} for '{item.product_name}' has been successfully approved and credited.",
        "details": {
            "order_id": order_id,
            "product_name": item.product_name,
            "refunded_amount": amount,
            "days_since_delivery": days_since_delivery
        }
    }

def escalate_to_human(order_id: int, reason: str, db: Session, item_id: int = None, amount: float = 0.0) -> dict:
    """
    Escalate a complex case or high-value refund to a human support manager.
    """
    logger.info(f"Tool invoked: escalate_to_human for order {order_id}. Reason: '{reason}'")
    
    # Log to refund history database as Escalated
    refund_record = RefundHistory(
        order_id=order_id,
        item_id=item_id,
        amount=amount if amount > 0 else 0.0,
        status="Escalated",
        reason=f"Escalation Request: {reason}",
        decision_reason=f"Escalated programmatically to a Support Supervisor. Reason: {reason}"
    )
    db.add(refund_record)
    db.commit()
    
    return {
        "status": "Escalated",
        "message": "This request has been successfully escalated to our Senior Customer Support Team.",
        "details": {
            "order_id": order_id,
            "escalation_reason": reason,
            "assigned_department": "Refund Review & Compliance Board",
            "estimated_resolution": "1-2 business hours"
        }
    }
