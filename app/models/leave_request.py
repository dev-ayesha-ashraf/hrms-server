from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class LeaveType(str, enum.Enum):
    annual = "annual"
    sick = "sick"
    unpaid = "unpaid"
    maternity = "maternity"
    paternity = "paternity"
    emergency = "emergency"


class LeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)

    # who is requesting leave
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # leave details
    leave_type = Column(Enum(LeaveType, native_enum=False), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)

    # workflow fields
    status = Column(
        Enum(LeaveStatus, native_enum=False),
        default=LeaveStatus.pending,
        nullable=False,
    )

    # who approved/rejected and when
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)  # HR's comment on approval/rejection

    # timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    employee = relationship("Employee", backref="leave_requests")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])