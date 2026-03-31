from sqlalchemy import (
    Column, Integer, DateTime, Date,
    ForeignKey, Numeric, String, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Payroll(Base):
    __tablename__ = "payroll"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # which month/year this payroll is for
    month = Column(Integer, nullable=False)   # 1-12
    year = Column(Integer, nullable=False)

    # earnings breakdown
    base_salary = Column(Numeric(10, 2), nullable=False)   # monthly base
    overtime_bonus = Column(Numeric(10, 2), default=0)     # extra hours pay
    performance_bonus = Column(Numeric(10, 2), default=0)  # HR adds manually
    gross_salary = Column(Numeric(10, 2), nullable=False)  # sum of all earnings

    # deductions breakdown
    income_tax = Column(Numeric(10, 2), nullable=False)
    social_security = Column(Numeric(10, 2), nullable=False)
    total_deductions = Column(Numeric(10, 2), nullable=False)

    # final amount
    net_pay = Column(Numeric(10, 2), nullable=False)

    # attendance stats for this month
    days_present = Column(Integer, default=0)
    days_absent = Column(Integer, default=0)
    overtime_hours = Column(Numeric(5, 2), default=0)

    # status
    is_paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)

    # who generated this payroll
    generated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    employee = relationship("Employee", backref="payroll_records")
    generated_by = relationship("User", foreign_keys=[generated_by_id])