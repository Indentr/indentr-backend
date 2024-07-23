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


def send_email_basic(subject: str, msg: str, sender: str, recipient: str, password: str):
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


def generate_practice_mail(patient: Dict, diagnosis: str, appointment_reason: str, primary_color) -> MIMEText:
    patient_name = f"{patient['forename']} {patient['surname']}"
    patient_dob = (
        f"<li style='margin-bottom: 10px; color: #153643; font-size: 16px; line-height: 24px;'><strong>DOB:</strong> {patient['dob']}</li>"
        if "dob" in patient
        else ""
    )
    patient_gender = (
        f"<li style='margin-bottom: 10px; color: #153643; font-size: 16px; line-height: 24px;'><strong>Gender:</strong> {patient['gender']}</li>"
        if "gender" in patient
        else ""
    )

    html_body = f"""
        <html>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                    <td style="padding: 20px 0;">
                        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border: 1px solid #ddd; border-radius: 5px; background-color: #ffffff;">
                            <tr>
                                <td align="center" bgcolor="{primary_color}" style="padding: 20px 0 20px 0; color: #ffffff; font-size: 24px; font-weight: bold; font-family: Arial, sans-serif; border-top-left-radius: 5px; border-top-right-radius: 5px;">
                                    New appointment request
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px 30px 10px 30px;">
                                    <p style="margin: 0; color: #153643; font-size: 18px; font-weight: bold; line-height: 34px;">Patient Details:</p>
                                    <ul style="padding: 0; margin: 10px 0 0 0; list-style-type: none;">
                                        <li style="margin-bottom: 10px; color: #153643; font-size: 16px; line-height: 24px;"><strong>Name:</strong> {patient_name}</li>
                                        {patient_dob}
                                        {patient_gender}
                                        <li style="margin-bottom: 10px; color: #153643; font-size: 16px; line-height: 24px;"><strong>Email:</strong> {patient["email"]}</li>
                                    </ul>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px 30px 20px 30px;">
                                    <p style="margin: 0; color: #153643; font-size: 18px; font-weight: bold; line-height: 34px;">Appointment Reason:</p>
                                    <p style="margin: 10px 0 0 0; color: #153643; font-size: 16px; line-height: 24px;">{appointment_reason}</p>
                                </td>
                            </tr>
                            <tr>
                                <td bgcolor="{primary_color}" style="padding: 30px 30px 30px 30px;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                        <tr>
                                            <td style="color: #ffffff; font-family: Arial, sans-serif; font-size: 14px;" width="75%">
                                                &copy; indentr, All rights reserved.
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
    """
    return MIMEText(html_body, "html")


def generate_patient_mail(practice: Dict, patient: Dict, instruction: str, primary_color: str) -> MIMEText:
    html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
            <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse;">
                <tr>
                    <td align="center" bgcolor="{primary_color}" style="padding: 40px 0 30px 0; color: #ffffff; font-size: 28px; font-weight: bold;">
                        {practice["practice_name"]}
                    </td>
                </tr>
                <tr>
                    <td bgcolor="#ffffff" style="padding: 40px 30px 40px 30px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                            <tr>
                                <td style="color: #153643; font-family: Arial, sans-serif; font-size: 24px;">
                                    <b>Dear {patient["forename"]},</b>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    Thank you for completing our online triage form. We greatly appreciate you taking the time to provide us with the necessary information.
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    One of our dedicated receptionists will be reaching out to you shortly to assist with scheduling your appointment. They will ensure that you are booked in at a convenient time for you.
                                </td>
                            </tr>
                            <tr>
                                <td style="color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    Based on the information you provided we advise:
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 0px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    {instruction}
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 30px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    If you feel like it's an emergency or would like to speak to a member of our team directly, please don't hesitate to email us at <a href="mailto:{practice["primary_email"]}" style="color: #48577d;">{practice["primary_email"]}</a> or call us on {practice["phone"]}.
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    We look forward to seeing you soon and providing you with exceptional dental care.
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 20px 0 30px 0; color: #153643; font-family: Arial, sans-serif; font-size: 16px; line-height: 24px;">
                                    Best regards,
                                    <br>
                                    {practice["practice_name"]}
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td bgcolor="{primary_color}" style="padding: 30px 30px 30px 30px;">
                        <table border="0" cellpadding="0" cellspacing="0" width="100%">
                            <tr>
                                <td style="color: #ffffff; font-family: Arial, sans-serif; font-size: 14px;" width="75%">
                                    &copy; indentr, All rights reserved.
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
    """
    return MIMEText(html_body, "html")


def generate_password_reset_email(user_email: str, reset_token: str):
    reset_link = f"{FRONTEND_URL}login/reset-password/{reset_token}"
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
