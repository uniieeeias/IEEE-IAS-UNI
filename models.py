from sqlalchemy import Column, String, DateTime
from datetime import datetime
from database import Base

class Certificate(Base):
    __tablename__ = "certificates"

    serial = Column(String, primary_key=True, index=True)
    event_name = Column(String)
    event_type = Column(String)
    participant = Column(String)
    status = Column(String, default="valid")
    created_at = Column(DateTime, default=datetime.utcnow)