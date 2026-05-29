import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

MYSQL_USER = os.getenv("MYSQL_USER", "noon_admin")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "noon_secure_pass")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "noon_crm")

MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

engine = None
try:
    logger.info(f"Attempting to connect to MySQL database at {MYSQL_HOST}:{MYSQL_PORT}...")
    engine = create_engine(
        MYSQL_URL, 
        pool_pre_ping=True, 
        connect_args={"connect_timeout": 5}
    )
    connection = engine.connect()
    connection.close()
    logger.info("Successfully connected to MySQL database!")
except Exception as e:
    logger.warning(f"MySQL connection failed: {e}. Falling back to SQLite for local development resilience!")
    SQLITE_URL = "sqlite:///./crm.db"
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    logger.info("Successfully initialized SQLite database!")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(50), unique=True, index=True, nullable=False)
    tier = Column(String(20), default="Regular")   
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), default="Pending") 
    payment_method = Column(String(50), default="Credit Card")
    
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    refunds = relationship("RefundHistory", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    is_final_sale = Column(Boolean, default=False)
    is_refunded = Column(Boolean, default=False)  
    
    order = relationship("Order", back_populates="items")

class RefundHistory(Base):
    __tablename__ = "refund_history"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("order_items.id"), nullable=True) 
    amount = Column(Float, nullable=False)
    status = Column(String(50)) 
    reason = Column(String(500), nullable=False)
    decision_reason = Column(String(1000), nullable=True) 
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    order = relationship("Order", back_populates="refunds")
    item = relationship("OrderItem")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully!")
