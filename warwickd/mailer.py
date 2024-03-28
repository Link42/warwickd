import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class mailer:
    def __init__(
        self,
        server: str,
        port: int,
        sender_name: str,
        sender_address: str,
        subject_extra: str,
    ):
        self.sender_name = sender_name
        self.sender_address = sender_address
        self.subject_extra = subject_extra
        self.server = server
        self.port = port

    def send_email(self, recipient_address: str, subject: str, body: str):
        msg = MIMEMultipart()
        msg["From"] = self.sender_name + " <" + self.sender_address + ">"
        msg["To"] = "<" + recipient_address + ">"
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
                to_addrs=recipient_address,
                msg=msg.as_string(),
            )
            server.quit()
            logger.warning(f"Email sent for '{subject}'")
        except Exception as e:
            logger.error(f"Failed to send email. Error: {str(e)}")
