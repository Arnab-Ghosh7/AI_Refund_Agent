import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db, Customer, Order, OrderItem, RefundHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_data(db: Session):
    logger.info("Clearing existing tables...")
    db.query(RefundHistory).delete()
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Customer).delete()
    db.commit()
    
    logger.info("Seeding customers...")
    
    now = datetime.utcnow()
    
    customers = [
        Customer(name="Alice Vance", email="alice.vance@example.com", phone="+1-555-0101", tier="Regular"),
        Customer(name="Bob Carter", email="bob.carter@example.com", phone="+1-555-0102", tier="VIP"),
        Customer(name="Charlie Drake", email="charlie.drake@example.com", phone="+1-555-0103", tier="Regular"),
        Customer(name="Diana Prince", email="diana.prince@example.com", phone="+1-555-0104", tier="Regular"),
        Customer(name="Evan Wright", email="evan.wright@example.com", phone="+1-555-0105", tier="VIP"),
        Customer(name="Fiona Gallagher", email="fiona.g@example.com", phone="+1-555-0106", tier="Regular"),
        Customer(name="George Brooks", email="george.b@example.com", phone="+1-555-0107", tier="Regular"),
        Customer(name="Hannah Abbott", email="hannah.a@example.com", phone="+1-555-0108", tier="Regular"),
        Customer(name="Ian Malcolm", email="ian.malcolm@example.com", phone="+1-555-0109", tier="Regular"),
        Customer(name="Julia Roberts", email="julia.r@example.com", phone="+1-555-0110", tier="VIP"),
        Customer(name="Kevin Bacon", email="kevin.bacon@example.com", phone="+1-555-0111", tier="Regular"),
        Customer(name="Laura Croft", email="laura.c@example.com", phone="+1-555-0112", tier="VIP"),
        Customer(name="Michael Scott", email="michael.s@example.com", phone="+1-555-0113", tier="Regular"),
        Customer(name="Nancy Drew", email="nancy.drew@example.com", phone="+1-555-0114", tier="Regular"),
        Customer(name="Oliver Queen", email="oliver.q@example.com", phone="+1-555-0115", tier="Regular"),
    ]
    
    db.add_all(customers)
    db.commit()
    
    customer_map = {c.email: c for c in db.query(Customer).all()}
    
    logger.info("Seeding orders and order items...")
    
    orders = []
    
    # 1. Alice Vance: Standard purchase within 30 days, eligible for auto-refund
    alice = customer_map["alice.vance@example.com"]
    o1 = Order(id=1001, customer_id=alice.id, purchase_date=now - timedelta(days=12), delivery_date=now - timedelta(days=10), total_amount=75.00, status="Delivered", payment_method="Credit Card")
    o1.items = [
        OrderItem(product_name="Worknoon ergonomic desk organizer", price=45.00, quantity=1, is_final_sale=False),
        OrderItem(product_name="Premium copper water bottle", price=30.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o1)
    
    # 2. Bob Carter: VIP Customer, high-value order under $500 ($350)
    bob = customer_map["bob.carter@example.com"]
    o2 = Order(id=1002, customer_id=bob.id, purchase_date=now - timedelta(days=8), delivery_date=now - timedelta(days=6), total_amount=350.00, status="Delivered", payment_method="PayPal")
    o2.items = [
        OrderItem(product_name="Worknoon Noise-Cancelling Headphones Pro", price=350.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o2)
    
    # 3. Charlie Drake: Regular, purchased a Final Sale item
    charlie = customer_map["charlie.drake@example.com"]
    o3 = Order(id=1003, customer_id=charlie.id, purchase_date=now - timedelta(days=5), delivery_date=now - timedelta(days=3), total_amount=150.00, status="Delivered", payment_method="Credit Card")
    o3.items = [
        OrderItem(product_name="Ultra-soft Merino Wool Sweater (Clearance)", price=150.00, quantity=1, is_final_sale=True)
    ]
    orders.append(o3)
    
    # 4. Diana Prince: Regular, order delivered 45 days ago (> 30 days window)
    diana = customer_map["diana.prince@example.com"]
    o4 = Order(id=1004, customer_id=diana.id, purchase_date=now - timedelta(days=48), delivery_date=now - timedelta(days=45), total_amount=95.00, status="Delivered", payment_method="Credit Card")
    o4.items = [
        OrderItem(product_name="Minimalist desk mat - XL", price=45.00, quantity=1, is_final_sale=False),
        OrderItem(product_name="Wireless vertical mouse", price=50.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o4)
    
    # 5. Evan Wright: VIP, high-value order ($1,200), strictly requires escalation (> $500 threshold)
    evan = customer_map["evan.wright@example.com"]
    o5 = Order(id=1005, customer_id=evan.id, purchase_date=now - timedelta(days=4), delivery_date=now - timedelta(days=2), total_amount=1200.00, status="Delivered", payment_method="Credit Card")
    o5.items = [
        OrderItem(product_name="Worknoon Smart Standing Desk Dual-Motor", price=850.00, quantity=1, is_final_sale=False),
        OrderItem(product_name="Active Sitting Balance Stool", price=350.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o5)
    
    # 6. Fiona Gallagher: Regular, order delivered 10 days ago, total is $600 (> $500 strict human escalation)
    fiona = customer_map["fiona.g@example.com"]
    o6 = Order(id=1006, customer_id=fiona.id, purchase_date=now - timedelta(days=12), delivery_date=now - timedelta(days=10), total_amount=600.00, status="Delivered", payment_method="Apple Pay")
    o6.items = [
        OrderItem(product_name="Ergonomic mesh task chair with 4D armrests", price=600.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o6)
    
    # 7. George Brooks: Regular, has an order with a pre-refunded item
    george = customer_map["george.b@example.com"]
    o7 = Order(id=1007, customer_id=george.id, purchase_date=now - timedelta(days=15), delivery_date=now - timedelta(days=13), total_amount=200.00, status="Delivered", payment_method="Credit Card")
    o7.items = [
        OrderItem(id=701, product_name="Mechanical hot-swappable keyboard", price=120.00, quantity=1, is_final_sale=False, is_refunded=True),
        OrderItem(id=702, product_name="Premium coiled USB-C cable", price=80.00, quantity=1, is_final_sale=False, is_refunded=False)
    ]
    orders.append(o7)
    
    # 8. Hannah Abbott: Regular, buyer's remorse on day 8 (< 14 days, approvable)
    hannah = customer_map["hannah.a@example.com"]
    o8 = Order(id=1008, customer_id=hannah.id, purchase_date=now - timedelta(days=9), delivery_date=now - timedelta(days=8), total_amount=80.00, status="Delivered", payment_method="Credit Card")
    o8.items = [
        OrderItem(product_name="Bamboo monitors stand riser", price=80.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o8)
    
    # 9. Ian Malcolm: Regular, buyer's remorse on day 20 (> 14 days, should be denied remorse)
    ian = customer_map["ian.malcolm@example.com"]
    o9 = Order(id=1009, customer_id=ian.id, purchase_date=now - timedelta(days=22), delivery_date=now - timedelta(days=20), total_amount=90.00, status="Delivered", payment_method="Credit Card")
    o9.items = [
        OrderItem(product_name="Dimmable monitor light bar", price=90.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o9)
    
    # 10. Julia Roberts: VIP customer, regular order
    julia = customer_map["julia.r@example.com"]
    o10 = Order(id=1010, customer_id=julia.id, purchase_date=now - timedelta(days=5), delivery_date=now - timedelta(days=4), total_amount=150.00, status="Delivered", payment_method="Apple Pay")
    o10.items = [
        OrderItem(product_name="Executive leather notebook folder", price=150.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o10)
    
    # 11. Kevin Bacon: Regular, damaged item on delivery, order total $150
    kevin = customer_map["kevin.bacon@example.com"]
    o11 = Order(id=1011, customer_id=kevin.id, purchase_date=now - timedelta(days=3), delivery_date=now - timedelta(days=2), total_amount=150.00, status="Delivered", payment_method="Credit Card")
    o11.items = [
        OrderItem(product_name="Tempered glass monitor stand", price=150.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o11)
    
    # 12. Laura Croft: VIP customer, expensive items
    laura = customer_map["laura.c@example.com"]
    o12 = Order(id=1012, customer_id=laura.id, purchase_date=now - timedelta(days=10), delivery_date=now - timedelta(days=8), total_amount=480.00, status="Delivered", payment_method="Credit Card")
    o12.items = [
        OrderItem(product_name="Worknoon Active Balance Board", price=180.00, quantity=1, is_final_sale=False),
        OrderItem(product_name="Professional LED desk panel lights (Dual Pack)", price=300.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o12)

    # 13. Michael Scott: Regular customer, small order
    michael = customer_map["michael.s@example.com"]
    o13 = Order(id=1013, customer_id=michael.id, purchase_date=now - timedelta(days=20), delivery_date=now - timedelta(days=19), total_amount=45.00, status="Delivered", payment_method="Credit Card")
    o13.items = [
        OrderItem(product_name="Fidget spinner metal edition", price=45.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o13)

    # 14. Nancy Drew: Regular, item not received
    nancy = customer_map["nancy.drew@example.com"]
    o14 = Order(id=1014, customer_id=nancy.id, purchase_date=now - timedelta(days=7), delivery_date=None, total_amount=120.00, status="Shipped", payment_method="Credit Card")
    o14.items = [
        OrderItem(product_name="Anti-glare blue light block glasses", price=120.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o14)

    # 15. Oliver Queen: Regular, buyer remorse, day 5
    oliver = customer_map["oliver.q@example.com"]
    o15 = Order(id=1015, customer_id=oliver.id, purchase_date=now - timedelta(days=6), delivery_date=now - timedelta(days=5), total_amount=220.00, status="Delivered", payment_method="Credit Card")
    o15.items = [
        OrderItem(product_name="Acoustic felt wall panels (Set of 6)", price=220.00, quantity=1, is_final_sale=False)
    ]
    orders.append(o15)
    
    db.add_all(orders)
    db.commit()
    
    pre_refund = RefundHistory(
        order_id=1007,
        item_id=701,
        amount=120.00,
        status="Approved",
        reason="Incorrect item received - customer shipped back.",
        decision_reason="Programmatic return validation passed on 2026-05-20.",
        processed_at=now - timedelta(days=6)
    )
    db.add(pre_refund)
    db.commit()
    
    logger.info("Successfully seeded database with 15 customer profiles and detailed order records!")

if __name__ == "__main__":
    init_db()
    db_session = SessionLocal()
    try:
        seed_data(db_session)
    finally:
        db_session.close()
