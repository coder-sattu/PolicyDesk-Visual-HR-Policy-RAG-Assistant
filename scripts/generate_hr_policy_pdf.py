"""Generate a sample HR policy handbook PDF (fictional company)."""
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

COMPANY = "Nimbus Technologies Pvt. Ltd."

# (title, [paragraphs or ("table", rows)])
SECTIONS = [
    ("1. Introduction and Scope", [
        f"This HR Policy Handbook applies to all full-time, part-time and contract employees of {COMPANY} "
        "(\"the Company\") across all offices, including the head office in Baner, Pune and the Bengaluru "
        "branch. Interns are covered by Sections 3, 4, 9 and 10 only. The handbook is effective from "
        "1 April 2026 and replaces all earlier versions.",
        "The Human Resources (HR) department owns this handbook and reviews it every year in March. "
        "Questions about any policy should be sent to hr@nimbustech.example or raised on the HR Helpdesk portal.",
    ]),
    ("2. Working Hours and Attendance", [
        "Standard working hours are 9:30 AM to 6:30 PM, Monday to Friday, including a one-hour lunch break. "
        "Employees must work a minimum of 8 productive hours per day and 40 hours per week.",
        "Core hours are 11:00 AM to 4:00 PM. All employees must be available for meetings during core hours, "
        "whether working from office or from home.",
        "Attendance is recorded through the HRMS clock-in system. Arriving after 10:15 AM is marked as a late "
        "mark. Three late marks in a calendar month result in a deduction of half a day of casual leave.",
        "Employees who forget to clock in must raise an attendance regularisation request within 3 working days, "
        "approved by their reporting manager. A maximum of 4 regularisation requests are allowed per month.",
    ]),
    ("3. Leave Policy", [
        "The leave year runs from 1 January to 31 December. Leave is credited monthly on a pro-rata basis. "
        "The annual leave entitlement for full-time employees is shown below.",
        ("table", [
            ["Leave Type", "Days per Year", "Carry Forward", "Notes"],
            ["Earned / Privilege Leave", "18", "Up to 30 days", "Encashable at exit"],
            ["Casual Leave", "8", "No", "Max 3 days at a time"],
            ["Sick Leave", "10", "No", "Medical certificate if > 2 days"],
            ["Maternity Leave", "26 weeks", "-", "For first two children"],
            ["Paternity Leave", "10 days", "-", "Within 3 months of birth"],
            ["Bereavement Leave", "5 days", "-", "Immediate family"],
            ["Marriage Leave", "3 days", "-", "Once during employment"],
        ]),
        "Earned leave must be applied at least 7 days in advance through the HRMS portal. Casual leave should "
        "be applied at least 1 day in advance, except in emergencies. Sick leave may be applied on the same day "
        "by informing the reporting manager before 10:00 AM.",
        "Unused earned leave of up to 30 days can be carried forward to the next year. Any balance above 30 days "
        "lapses on 31 December. At resignation, the earned leave balance is encashed at the basic salary rate "
        "in the full and final settlement.",
        "Employees on probation are eligible for casual and sick leave only. Earned leave is credited from the "
        "first month but can be used only after confirmation.",
        "Leave without pay (LWP) may be approved by the department head for a maximum of 30 days in a year "
        "after all other leave balances are exhausted.",
    ]),
    ("4. Public Holidays", [
        "The Company observes 10 public holidays per year. The holiday calendar is published on the HR portal "
        "in December for the following year. It includes Republic Day, Holi, Maharashtra Day, Independence Day, "
        "Ganesh Chaturthi, Gandhi Jayanti, Dussehra, Diwali (2 days) and Christmas.",
        "In addition, each employee may choose 2 optional (floating) holidays from the optional holiday list. "
        "Employees who work on a public holiday at the manager's request receive a compensatory off, "
        "which must be used within 60 days.",
    ]),
    ("5. Work From Home and Hybrid Work", [
        "The Company follows a hybrid model. Employees may work from home up to 2 days per week after completing "
        "their probation period. Work from home days must be agreed with the reporting manager in advance.",
        "Employees working from home must be reachable on Teams and phone during core hours, use the "
        "Company VPN for all work systems and keep confidential documents secure.",
        "Full remote work for longer than 2 consecutive weeks requires written approval from the department head "
        "and HR. The Company provides an internet allowance of INR 1,000 per month to employees on the hybrid plan.",
    ]),
    ("6. Probation, Confirmation and Notice Period", [
        "All new employees serve a probation period of 6 months from the date of joining. The probation may be "
        "extended once by up to 3 months if performance expectations are not met.",
        "During probation the notice period is 15 days from either side. After confirmation the notice period is "
        "60 days for all employees, and 90 days for employees at Manager grade and above.",
        "The notice period may be shortened at the Company's discretion. Any shortfall in notice not waived by the "
        "Company may be recovered as basic salary for the unserved days. Earned leave cannot be used to adjust the "
        "notice period.",
        "The full and final settlement is processed within 45 days of the last working day, after the employee "
        "completes the exit checklist and returns all Company assets.",
    ]),
    ("7. Compensation, Payroll and Benefits", [
        "Salaries are credited to the employee's bank account on the last working day of each month. Payslips are "
        "available on the HRMS portal. Payroll queries must be raised before the 5th of the following month.",
        "All confirmed employees and their families (spouse, up to two children and parents) are covered by a "
        "group medical insurance family floater of INR 5,00,000 per year. Employees may add parents-in-law by "
        "paying the additional premium.",
        "The Company provides term life insurance of 3 times the annual CTC and personal accident cover for all "
        "employees from the date of joining.",
        "Employee Referral Bonus: an employee who refers a candidate who joins receives INR 25,000, paid after the "
        "new employee completes 90 days. Referrals for senior roles (Manager and above) earn INR 50,000.",
        "The Company contributes to Provident Fund (PF) as per statutory rules, and gratuity is payable after "
        "5 years of continuous service as per the Payment of Gratuity Act.",
    ]),
    ("8. Travel and Expense Reimbursement", [
        "Business travel must be pre-approved by the reporting manager through the travel request form. "
        "Domestic flights are booked in economy class. Train travel is allowed in AC 2-tier.",
        ("table", [
            ["Grade", "Hotel Limit / Night", "Daily Allowance"],
            ["Associate / Engineer", "INR 4,000", "INR 800"],
            ["Senior Engineer / Lead", "INR 6,000", "INR 1,200"],
            ["Manager and above", "INR 9,000", "INR 1,800"],
        ]),
        "Expense claims must be submitted on the HRMS portal with original bills within 30 days of returning "
        "from travel. Claims submitted after 30 days need department head approval, and claims older than "
        "90 days are not reimbursed. Approved claims are paid with the next monthly salary.",
        "Local conveyance for client visits is reimbursed at INR 12 per km for a car and INR 5 per km for a "
        "two-wheeler, or the actual cab fare with receipt.",
    ]),
    ("9. Code of Conduct", [
        "Employees are expected to act with honesty, integrity and respect towards colleagues, clients and "
        "partners. Discrimination or harassment on the basis of gender, religion, caste, age, disability or any "
        "other characteristic is strictly prohibited.",
        "Employees must avoid conflicts of interest. Any outside employment, freelance work or directorship must "
        "be disclosed to HR and approved in writing before it begins.",
        "Gifts from vendors or clients above INR 2,000 in value must be declared to HR and may not be accepted "
        "without approval. Cash gifts of any amount are not allowed.",
        "Company laptops and accounts are for business use. Sharing passwords, installing unlicensed software or "
        "copying client data to personal devices is a violation of the IT Security Policy.",
        "The dress code is business casual from Monday to Thursday and casual on Fridays. Formal attire is "
        "required for client meetings.",
    ]),
    ("10. Prevention of Sexual Harassment (POSH)", [
        "The Company is committed to a workplace free from sexual harassment, in line with the Sexual Harassment "
        "of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013.",
        "An Internal Committee (IC) is constituted at each office, chaired by a senior woman employee and including "
        "an external member. Complaints can be made in writing to the IC at ic@nimbustech.example within 3 months of "
        "the incident.",
        "The IC completes its inquiry within 90 days. The identity of the complainant, the respondent and witnesses "
        "is kept confidential. Retaliation against anyone who raises a complaint is a serious offence.",
        "All employees must complete the online POSH awareness training within 30 days of joining and once every year.",
    ]),
    ("11. Performance Management", [
        "The performance cycle runs from April to March. Goals are set in April, a mid-year review happens in "
        "October, and the annual appraisal is completed in April with salary revisions effective from 1 April.",
        "Performance is rated on a 5-point scale: 5 - Outstanding, 4 - Exceeds Expectations, 3 - Meets "
        "Expectations, 2 - Needs Improvement, 1 - Unsatisfactory.",
        "Employees who joined after 1 October are not eligible for the annual increment in that cycle but receive "
        "a probation review instead. Employees rated 2 or below may be placed on a Performance Improvement Plan "
        "(PIP) of 60 days.",
        "Promotions are reviewed twice a year, in April and October, based on performance rating, role readiness "
        "and business need.",
    ]),
    ("12. Learning and Development", [
        "Each confirmed employee has a learning budget of INR 20,000 per year for certifications, courses and "
        "conferences approved by the reporting manager.",
        "Certification fees are reimbursed only after the employee passes the exam. If an employee resigns within "
        "12 months of a reimbursement above INR 10,000, the amount is recovered in the full and final settlement.",
        "Employees can take up to 3 days of paid learning leave per year to attend approved training or exams.",
    ]),
    ("13. Grievance Redressal", [
        "Employees should first raise a concern with their reporting manager. If the issue is not resolved within "
        "7 working days, it can be escalated to the HR Business Partner, and then to the Grievance Committee.",
        "The Grievance Committee responds within 15 working days. Employees can also raise concerns anonymously "
        "through the Whistleblower channel at ethics@nimbustech.example.",
    ]),
    ("14. Exit Process", [
        "Resignations must be submitted through the HRMS portal. The reporting manager and HR hold an exit "
        "discussion within 5 working days of the resignation.",
        "On the last working day, the employee must return the laptop, ID card, access card and any other "
        "Company property. The relieving letter and experience letter are issued along with the full and "
        "final settlement.",
    ]),
]


