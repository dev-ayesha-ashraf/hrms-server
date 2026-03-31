from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
from decimal import Decimal


# ── COLORS ───────────────────────────────────────────────
NAVY      = colors.HexColor("#1a237e")
DARK      = colors.HexColor("#212121")
MUTED     = colors.HexColor("#757575")
GREEN     = colors.HexColor("#2e7d32")
RED       = colors.HexColor("#c62828")
LIGHT_BG  = colors.HexColor("#f5f5f5")
GREEN_BG  = colors.HexColor("#e8f5e9")
WHITE     = colors.white


MONTHS = [
    "", "January", "February", "March", "April",
    "May", "June", "July", "August", "September",
    "October", "November", "December"
]


def fmt(value) -> str:
    """Format a number as money string."""
    return f"${float(value):,.2f}"


def generate_payslip_pdf(payslip: dict) -> bytes:
    """
    Takes a payslip dict and returns PDF bytes.
    payslip dict matches PayrollResponse shape.
    """
    buffer = BytesIO()  # in-memory file — no disk needed

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # all content goes into this list — reportlab renders it top to bottom
    elements = []

    styles = getSampleStyleSheet()

    # ── CUSTOM STYLES ────────────────────────────────────
    def style(name, **kwargs):
        return ParagraphStyle(name, parent=styles["Normal"], **kwargs)

    title_style    = style("title",    fontSize=22, textColor=NAVY, fontName="Helvetica-Bold")
    sub_style      = style("sub",      fontSize=10, textColor=MUTED)
    heading_style  = style("heading",  fontSize=11, textColor=MUTED, fontName="Helvetica-Bold", spaceAfter=2)
    name_style     = style("name",     fontSize=16, fontName="Helvetica-Bold", textColor=DARK)
    job_style      = style("job",      fontSize=11, textColor=MUTED)
    right_style    = style("right",    fontSize=11, alignment=TA_RIGHT)
    right_bold     = style("rightb",   fontSize=13, alignment=TA_RIGHT, fontName="Helvetica-Bold")
    label_style    = style("label",    fontSize=10, textColor=MUTED)
    value_style    = style("value",    fontSize=10, textColor=DARK)
    value_red      = style("vred",     fontSize=10, textColor=RED)
    value_bold     = style("vbold",    fontSize=11, fontName="Helvetica-Bold", textColor=DARK)
    value_red_bold = style("vrb",      fontSize=11, fontName="Helvetica-Bold", textColor=RED)

    emp = payslip["employee"]
    full_name = f"{emp['first_name']} {emp['last_name']}"
    period = f"{MONTHS[payslip['month']]} {payslip['year']}"
    slip_number = f"#{str(payslip['id']).zfill(6)}"

    # ── HEADER ROW ────────────────────────────────────────
    header_data = [[
        Paragraph("HRMS", title_style),
        Paragraph(f"<b>{period}</b><br/>{slip_number}", right_bold),
    ]]
    header_table = Table(header_data, colWidths=["60%", "40%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Paragraph("Payslip", sub_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=12))

    # ── EMPLOYEE INFO ─────────────────────────────────────
    elements.append(Paragraph("Employee", heading_style))
    elements.append(Paragraph(full_name, name_style))
    elements.append(Paragraph(emp["job_title"], job_style))
    elements.append(Spacer(1, 12))

    # ── ATTENDANCE STATS ──────────────────────────────────
    att_data = [[
        Paragraph(f"<b>{payslip['days_present']}</b> days present", value_style),
        Paragraph(f"<b>{payslip['days_absent']}</b> days absent", value_style),
        Paragraph(
            f"<b>{float(payslip['overtime_hours']):.1f}h</b> overtime"
            if float(payslip.get("overtime_hours", 0)) > 0 else "",
            value_style
        ),
    ]]
    att_table = Table(att_data, colWidths=["33%", "33%", "34%"])
    att_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(att_table)
    elements.append(Spacer(1, 16))

    # ── EARNINGS TABLE ────────────────────────────────────
    elements.append(Paragraph("Earnings", heading_style))

    earnings_rows = [
        [Paragraph("Base Salary", label_style), Paragraph(fmt(payslip["base_salary"]), value_style)],
    ]

    if float(payslip.get("overtime_bonus", 0)) > 0:
        earnings_rows.append([
            Paragraph("Overtime Bonus", label_style),
            Paragraph(fmt(payslip["overtime_bonus"]), value_style),
        ])

    if float(payslip.get("performance_bonus", 0)) > 0:
        earnings_rows.append([
            Paragraph("Performance Bonus", label_style),
            Paragraph(fmt(payslip["performance_bonus"]), value_style),
        ])

    earnings_rows.append([
        Paragraph("Gross Salary", style("gl", fontName="Helvetica-Bold", fontSize=10)),
        Paragraph(fmt(payslip["gross_salary"]), value_bold),
    ])

    earnings_table = Table(earnings_rows, colWidths=["70%", "30%"])
    earnings_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#eeeeee")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, -1), 4),
    ]))
    elements.append(earnings_table)
    elements.append(Spacer(1, 14))

    # ── DEDUCTIONS TABLE ──────────────────────────────────
    elements.append(Paragraph("Deductions", heading_style))

    deduction_rows = [
        [Paragraph("Income Tax", label_style),         Paragraph(f"-{fmt(payslip['income_tax'])}", value_red)],
        [Paragraph("Social Security (5%)", label_style), Paragraph(f"-{fmt(payslip['social_security'])}", value_red)],
        [
            Paragraph("Total Deductions", style("dl", fontName="Helvetica-Bold", fontSize=10)),
            Paragraph(f"-{fmt(payslip['total_deductions'])}", value_red_bold),
        ],
    ]

    deductions_table = Table(deduction_rows, colWidths=["70%", "30%"])
    deductions_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#eeeeee")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, RED),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, -1), 4),
    ]))
    elements.append(deductions_table)
    elements.append(Spacer(1, 16))

    # ── NET PAY BOX ───────────────────────────────────────
    net_style = style("net", fontSize=18, fontName="Helvetica-Bold",
                      textColor=WHITE, alignment=TA_RIGHT)
    net_label = style("netlabel", fontSize=13, fontName="Helvetica-Bold",
                      textColor=WHITE)

    net_data = [[
        Paragraph("Net Pay", net_label),
        Paragraph(fmt(payslip["net_pay"]), net_style),
    ]]
    net_table = Table(net_data, colWidths=["50%", "50%"])
    net_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 10))

    # ── PAYMENT STATUS ────────────────────────────────────
    status_text = "✓ Payment Confirmed" if payslip["is_paid"] else "⏳ Payment Pending"
    status_color = GREEN if payslip["is_paid"] else colors.HexColor("#f57f17")
    status_bg = GREEN_BG if payslip["is_paid"] else colors.HexColor("#fff8e1")

    status_style_p = style(
        "statusp", fontSize=11, fontName="Helvetica-Bold",
        textColor=status_color
    )

    status_data = [[Paragraph(status_text, status_style_p)]]
    status_table = Table(status_data, colWidths=["100%"])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
    ]))
    elements.append(status_table)

    if payslip.get("notes"):
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"Note: {payslip['notes']}", sub_style))

    # ── FOOTER ────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=MUTED))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "This is a computer-generated payslip and does not require a signature.",
        style("footer", fontSize=8, textColor=MUTED, alignment=TA_CENTER)
    ))

    # ── BUILD THE PDF ─────────────────────────────────────
    doc.build(elements)

    # return the bytes from the in-memory buffer
    buffer.seek(0)
    return buffer.read()