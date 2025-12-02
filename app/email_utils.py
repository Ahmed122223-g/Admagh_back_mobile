# app/email_utils.py
from fastapi_mail import ConnectionConfig, FastMail
from starlette.config import Config

# Load .env file
config = Config(".env")

# Mail configuration
conf = ConnectionConfig(
    MAIL_USERNAME=config("MAIL_USERNAME"),
    MAIL_PASSWORD=config("MAIL_PASSWORD"),
    MAIL_FROM=config("MAIL_FROM"),
    MAIL_PORT=config("MAIL_PORT", cast=int),
    MAIL_SERVER=config("MAIL_SERVER"),
    MAIL_STARTTLS=config("MAIL_STARTTLS", cast=bool),
    MAIL_SSL_TLS=config("MAIL_SSL_TLS", cast=bool),
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)

from fastapi_mail import MessageSchema, MessageType

async def send_verification_code_email(email: str, name: str, code: str):
    """Sends a standardized email with a verification code to a new user."""
    html = f"""
    <div style="font-family: sans-serif; text-align: center; color: #333;">
        <h2>أهلاً بك يا {name}!</h2>
        <p>شكراً لتسجيلك في تطبيقنا. استخدم الكود التالي لتفعيل حسابك:</p>
        <p style="font-size: 24px; font-weight: bold; letter-spacing: 5px; background: #f2f2f2; padding: 10px 20px; border-radius: 5px; display: inline-block;">
            {code}
        </p>
        <p>هذا الكود صالح لمدة 15 دقيقة.</p>
        <hr>
        <p style="font-size: 0.9em; color: #777;">إذا لم تقم أنت بطلب هذا التسجيل، يرجى تجاهل هذا البريد الإلكتروني.</p>
    </div>
    """

    message = MessageSchema(
        subject="كود تفعيل حسابك",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    await fm.send_message(message)
