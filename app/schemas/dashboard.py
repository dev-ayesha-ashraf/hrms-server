from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_employees: int
    present_today: int
    on_leave: int
    pending_requests: int
    total_payroll_this_month: float