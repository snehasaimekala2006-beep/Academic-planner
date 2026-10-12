import io
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw institutional running headers,
    footers, page numbers ('Page X of Y'), and watermark.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Institution Header Bar
        self.setFillColor(colors.HexColor('#002B5B'))  # DIET Navy
        self.rect(0, A4[1] - 40, A4[0], 40, fill=1, stroke=0)
        
        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 11)
        self.drawString(36, A4[1] - 25, "DHANEKULA INSTITUTE OF ENGINEERING AND TECHNOLOGY (DIET)")
        
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[0] - 36, A4[1] - 25, "OFFICIAL ACADEMIC REPORT")
        
        # Footer Bar
        self.setStrokeColor(colors.HexColor('#CCCCCC'))
        self.setLineWidth(0.5)
        self.line(36, 45, A4[0] - 36, 45)
        
        self.setFillColor(colors.HexColor('#555555'))
        self.setFont("Helvetica", 8)
        self.drawString(36, 32, "Ganguru, Vijayawada, Andhra Pradesh - 521139 | www.diet.ac.in")
        self.drawRightString(A4[0] - 36, 32, f"Page {self._pageNumber} of {page_count}")
        
        self.restoreState()


def build_student_progress_pdf(student, progress_data, attendance_data):
    """
    Generates official DIET Student Academic & Syllabus Progress PDF Report.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=55,
        bottomMargin=55
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#002B5B'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#002B5B'),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#222222')
    )
    bold_cell = ParagraphStyle(
        'BoldCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    story = []
    
    # Report Header
    story.append(Paragraph("Student Academic Progress & Syllabus Completion Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.utcnow().strftime('%d %B %Y at %H:%M UTC')} | Confidential Official Record", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#002B5B'), spaceAfter=12))

    # Student Info Grid
    info_data = [
        [
            Paragraph("<b>Student Name:</b>", body_style), Paragraph(student.user.full_name, body_style),
            Paragraph("<b>Roll Number:</b>", body_style), Paragraph(student.roll_number, body_style)
        ],
        [
            Paragraph("<b>Branch:</b>", body_style), Paragraph(student.branch.name, body_style),
            Paragraph("<b>Semester:</b>", body_style), Paragraph(f"Semester {student.semester.semester_number}", body_style)
        ],
        [
            Paragraph("<b>Academic Year:</b>", body_style), Paragraph(student.academic_year.label, body_style),
            Paragraph("<b>Section:</b>", body_style), Paragraph(student.section.name if student.section else "N/A", body_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[1.3*inch, 2.3*inch, 1.3*inch, 2.3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))

    # KPI Summary Cards Row
    kpi_data = [
        [
            Paragraph("<b>Overall Syllabus Completion</b>", body_style),
            Paragraph("<b>Overall Attendance</b>", body_style),
            Paragraph("<b>Total Topics Completed</b>", body_style),
            Paragraph("<b>Remaining Study Hours</b>", body_style)
        ],
        [
            Paragraph(f"<font size=14 color='#002B5B'><b>{progress_data['overall_percentage']}%</b></font>", body_style),
            Paragraph(f"<font size=14 color='#002B5B'><b>{attendance_data['overall_percentage']}%</b></font>", body_style),
            Paragraph(f"<font size=14 color='#002B5B'><b>{progress_data['completed_topics']} / {progress_data['total_topics']}</b></font>", body_style),
            Paragraph(f"<font size=14 color='#002B5B'><b>{progress_data['remaining_hours']} hrs</b></font>", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EDF2F7')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Subject-Wise Syllabus Completion Table
    story.append(Paragraph("Subject-Wise Syllabus Completion Breakdown", heading_style))
    subj_table_data = [
        [
            Paragraph("Subject Code", bold_cell),
            Paragraph("Subject Name", bold_cell),
            Paragraph("Type", bold_cell),
            Paragraph("Topics Done", bold_cell),
            Paragraph("Progress", bold_cell),
            Paragraph("Est. Rem. Hours", bold_cell)
        ]
    ]
    for s in progress_data['subjects']:
        subj_table_data.append([
            Paragraph(s['code'], body_style),
            Paragraph(s['name'], body_style),
            Paragraph(s['course_type'], body_style),
            Paragraph(f"{s['completed_topics']} / {s['total_topics']}", body_style),
            Paragraph(f"<b>{s['completion_percentage']}%</b>", body_style),
            Paragraph(f"{s['remaining_hours']} hrs", body_style)
        ])
        
    subj_table = Table(subj_table_data, colWidths=[1.1*inch, 2.5*inch, 0.9*inch, 1.0*inch, 0.9*inch, 0.8*inch])
    subj_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B5B')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(subj_table)
    story.append(Spacer(1, 14))

    # Attendance Breakdown Table
    story.append(Paragraph("Subject-Wise Attendance Details", heading_style))
    att_table_data = [
        [
            Paragraph("Subject Code", bold_cell),
            Paragraph("Subject Name", bold_cell),
            Paragraph("Classes Held", bold_cell),
            Paragraph("Attended", bold_cell),
            Paragraph("Absent", bold_cell),
            Paragraph("Attendance %", bold_cell)
        ]
    ]
    for a in attendance_data['subject_wise']:
        att_table_data.append([
            Paragraph(a['code'], body_style),
            Paragraph(a['name'], body_style),
            Paragraph(str(a['total_classes']), body_style),
            Paragraph(str(a['present_classes']), body_style),
            Paragraph(str(a['absent_classes']), body_style),
            Paragraph(f"<b>{a['percentage']}%</b>", body_style)
        ])
        
    if not attendance_data['subject_wise']:
        att_table_data.append([Paragraph("No attendance records recorded yet.", body_style), "", "", "", "", ""])

    att_table = Table(att_table_data, colWidths=[1.1*inch, 2.7*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.9*inch])
    att_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B5B')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(att_table)
    story.append(Spacer(1, 20))

    # Signature Blocks
    sig_data = [
        [
            Paragraph("____________________________<br/><b>Student Signature</b>", body_style),
            Paragraph("____________________________<br/><b>Faculty Advisor</b>", body_style),
            Paragraph("____________________________<br/><b>Head of Department (HOD)</b>", body_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[2.4*inch, 2.4*inch, 2.4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def build_department_summary_pdf(department, faculty_members, branch_stats, att_rate):
    """
    Generates official DIET Department Academic & Faculty Performance PDF Report for HOD / Principal.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=55, bottomMargin=55)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=colors.HexColor('#002B5B'))
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#002B5B'), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=12)
    bold_cell = ParagraphStyle('BoldCell', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white)

    story = [
        Paragraph(f"Department Performance Summary — {department.name} ({department.code})", title_style),
        Paragraph(f"Generated on: {datetime.utcnow().strftime('%d %B %Y')} | Institutional Evaluation", body_style),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#002B5B'), spaceAfter=10)
    ]
    
    # Faculty Table
    story.append(Paragraph("Department Faculty Roster & Teaching Allocation", heading_style))
    fac_data = [[Paragraph("Emp ID", bold_cell), Paragraph("Faculty Name", bold_cell), Paragraph("Designation", bold_cell), Paragraph("Active Offerings", bold_cell)]]
    for f in faculty_members:
        fac_data.append([
            Paragraph(f.employee_id, body_style),
            Paragraph(f.user.full_name, body_style),
            Paragraph(f.designation, body_style),
            Paragraph(str(f.offerings.count()), body_style)
        ])
    fac_table = Table(fac_data, colWidths=[1.2*inch, 2.8*inch, 2.0*inch, 1.2*inch])
    fac_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B5B')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(fac_table)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


