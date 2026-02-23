from sqlalchemy import Column, String, Text, Float, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class Content(Base):
    __tablename__ = "contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(Text, nullable=False)
    original_url = Column(Text, nullable=False, unique=True, index=True)
    transcript = Column(Text)
    summary = Column(Text)
    key_points = Column(ARRAY(Text))
    quality_score = Column(Float, default=0.0)
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
