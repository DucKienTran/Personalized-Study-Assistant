import asyncio
from email.message import EmailMessage

import aiosmtplib

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "tranduckien0110@gmail.com"
SMTP_APP_PASSWORD = "vedmpvcsauapilex"

TO_EMAIL = "23000131@hus.edu.vn"


async def main():
    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = TO_EMAIL
    message["Subject"] = "SMTP Test"
    message.set_content("Đây là email test từ aiosmtplib.")

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_APP_PASSWORD,
            start_tls=True,
        )
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Failed to send email:")
        print(repr(e))


if __name__ == "__main__":
    asyncio.run(main())