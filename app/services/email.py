import smtplib
from email.mime.text import MIMEText
from typing import Dict

from fastapi import HTTPException

from app.constants import FRONTEND_URL


def send_email(subject: str, msg: MIMEText, sender: str, recipient: str, password: str):
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.zoho.eu", 465) as smtp_server:
            smtp_server.login(sender, password)
            smtp_server.sendmail(sender, recipient, msg.as_string())

    except smtplib.SMTPDataError as e:
        # Handle the SMTPDataError exception
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}") from e
    except Exception as e:
        # Handle any other exceptions that may occur
        raise HTTPException(status_code=500, detail=f"Error sending email: {e}") from e


def generate_practice_mail(patient: Dict, diagnosis: str, overview: str) -> MIMEText:
    html_body = f"""
        <html>
        <body>
            <p>New triage request received. Details:</p>
            <ul>
                <li>Patient Name: {patient["forename"]} {patient["surname"]}</li>
                <li>Patient DOB: {patient["dob"]}</li>
                <li>Patient Gender: {patient["gender"]}</li>
                <li>Patient Email: {patient["email"]}</li>
                <li>AI diagnosis: {diagnosis}</li>
            </ul>
            <p>{overview}</p>
        </body>
        </html>
    """
    return MIMEText(html_body, "html")


def generate_patient_mail(practice: Dict, patient: Dict, instruction: str) -> MIMEText:
    html_body = f"""
        <html>
        <body>
            <p>Dear {patient["forename"]},</p>
            <p>Thank you for completing our online triage form. We greatly appreciate you taking the time to provide us with the necessary information.</p>
            <p>One of our dedicated receptionists will be reaching out to you shortly to assist with scheduling your appointment. They will ensure that you are booked in at a convenient time for you.</p>
            <p>{instruction}</p>
            <p>We look forward to seeing you soon and providing you with exceptional dental care.</p>
            <p>Best regards,</p>
            <p>{practice["practice_name"]}</p>
        </body>
        </html>
    """
    return MIMEText(html_body, "html")


def generate_password_reset_email(user_email: str, reset_token: str):
    reset_link = f"{FRONTEND_URL}landing/login/reset-password/{reset_token}"
    return MIMEText(
        f"""
        <html>
        <body>
            <p>A request to reset your indentr password has been received. If this wasn't you then simply ignore this email.</p>
            <p>If you did request to reset your password then you follow the link below:</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
        </body>
        </html>
        """,
        "html",
    )
