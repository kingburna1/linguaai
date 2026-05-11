from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import settings


conf = ConnectionConfig(
    MAIL_USERNAME     = settings.MAIL_USERNAME,
    MAIL_PASSWORD     = settings.MAIL_PASSWORD,
    MAIL_FROM         = settings.MAIL_FROM,
    MAIL_PORT         = settings.MAIL_PORT,
    MAIL_SERVER       = settings.MAIL_SERVER,
    MAIL_FROM_NAME    = settings.MAIL_FROM_NAME,
    MAIL_STARTTLS     = True,
    MAIL_SSL_TLS      = False,
    USE_CREDENTIALS   = True,
    VALIDATE_CERTS    = True,
)

fm = FastMail(conf)




async def _send(to: EmailStr, subject: str, body: str) -> None:
    message = MessageSchema(
        subject    = subject,
        recipients = [to],
        body       = body,
        subtype    = MessageType.html,
    )
    await fm.send_message(message)




def _base_template(title: str, content: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:32px;
                background:#f9f9f9;border-radius:8px;">
      <h1 style="color:#4F46E5;font-size:24px;margin-bottom:8px;"> LinguaAI</h1>
      <hr style="border:none;border-top:1px solid #e5e5e5;margin-bottom:24px;">
      <h2 style="color:#111;font-size:20px;">{title}</h2>
      {content}
      <hr style="border:none;border-top:1px solid #e5e5e5;margin-top:32px;">
      <p style="color:#999;font-size:12px;">
        If you did not request this email, you can safely ignore it.
      </p>
    </div>
    """


async def send_verification_email(to: EmailStr, full_name: str, token: str) -> None:
  
    verify_url = f"http://localhost:3000/verify-email?token={token}"
    content = f"""
        <p style="color:#444;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#444;">
            Welcome to LinguaAI! Please verify your email address to activate your account.
        </p>
        <a href="{verify_url}"
           style="display:inline-block;background:#4F46E5;color:#fff;padding:12px 28px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0;">
            Verify My Email
        </a>
        <p style="color:#888;font-size:13px;">
            Or copy this link into your browser:<br>
            <a href="{verify_url}" style="color:#4F46E5;">{verify_url}</a>
        </p>
        <p style="color:#888;font-size:13px;">This link expires in <strong>24 hours</strong>.</p>
    """
    await _send(to, "Verify your LinguaAI email", _base_template("Confirm your email", content))


async def send_reset_password_email(to: EmailStr, full_name: str, token: str) -> None:
  
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    content = f"""
        <p style="color:#444;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#444;">
            We received a request to reset your LinguaAI password.
            Click the button below to choose a new password.
        </p>
        <a href="{reset_url}"
           style="display:inline-block;background:#DC2626;color:#fff;padding:12px 28px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0;">
            Reset My Password
        </a>
        <p style="color:#888;font-size:13px;">
            Or copy this link into your browser:<br>
            <a href="{reset_url}" style="color:#DC2626;">{reset_url}</a>
        </p>
        <p style="color:#888;font-size:13px;">
            This link expires in <strong>1 hour</strong>.<br>
            If you did not request a password reset, your account is safe — ignore this email.
        </p>
    """
    await _send(to, "Reset your LinguaAI password", _base_template("Password Reset Request", content))


async def send_password_changed_email(to: EmailStr, full_name: str) -> None:
    content = f"""
        <p style="color:#444;">Hi <strong>{full_name}</strong>,</p>
        <p style="color:#444;">
            Your LinguaAI password was successfully changed.
        </p>
        <p style="color:#444;">
            If you made this change, no action is needed.
        </p>
        <p style="color:#444;">
            If you did <strong>not</strong> make this change, please contact support
            immediately and reset your password.
        </p>
    """
    await _send(to, "Your password has been changed", _base_template("Password Changed", content))


async def send_welcome_email(to: EmailStr, full_name: str) -> None:
  
    content = f"""
        <p style="color:#444;">Hi <strong>{full_name}</strong> </p>
        <p style="color:#444;">
            Your email is verified and your LinguaAI account is ready!
        </p>
        <p style="color:#444;">
            Start your first lesson by opening the app and picking a language.
            Whether you are 2 or 102, we will guide you at your own pace.
        </p>
        <a href="http://localhost:3000/dashboard"
           style="display:inline-block;background:#4F46E5;color:#fff;padding:12px 28px;
                  border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0;">
            Start Learning Now
        </a>
    """
    await _send(to, "Welcome to LinguaAI! ", _base_template("You're all set!", content))