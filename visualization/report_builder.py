"""PDF and HTML report builder for environmental analysis."""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)


class ReportBuilder:
    """Build PDF and HTML reports from analysis results."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor("#1a5f7a"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor("#2c3e50"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SubSection",
                parent=self.styles["Heading3"],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=5,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceBefore=5,
                spaceAfter=5,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="Finding",
                parent=self.styles["Normal"],
                fontSize=10,
                leftIndent=20,
                bulletIndent=10,
            )
        )

    def build_pdf_report(
        self,
        analysis_results: Dict[str, Any],
        insights: Dict[str, Any],
        location: Dict[str, str],
        charts: List[Any] = None,
    ) -> bytes:
        """Build a PDF report from analysis results."""
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        story = []

        # Title
        county = location.get("county", "Unknown")
        state = location.get("state", "")
        title = f"Environmental Analysis Report: {county} County, {state}"
        story.append(Paragraph(title, self.styles["CustomTitle"]))

        # Date
        story.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%B %d, %Y')}",
                self.styles["CustomBody"],
            )
        )
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))
        summary = insights.get("summary", "Analysis complete.")
        story.append(Paragraph(summary, self.styles["CustomBody"]))
        story.append(Spacer(1, 15))

        # Key Findings
        story.append(Paragraph("Key Findings", self.styles["SectionHeader"]))
        findings = insights.get("key_findings", [])
        for finding in findings:
            story.append(Paragraph(f"• {finding}", self.styles["Finding"]))
        story.append(Spacer(1, 15))

        # Patterns Identified
        patterns = insights.get("patterns", [])
        if patterns:
            story.append(Paragraph("Patterns Identified", self.styles["SectionHeader"]))
            for pattern in patterns:
                story.append(Paragraph(f"• {pattern}", self.styles["Finding"]))
            story.append(Spacer(1, 15))

        # Areas of Concern
        concerns = insights.get("concerns", [])
        if concerns:
            story.append(Paragraph("Areas of Concern", self.styles["SectionHeader"]))
            for concern in concerns:
                story.append(Paragraph(f"• {concern}", self.styles["Finding"]))
            story.append(Spacer(1, 15))

        # Recommendations
        story.append(Paragraph("Recommendations", self.styles["SectionHeader"]))
        recommendations = insights.get("recommendations", [])
        for i, rec in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {rec}", self.styles["Finding"]))
        story.append(Spacer(1, 15))

        # Data Summary
        story.append(PageBreak())
        story.append(Paragraph("Data Summary", self.styles["SectionHeader"]))

        # Build summary table
        summary_data = self._build_summary_table(analysis_results)
        if summary_data:
            table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5f7a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8f9fa")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("PADDING", (0, 0), (-1, -1), 8),
                ])
            )
            story.append(table)
        story.append(Spacer(1, 20))

        # Top Violators Table
        if "by_facility" in analysis_results:
            top_violators = analysis_results["by_facility"].get("top_violators", {})
            if top_violators:
                story.append(Paragraph("Top Facilities by Violations", self.styles["SubSection"]))
                violator_data = [["Facility", "Violations"]]
                for facility, count in list(top_violators.items())[:10]:
                    violator_data.append([facility[:40], str(count)])

                table = Table(violator_data, colWidths=[4 * inch, 1.5 * inch])
                table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5f7a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("ALIGN", (1, 0), (1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dee2e6")),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ])
                )
                story.append(table)

        # Context
        context = insights.get("context", "")
        if context:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Context", self.styles["SectionHeader"]))
            story.append(Paragraph(context, self.styles["CustomBody"]))

        # Footer
        story.append(Spacer(1, 30))
        story.append(
            Paragraph(
                "Report generated by ClimateBud Environmental Analysis System",
                self.styles["CustomBody"],
            )
        )

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_summary_table(self, results: Dict[str, Any]) -> List[List[str]]:
        """Build summary statistics table."""
        data = [["Metric", "Value"]]

        if "total_incidents" in results:
            data.append(["Total Incidents", str(results["total_incidents"])])

        if "date_range" in results:
            dr = results["date_range"]
            data.append(["Date Range", f"{dr.get('start', 'N/A')} to {dr.get('end', 'N/A')}"])

        if "by_facility" in results:
            bf = results["by_facility"]
            data.append(["Total Facilities", str(bf.get("total_facilities", "N/A"))])
            data.append(["Repeat Violators", str(bf.get("repeat_violator_count", "N/A"))])

        if "temporal" in results:
            temp = results["temporal"]
            month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            peak = temp.get("peak_month", 0)
            if peak and peak < len(month_names):
                data.append(["Peak Month", month_names[peak]])
            data.append(["Trend", temp.get("trend", "N/A").title()])

        if "severity" in results:
            for severity, count in results["severity"].items():
                data.append([f"{severity.title()} Severity", str(count)])

        return data

    def build_csv_export(
        self,
        violations: pd.DataFrame,
        filename: str = None,
    ) -> bytes:
        """Export violations data to CSV."""
        if violations.empty:
            return b"No data available"

        buffer = io.BytesIO()
        violations.to_csv(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()

    def build_html_report(
        self,
        analysis_results: Dict[str, Any],
        insights: Dict[str, Any],
        location: Dict[str, str],
    ) -> str:
        """Build an HTML report from analysis results."""
        county = location.get("county", "Unknown")
        state = location.get("state", "")

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Environmental Analysis Report - {county} County</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .report-container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a5f7a;
            border-bottom: 3px solid #1a5f7a;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .finding {{
            padding: 10px 15px;
            margin: 5px 0;
            background-color: #fff;
            border-left: 4px solid #1a5f7a;
        }}
        .concern {{
            border-left-color: #e74c3c;
            background-color: #fdf2f2;
        }}
        .recommendation {{
            border-left-color: #27ae60;
            background-color: #f2fdf5;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #1a5f7a;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .date {{
            color: #666;
            font-size: 0.9em;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <h1>Environmental Analysis Report</h1>
        <h2>{county} County, {state}</h2>
        <p class="date">Generated: {datetime.now().strftime('%B %d, %Y')}</p>

        <div class="summary">
            <h3>Executive Summary</h3>
            <p>{insights.get('summary', 'Analysis complete.')}</p>
        </div>

        <h2>Key Findings</h2>
        {''.join(f'<div class="finding">{f}</div>' for f in insights.get('key_findings', []))}

        <h2>Patterns Identified</h2>
        {''.join(f'<div class="finding">{p}</div>' for p in insights.get('patterns', []))}

        <h2>Areas of Concern</h2>
        {''.join(f'<div class="finding concern">{c}</div>' for c in insights.get('concerns', []))}

        <h2>Recommendations</h2>
        {''.join(f'<div class="finding recommendation">{r}</div>' for r in insights.get('recommendations', []))}

        <h2>Data Summary</h2>
        {self._build_html_table(analysis_results)}

        <div class="footer">
            <p>Report generated by ClimateBud Environmental Analysis System</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_html_table(self, results: Dict[str, Any]) -> str:
        """Build HTML summary table."""
        rows = []

        if "total_incidents" in results:
            rows.append(("Total Incidents", results["total_incidents"]))

        if "by_facility" in results:
            bf = results["by_facility"]
            rows.append(("Total Facilities", bf.get("total_facilities", "N/A")))
            rows.append(("Repeat Violators", bf.get("repeat_violator_count", "N/A")))

        if "temporal" in results:
            rows.append(("Trend", results["temporal"].get("trend", "N/A").title()))

        if not rows:
            return "<p>No summary data available.</p>"

        html = "<table><tr><th>Metric</th><th>Value</th></tr>"
        for metric, value in rows:
            html += f"<tr><td>{metric}</td><td>{value}</td></tr>"
        html += "</table>"

        return html
