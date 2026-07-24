from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import aiosmtplib

from app.core.config import settings
from app.exceptions import InternalServerError

logger = logging.getLogger(__name__)


class EmailService:
    async def send_verification_email(
        self, to_email: str, full_name: str | None, token: str
    ) -> None:
        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        name = full_name or "user"

        subject = "Account Verification"
        html_content = f"""
        <html>
            <body>
                <p>Hello <strong>{name}</strong>,</p>
                <p>Thank you for registering. Please click the link below to verify your account (valid for 15 minutes):</p>
                <p><a href="{verify_link}">{verify_link}</a></p>
                <p>If you did not request this, please ignore this email.</p>
            </body>
        </html>
        """
        await self._send_email(to_email, subject, html_content)

    async def send_password_reset_email(
        self, to_email: str, full_name: str | None, token: str
    ) -> None:
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        name = full_name or "user"

        subject = "Password Reset Request"
        html_content = f"""
        <html>
            <body>
                <p>Hello <strong>{name}</strong>,</p>
                <p>We received a request to reset your password. Click the link below to set a new password (valid for 15 minutes):</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>If you did not request a password reset, you can safely ignore this email.</p>
            </body>
        </html>
        """
        await self._send_email(to_email, subject, html_content)

    async def _send_email(self, to_email: str, subject: str, html_content: str) -> None:
        message = MIMEMultipart("alternative")
        message["From"] = settings.SMTP_USER
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_APP_PASSWORD,
                start_tls=True,
            )
            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            raise InternalServerError("Failed to send email. Please try again later.")

    # email_service.py — thêm method mới
    async def send_already_registered_email(
        self, to_email: str, full_name: str | None
    ) -> None:
        name = full_name or "user"
        subject = "Registration Attempt"
        html_content = f"""
        <html>
            <body>
                <p>Hello <strong>{name}</strong>,</p>
                <p>Someone just tried to register a new account using this email address, but an account already exists.</p>
                <p>If this was you, you can <a href="{settings.FRONTEND_URL}/login">log in</a> or
                   <a href="{settings.FRONTEND_URL}/forgot-password">reset your password</a> if you forgot it.</p>
                <p>If this wasn't you, you can safely ignore this email.</p>
            </body>
        </html>
        """
        await self._send_email(to_email, subject, html_content)