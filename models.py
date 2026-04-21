from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    serial = Column(String, unique=True, index=True)
    event_name = Column(String)
    event_type = Column(String)
    participant = Column(String)
    status = Column(String, default="valid")
    created_at = Column(DateTime, default=datetime.utcnow)
