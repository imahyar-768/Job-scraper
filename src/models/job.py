from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    company = Column(String(100), nullable=False)
    location = Column(String(100))
    description = Column(Text)
    url = Column(String(500), unique=True)
    source = Column(String(50))
    
    # Job type and level
    job_type = Column(String(50))
    experience_level = Column(String(50))
    work_type = Column(String(20))  # fully_remote, hybrid, onsite, unknown
    
    # Stack and requirements
    tech_stack = Column(JSON)
    
    # Compensation
    min_salary = Column(Float)
    max_salary = Column(Float)
    currency = Column(String(3))
    salary_period = Column(String(10))
    
    # Benefits and perks
    visa_sponsorship = Column(Boolean, default=False)
    relocation_support = Column(Boolean, default=False)
    benefits = Column(Text)
    
    # Company information
    company_size = Column(String(100))
    industry = Column(String(100))
    
    # Metadata
    posted_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Job(title='{self.title}', company='{self.company}')>"
