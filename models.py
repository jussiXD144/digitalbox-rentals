from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    digitalbox = relationship("DigitalBox", back_populates="user", uselist=False)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    stripe_subscription_id = Column(String, unique=True, index=True)
    status = Column(String)  # active, canceled, past_due, etc.
    plan_name = Column(String)
    current_period_end = Column(DateTime)
    
    user = relationship("User", back_populates="subscriptions")

class NichePage(Base):
    __tablename__ = "niche_pages"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True)
    title = Column(String)
    meta_description = Column(String)
    h1 = Column(String)
    subtitle = Column(String)
    problem_statement = Column(String)
    solution_benefits = Column(String) # JSON string of bullet points
    target_audience = Column(String)

class DigitalBox(Base):
    __tablename__ = "digitalboxes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    storage_path = Column(String)
    is_active = Column(Boolean, default=False)
    current_storage_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="digitalbox")
