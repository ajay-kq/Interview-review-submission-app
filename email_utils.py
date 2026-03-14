import smtplib
from email.message import EmailMessage
from pathlib import Path


def default_email_subject(candidate_name, interview_date):
    return f"{candidate_name} - {interview_date} - Interview Assessment Report"


def build_plain_text(review, ratings, note_reply_to="", regards_name=""):
    recommendation_text = (review["recommendation"] or "-").upper()

    lines = [
        "Hello,",
        "",
        "Please find the interview assessment details below.",
        "",
        f"Candidate Name: {review['candidate_name'] or '-'}",
        f"Position: {review['position'] or '-'}",
        f"Interview Date: {review['interview_date'] or '-'}",
        f"Interviewer Name: {review['interviewer_name'] or '-'}",
        f"Recommendation: {recommendation_text}",
        "",
        "Profile Summary:",
        f"{review['profile_summary'] or '-'}",
        "",
        "Technical Evaluation:",
        f"{review['technical_evaluation'] or '-'}",
        "",
        "Observations:",
        f"{review['observations'] or '-'}",
        "",
        "Overall Assessment:",
        f"{review['overall_assessment'] or '-'}",
        "",
        "Selected Skills & Ratings:"
    ]

    if ratings:
        for row in ratings:
            lines.append(f"- {row['skill_label']}: {row['rating'] * 2}/10")
    else:
        lines.append("- No skills selected")

    if note_reply_to:
        lines.extend([
            "",
            f"Note: If need more details information kindly reply to {note_reply_to}."
        ])

    lines.extend([
        "",
        "Regards,",
        regards_name or "-"
    ])

    return "\n".join(lines)


def build_html_body(review, ratings, note_reply_to="", regards_name=""):
    rating_rows = ""
    if ratings:
        for row in ratings:
            rating_rows += f"""
            <tr>
              <td style="padding:8px;border:1px solid #d9dee7;">{row['skill_label']}</td>
              <td style="padding:8px;border:1px solid #d9dee7;">{row['rating'] * 2}/10</td>
            </tr>
            """
    else:
        rating_rows = """
        <tr>
          <td colspan="2" style="padding:8px;border:1px solid #d9dee7;">No skills selected</td>
        </tr>
        """

    note_html = ""
    if note_reply_to:
        note_html = f"""
        <p><b>Note:</b> If need more details information kindly reply to {note_reply_to}.</p>
        """

    recommendation_text = (review["recommendation"] or "-").upper()

    return f"""
    <html>
      <body style="font-family:Arial, sans-serif; color:#222;">
        <p>Hello,</p>
        <p>Please find the interview assessment details below.</p>

        <table style="border-collapse:collapse; margin-bottom:18px;">
          <tr><td style="padding:6px 10px;"><b>Candidate Name</b></td><td style="padding:6px 10px;"><b>{review['candidate_name'] or '-'}</b></td></tr>
          <tr><td style="padding:6px 10px;"><b>Position</b></td><td style="padding:6px 10px;">{review['position'] or '-'}</td></tr>
          <tr><td style="padding:6px 10px;"><b>Interview Date</b></td><td style="padding:6px 10px;">{review['interview_date'] or '-'}</td></tr>
          <tr><td style="padding:6px 10px;"><b>Interviewer Name</b></td><td style="padding:6px 10px;">{review['interviewer_name'] or '-'}</td></tr>
          <tr><td style="padding:6px 10px;"><b>Recommendation</b></td><td style="padding:6px 10px;"><b>{recommendation_text}</b></td></tr>
        </table>

        <p><b>Profile Summary</b></p>
        <p>{review['profile_summary'] or '-'}</p>

        <p><b>Technical Evaluation</b></p>
        <p>{review['technical_evaluation'] or '-'}</p>

        <p><b>Observations</b></p>
        <p>{review['observations'] or '-'}</p>

        <p><b>Overall Assessment</b></p>
        <p>{review['overall_assessment'] or '-'}</p>

        <p><b>Selected Skills & Ratings</b></p>
        <table style="border-collapse:collapse; width:100%; max-width:650px; margin-bottom:16px;">
          <tr style="background:#eef2f7;">
            <th style="text-align:left;padding:8px;border:1px solid #d9dee7;">Skill Area</th>
            <th style="text-align:left;padding:8px;border:1px solid #d9dee7;">Rating</th>
          </tr>
          {rating_rows}
        </table>

        {note_html}

        <p>Regards,<br>{regards_name or '-'}</p>
      </body>
    </html>
    """


def send_review_email(
    smtp_server,
    smtp_port,
    smtp_username,
    smtp_password,
    email_from,
    email_to,
    email_cc,
    email_bcc,
    subject,
    review,
    ratings,
    attachment_path: Path | None,
    note_reply_to="",
    regards_name=""
):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = email_to

        if email_cc:
            msg["Cc"] = email_cc
        if email_bcc:
            msg["Bcc"] = email_bcc

        plain_text = build_plain_text(review, ratings, note_reply_to, regards_name)
        html_body = build_html_body(review, ratings, note_reply_to, regards_name)

        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype="html")

        if attachment_path and attachment_path.exists():
            with open(attachment_path, "rb") as f:
                pdf_data = f.read()

            msg.add_attachment(
                pdf_data,
                maintype="application",
                subtype="pdf",
                filename=attachment_path.name
            )

        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        return True, "Email sent successfully"

    except Exception as exc:
        return False, str(exc)