def build_study_plan_pdf(study_plan):
    """
    Generates official DIET Student Study Plan & Timetable PDF Report.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=55, bottomMargin=55)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor('#002B5B'))
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#002B5B'), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=8.5, leading=11)
    bold_cell = ParagraphStyle('BoldCell', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white)

    student = study_plan.student
    story = [
        Paragraph(f"Academic Study Schedule & Daily Timetable — {study_plan.title}", title_style),
        Paragraph(f"Student: <b>{student.user.full_name}</b> ({student.roll_number}) | Branch: {student.branch.code} | Sem: {student.semester.label}", body_style),
        Paragraph(f"Plan Timeframe: <b>{study_plan.start_date.strftime('%d %b %Y')}</b> to <b>{study_plan.target_date.strftime('%d %b %Y')}</b> | Target: <b>{study_plan.available_hours_per_day} hrs/day</b> ({study_plan.days_per_week} days/wk) | Mode: <b>{'AI Optimized' if study_plan.is_ai_generated else 'Deterministic Engine'}</b>", body_style),
        Spacer(1, 8),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#002B5B'), spaceAfter=8)
    ]

    # Tasks Table
    story.append(Paragraph("Scheduled Study Tasks & Milestone Breakdown", heading_style))
    task_data = [[
        Paragraph("Date", bold_cell),
        Paragraph("Subject", bold_cell),
        Paragraph("Type", bold_cell),
        Paragraph("Duration", bold_cell),
        Paragraph("Topic & Study Milestone", bold_cell),
        Paragraph("Status", bold_cell)
    ]]

    for t in study_plan.tasks:
        status_color = '#10B981' if t.status == 'COMPLETED' else ('#EF4444' if t.status == 'MISSED' else '#4B5563')
        status_html = f"<font color='{status_color}'><b>{t.status}</b></font>"
        topic_title = t.topic.topic_name if t.topic else (t.unit.unit_title if t.unit else 'Revision Block')
        notes = f"{topic_title}<br/><font color='#6B7280' size='7'>{t.reason_notes or ''}</font>"
        
        task_data.append([
            Paragraph(t.task_date.strftime('%d %b (%a)'), body_style),
            Paragraph(f"<b>{t.subject.code}</b>", body_style),
            Paragraph(t.task_type, body_style),
            Paragraph(f"{t.duration_hours} hrs", body_style),
            Paragraph(notes, body_style),
            Paragraph(status_html, body_style)
        ])

    task_table = Table(task_data, colWidths=[1.1*inch, 0.9*inch, 0.8*inch, 0.7*inch, 3.0*inch, 0.8*inch])
    task_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002B5B')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(task_table)

    story.append(Spacer(1, 15))
    sig_data = [
        [
            Paragraph("____________________________<br/><b>Student Signature</b>", body_style),
            Paragraph(f"Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M')}<br/>DIET Academic Planner", body_style),
            Paragraph("____________________________<br/><b>Faculty Mentor / Advisor</b>", body_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[2.4*inch, 2.4*inch, 2.4*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()

