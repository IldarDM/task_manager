from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        if all([settings.smtp_host, settings.smtp_username, settings.smtp_password]):
            self.conf = ConnectionConfig(
                MAIL_USERNAME=settings.smtp_username,
                MAIL_PASSWORD=settings.smtp_password,
                MAIL_FROM=settings.emails_from_email or settings.smtp_username,
                MAIL_PORT=settings.smtp_port,
                MAIL_SERVER=settings.smtp_host,
                MAIL_STARTTLS=True,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )
            self.fastmail = FastMail(self.conf)
            self.enabled = True
        else:
            logger.warning("Email configuration incomplete. Email service disabled.")
            self.enabled = False

    async def send_password_reset_email(
            self,
            email_to: str,
            reset_token: str,
            user_name: Optional[str] = None
    ) -> bool:
        """Send password reset email."""
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send password reset to {email_to}")
            return True

        try:
            reset_url = f"http://localhost:3000/reset-password?token={reset_token}"

            html_content = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {user_name or 'User'},</p>
                <p>You requested a password reset for your TaskFlow account.</p>
                <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
                <p>If you didn't request this, please ignore this email.</p>
                <p>This link will expire in 1 hour.</p>
                <br>
                <p>Best regards,<br>TaskFlow Team</p>
            </body>
            </html>
            """

            message = MessageSchema(
                subject="Password Reset - TaskFlow",
                recipients=[email_to],
                body=html_content,
                subtype=MessageType.html
            )

            await self.fastmail.send_message(message)
            logger.info(f"Password reset email sent to {email_to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {email_to}: {e}")
            return False

    async def send_welcome_email(self, email_to: str, user_name: str) -> bool:
        """Send welcome email to new users."""
        if not self.enabled:
            logger.warning(f"Email service disabled. Would send welcome email to {email_to}")
            return True

        try:
            html_content = f"""
            <html>
            <body>
                <h2>Welcome to TaskFlow!</h2>
                <p>Hello {user_name},</p>
                <p>Welcome to TaskFlow! Your account has been successfully created.</p>
                <p>You can now start organizing your tasks and boosting your productivity.</p>
                <br>
                <p>Best regards,<br>TaskFlow Team</p>
            </body>
            </html>
            """

            message = MessageSchema(
                subject="Welcome to TaskFlow!",
                recipients=[email_to],
                body=html_content,
                subtype=MessageType.html
            )

            await self.fastmail.send_message(message)
            logger.info(f"Welcome email sent to {email_to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {email_to}: {e}")
            return False


# Global email service instance
email_service = EmailService()