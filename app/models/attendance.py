from sqlalchemy import (
    Column, Integer, DateTime, Date,
    ForeignKey, Numeric, String
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)

    clock_in = Column(DateTime(timezone=True), nullable=False)
    clock_out = Column(DateTime(timezone=True), nullable=True)

    # stored as decimal hours e.g. 8.5 = 8 hours 30 minutes
    hours_worked = Column(Numeric(4, 2), nullable=True)

    # optional note — late arrival, early departure, etc.
    note = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    employee = relationship("Employee", backref="attendance_records")