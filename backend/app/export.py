"""
Data export module for People Counter.
Supports CSV, Excel, and PDF formats.
"""

import io
from datetime import datetime
from typing import List

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt


def export_to_csv(events: List[dict]) -> bytes:
    """
    Export events to CSV format.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        CSV file as bytes
    """
    df = pd.DataFrame(events)
    
    # Convert timestamp to readable format
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create CSV in memory
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8')
    return output.getvalue().encode('utf-8')


def export_to_excel(events: List[dict], stats: dict = None) -> bytes:
    """
    Export events to Excel format with optional statistics.
    
    Args:
        events: List of event dictionaries
        stats: Optional statistics dictionary
        
    Returns:
        Excel file as bytes
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Events sheet
        df_events = pd.DataFrame(events)
        if 'timestamp' in df_events.columns:
            df_events['timestamp'] = pd.to_datetime(df_events['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        df_events.to_excel(writer, sheet_name='Events', index=False)
        
        # Statistics sheet
        if stats:
            df_stats = pd.DataFrame([stats])
            df_stats.to_excel(writer, sheet_name='Statistics', index=False)
    
    output.seek(0)
    return output.getvalue()


def export_to_pdf(
    events: List[dict],
    stats: dict,
    hourly_stats: List[dict] = None,
    title: str = "People Counter Report"
) -> bytes:
    """
    Export events and statistics to PDF format with charts.
    
    Args:
        events: List of event dictionaries
        stats: Statistics dictionary
        hourly_stats: Optional hourly statistics for chart
        title: Report title
        
    Returns:
        PDF file as bytes
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Date and time
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elements.append(Paragraph(f"<b>Generated:</b> {date_str}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Statistics table
    elements.append(Paragraph("<b>Statistics Summary</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    stats_data = [
        ['Metric', 'Value'],
        ['Total IN', str(stats.get('in_count', 0))],
        ['Total OUT', str(stats.get('out_count', 0))],
        ['Net Flow', str(stats.get('in_count', 0) - stats.get('out_count', 0))],
        ['Total Events', str(len(events))],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299E1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Hourly chart (if data provided)
    if hourly_stats and len(hourly_stats) > 0:
        elements.append(Paragraph("<b>Hourly Activity Chart</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Create chart
        fig, ax = plt.subplots(figsize=(8, 4))
        hours = [h['hour'] for h in hourly_stats]
        in_counts = [h.get('IN', 0) for h in hourly_stats]
        out_counts = [h.get('OUT', 0) for h in hourly_stats]
        
        x = range(len(hours))
        width = 0.35
        
        ax.bar([i - width/2 for i in x], in_counts, width, label='IN', color='#48BB78')
        ax.bar([i + width/2 for i in x], out_counts, width, label='OUT', color='#F56565')
        
        ax.set_xlabel('Hour')
        ax.set_ylabel('Count')
        ax.set_title('Hourly Activity')
        ax.set_xticks(x)
        ax.set_xticklabels([f"{h}:00" for h in hours], rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Save chart to bytes
        chart_buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(chart_buffer, format='png', dpi=150)
        chart_buffer.seek(0)
        plt.close()
        
        # Add chart to PDF
        from reportlab.platypus import Image as RLImage
        chart_img = RLImage(chart_buffer, width=6*inch, height=3*inch)
        elements.append(chart_img)
        elements.append(Spacer(1, 0.4*inch))
    
    # Recent events table
    elements.append(Paragraph("<b>Recent Events</b>", styles['Heading2']))
    elements.append(Spacer(1, 0.1*inch))
    
    # Limit to last 20 events
    recent_events = events[:20] if len(events) > 20 else events
    
    events_data = [['Timestamp', 'Track ID', 'Direction']]
    for event in recent_events:
        timestamp = event.get('timestamp', '')
        if isinstance(timestamp, datetime):
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        events_data.append([
            str(timestamp),
            str(event.get('track_id', '')),
            str(event.get('direction', ''))
        ])
    
    events_table = Table(events_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    events_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299E1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(events_table)
    
    # Build PDF
    doc.build(elements)
    output.seek(0)
    return output.getvalue()
