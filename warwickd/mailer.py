import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any

from warwickd.config import Config

logger = logging.getLogger(__name__)


class mailer:
    def __init__(self, config: Config):
        self.sender_name = config.mailer.from_name
        self.sender_address = config.mailer.from_address
        self.subject_extra = config.mailer.subject
        self.server = config.mailer.smtp.server
        self.port = config.mailer.smtp.port
        self.recipient_address = config.mailer.to_address

    def send_email(self, subject: str, body: str):
        msg = MIMEMultipart()
        msg["From"] = self.sender_name + " <" + self.sender_address + ">"
        msg["To"] = "<" + self.recipient_address + ">"
        msg["Subject"] = (
            self.subject_extra
            + " "
            + subject
            + " - "
            + datetime.now().strftime("%a %H:%M:%S")
        )
        msg = MIMEText("<html><body>" + body + "</body></html>", "html")

        try:
            server = smtplib.SMTP(host=self.server, port=self.port)
            server.sendmail(
                from_addr=self.sender_address,
                to_addrs=self.recipient_address,
                msg=msg.as_string(),
            )
            server.quit()
            logger.warning(f"Email sent for '{subject}'")
        except Exception as e:
            logger.error(f"Failed to send email. Error: {str(e)}")
