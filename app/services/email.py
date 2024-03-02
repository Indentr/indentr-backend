import smtplib
from email.mime.text import MIMEText
from typing import Dict


def send_email(subject: str, body: str, sender: str, recipient: str, password: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.zoho.eu", 465) as smtp_server:
            smtp_server.login(sender, password)
            smtp_server.sendmail(sender, recipient, msg.as_string())
        print("Email sent successfully")
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed: Check your username/password")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def generate_practice_mail(patient: Dict, diagnosis: str, overview: str):
    msg = f"""
        New triage request recieved. Details:\n

        Patient Name: {patient["forename"]} {patient["surname"]}\n
        Patient DOB: {patient["dob"]}\n
        Patient Gender: {patient["gender"]}\n
        Patient Email: {patient["email"]}\n

        AI diagnosis: {diagnosis}\n
        {overview}
    """
    return msg


def generate_patient_mail(practice: Dict, patient: Dict):
    msg = f"""Dear {patient["forename"]},\n\n"""
    msg += (
        "Thank you for completing our online triage form. We greatly appreciate you taking the time to provide us with the necessary information.\n\n"
    )
    msg += "One of our dedicated receptionists will be reaching out to you shortly to assist with scheduling your appointment. They will ensure that you are booked in at a convenient time for you.\n\n"
    msg += "If you have any urgent concerns or questions in the meantime, please don't hesitate to contact us.\n\n"
    msg += "We look forward to seeing you soon and providing you with exceptional dental care.\n\n"
    msg += "Best regards,\n"
    msg += f"""{practice["practice_name"]}"""
    return msg
