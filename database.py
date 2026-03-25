import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Index, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Lead(Base):
    """
    Lead model representing a potential client intake with technical specifications.
    """
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20))
    client_email = Column(String(100))
    
    # Technical Specs
    incident_description = Column(Text)
    incident_location = Column(String(200))
    injuries_sustained = Column(String(200))
    insurance_info = Column(String(200))
    
    police_report_filed = Column(Boolean, default=False)
    medical_treatment_received = Column(Boolean, default=False)
    incident_date = Column(String(50))
    
    # AI Analysis
    ai_score = Column(Integer)
    ai_tier = Column(String(30))
    ai_summary = Column(Text)
    liability_score = Column(Integer)
    damages_score = Column(Integer)
    sol_score = Column(Integer)
    red_flags = Column(Text)  # JSON string
    
    # Action Workflow
    recommended_action = Column(String(30))
    action_taken = Column(String(30), default='pending')
    action_taken_at = Column(DateTime)
    lawyer_notified = Column(Boolean, default=False)
    lawyer_notified_at = Column(DateTime)
    status = Column(String(20), default='pending')

    __table_args__ = (
        Index('idx_ai_score', 'ai_score'),
        Index('idx_created_at', 'created_at'),
    )

class DatabaseManager:
    def __init__(self, db_path='legal_intake.db'):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}')
        try:
            # Check if schema is valid
            self.Session = sessionmaker(bind=self.engine)
            session = self.Session()
            session.query(Lead).first()
            session.close()
        except Exception:
            # Schema mismatch or no table - recreate everything
            print("Database schema mismatch detected. Recreating database...")
            if os.path.exists(db_path):
                os.remove(db_path)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def insert_lead(self, data: dict) -> int:
        session = self.Session()
        try:
            new_lead = Lead(**data)
            session.add(new_lead)
            session.commit()
            return new_lead.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_lead_action(self, lead_id: int, action: str, lawyer_notified: bool = False):
        session = self.Session()
        try:
            lead = session.query(Lead).get(lead_id)
            if lead:
                lead.action_taken = action
                lead.action_taken_at = datetime.utcnow()
                if lawyer_notified:
                    lead.lawyer_notified = True
                    lead.lawyer_notified_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    def get_all_leads(self):
        session = self.Session()
        leads = session.query(Lead).order_by(Lead.created_at.desc()).all()
        session.close()
        return leads

    def get_dashboard_stats(self):
        session = self.Session()
        try:
            total_leads = session.query(func.count(Lead.id)).scalar() or 0
            avg_score = session.query(func.avg(Lead.ai_score)).scalar() or 0
            book_now_count = session.query(func.count(Lead.id)).filter(Lead.ai_tier == 'BOOK NOW').scalar() or 0
            
            conversion_rate = (book_now_count / total_leads * 100) if total_leads > 0 else 0
            
            return {
                "total_leads": total_leads,
                "avg_score": round(avg_score, 1) if avg_score else 0.0,
                "book_now_count": book_now_count,
                "conversion_rate": round(conversion_rate, 1)
            }
        finally:
            session.close()

    def seed_data(self):
        session = self.Session()
        if session.query(Lead).count() > 0:
            session.close()
            return

        samples = [
            {
                "client_name": "Michael Harrison",
                "client_phone": "310-555-0102",
                "client_email": "m.harrison@example.com",
                "incident_description": "Rear-ended by a commercial vehicle at high speed.",
                "incident_location": "I-405 South, Los Angeles",
                "injuries_sustained": "Cervical spine fracture, concussion",
                "insurance_info": "State Farm (Policy #99283)",
                "police_report_filed": True,
                "medical_treatment_received": True,
                "incident_date": "2024-03-20",
                "ai_score": 9,
                "ai_tier": "BOOK NOW",
                "ai_summary": "High-value commercial vehicle liability with catastrophic injury profile.",
                "liability_score": 10, "damages_score": 9, "sol_score": 10,
                "red_flags": json.dumps([]),
                "recommended_action": "AUTO_BOOK",
                "status": "completed",
                "action_taken": "Automated Booking Sent"
            }
        ]

        for s in samples:
            session.add(Lead(**s))
        session.commit()
        session.close()

if __name__ == "__main__":
    # Clean restart of DB for new schema (Commented out to keep DB truncated)
    # if os.path.exists('legal_intake.db'):
    #     os.remove('legal_intake.db')
    db = DatabaseManager()
    # db.seed_data()
    print("Database Architecture Ready.")
