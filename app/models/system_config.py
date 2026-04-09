# app/models/system_config.py
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)
    weekly_cron = Column(String, nullable=False, default="0 9 * * 3")
    ai_model = Column(String, nullable=False, default="deepseek")
    default_max_items_per_run = Column(Integer, nullable=False, default=5)
    force_recent = Column(Boolean, nullable=False, default=False)
    summarize_prompt = Column(Text, nullable=True)
    translate_prompt = Column(Text, nullable=True)
