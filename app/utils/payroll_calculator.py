from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple


class PayrollResult(NamedTuple):
    base_salary: Decimal
    overtime_bonus: Decimal
    performance_bonus: Decimal
    gross_salary: Decimal
    income_tax: Decimal
    social_security: Decimal
    total_deductions: Decimal
    net_pay: Decimal


def calculate_income_tax(gross: Decimal) -> Decimal:
    """
    Simple progressive tax brackets (monthly amounts):
    
    $0      - $2,000   →  10%
    $2,001  - $5,000   →  20%
    $5,001  - $10,000  →  25%
    $10,001+           →  30%
    
    Each bracket only taxes the amount WITHIN that bracket.
    This is how real tax works — marginal rates.
    """
    tax = Decimal("0")

    brackets = [
        (Decimal("2000"),  Decimal("0.10")),
        (Decimal("3000"),  Decimal("0.20")),  # 2001-5000
        (Decimal("5000"),  Decimal("0.25")),  # 5001-10000
        (Decimal("Inf"),   Decimal("0.30")),  # 10001+
    ]

    remaining = gross
    prev_limit = Decimal("0")

    for limit, rate in brackets:
        if remaining <= 0:
            break
        if limit == Decimal("Inf"):
            taxable = remaining
        else:
            taxable = min(remaining, limit - prev_limit)

        tax += taxable * rate
        remaining -= taxable
        prev_limit = limit

    return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_payroll(
    annual_salary: float,
    days_present: int,
    working_days_in_month: int,
    overtime_hours: float = 0,
    performance_bonus: float = 0,
) -> PayrollResult:
    """
    Core calculation function.
    
    annual_salary         →  employee's yearly salary from DB
    days_present          →  how many days they came in this month
    working_days_in_month →  total working days (excluding weekends)
    overtime_hours        →  hours worked beyond standard (optional)
    performance_bonus     →  manual bonus added by HR (optional)
    """

    # convert to Decimal for precise arithmetic
    # never use float for money — floating point errors accumulate
    annual = Decimal(str(annual_salary))
    perf_bonus = Decimal(str(performance_bonus))
    ot_hours = Decimal(str(overtime_hours))

    # ── BASE SALARY ──────────────────────────────────────────
    # pro-rate based on attendance
    # if they worked 18 of 22 days they get 18/22 of monthly salary
    monthly_base = annual / Decimal("12")

    if working_days_in_month > 0:
        attendance_ratio = Decimal(str(days_present)) / Decimal(str(working_days_in_month))
    else:
        attendance_ratio = Decimal("1")

    base_salary = (monthly_base * attendance_ratio).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # ── OVERTIME BONUS ───────────────────────────────────────
    # overtime rate = 1.5x the hourly rate
    # hourly rate = annual salary / 52 weeks / 40 hours
    hourly_rate = annual / Decimal("52") / Decimal("40")
    overtime_rate = hourly_rate * Decimal("1.5")
    overtime_bonus = (ot_hours * overtime_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # ── GROSS SALARY ─────────────────────────────────────────
    gross_salary = base_salary + overtime_bonus + perf_bonus

    # ── DEDUCTIONS ───────────────────────────────────────────
    income_tax = calculate_income_tax(gross_salary)

    # social security: flat 5% of gross
    social_security = (gross_salary * Decimal("0.05")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    total_deductions = income_tax + social_security

    # ── NET PAY ──────────────────────────────────────────────
    net_pay = gross_salary - total_deductions

    return PayrollResult(
        base_salary=base_salary,
        overtime_bonus=overtime_bonus,
        performance_bonus=perf_bonus,
        gross_salary=gross_salary,
        income_tax=income_tax,
        social_security=social_security,
        total_deductions=total_deductions,
        net_pay=net_pay,
    )


def get_working_days(year: int, month: int) -> int:
    """Count weekdays (Mon-Fri) in a given month."""
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    working_days = 0
    for day in range(1, days_in_month + 1):
        # weekday() returns 0=Mon ... 6=Sun
        if date(year, month, day).weekday() < 5:
            working_days += 1
    return working_days