def build(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#1e293b"))
    sub = ParagraphStyle("S", parent=styles["Normal"], alignment=TA_CENTER, fontSize=12,
                         textColor=colors.HexColor("#475569"))
    h = ParagraphStyle("H", parent=styles["Heading2"], textColor=colors.HexColor("#4338ca"), spaceBefore=12)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)

    story = [Spacer(1, 6 * cm), Paragraph(COMPANY, title), Spacer(1, 0.4 * cm),
             Paragraph("Employee HR Policy Handbook", sub), Spacer(1, 0.3 * cm),
             Paragraph("Version 3.0 &middot; Effective 1 April 2026 &middot; Baner, Pune", sub),
             Spacer(1, 1 * cm),
             Paragraph("Fictional sample document for RAG demo purposes", sub), PageBreak()]

    for sec_title, items in SECTIONS:
        story.append(Paragraph(sec_title, h))
        for item in items:
            if isinstance(item, tuple):
                tbl = Table(item[1], hAlign="LEFT")
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e7ff")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story += [tbl, Spacer(1, 0.3 * cm)]
            else:
                story.append(Paragraph(item, body))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(2 * cm, 1.2 * cm, f"{COMPANY} - HR Policy Handbook v3.0")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2 * cm,
                      title="HR Policy Handbook", author=COMPANY).build(
        story, onFirstPage=footer, onLaterPages=footer)
    return out_path


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "docs" / "HR_Policy_Handbook.pdf"
    print(f"Created {build(target)}")
