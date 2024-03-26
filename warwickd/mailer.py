import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

class mailer:

    def __init__(self, config, subject, message):
        self.config = config

        # Email content
        mail_content = "<html><body>" + message + "</body></html>"

        # Add email headers
        message = MIMEText(mail_content, "html")
        message["From"] = (
            self.config["mailer"]["from_name"]
            + " <"
            + self.config["mailer"]["from_address"]
            + ">"
        )
        message["To"] = "<" + self.config["mailer"]["to_address"] + ">"
        message["Subject"] = (
            self.config["mailer"]["subject"]
            + " "
            + subject
            + " - "
            + datetime.now().strftime("%a %H:%M:%S")
        )

        # Contect to SMTP server and send the mail ^_^
        server = smtplib.SMTP(
            self.config["mailer"]["smtp"]["server"]
            + ":"
            + str(self.config["mailer"]["smtp"]["port"])
        )
        server.sendmail(
            self.config["mailer"]["from_address"],
            self.config["mailer"]["to_address"],
            message.as_string(),
        )
        server.quit()

        logger.warning("Email sent for '" + subject + "'")
