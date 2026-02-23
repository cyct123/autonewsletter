from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class SendLog(Base):
    __tablename__ = "send_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_id = Column(UUID(as_uuid=True), nullable=False)
    channel_type = Column(String, nullable=False)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
