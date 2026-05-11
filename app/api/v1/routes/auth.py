from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.crud_user import crud_user
from app.core.security import verify_password, decode_token, create_token_pair
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    EmailNotVerifiedException,
    AccountDisabledException,
    InvalidTokenException,
    BadRequestException,
    UserNotFoundException,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.schemas.user import UserOut
from app.services.email_service import (
    send_verification_email,
    send_welcome_email,
    send_reset_password_email,
    send_password_changed_email,
)
from app.api.deps import get_current_user
from app.models.user import User
from uuid import UUID

router = APIRouter()


# ── REGISTER ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
 
    if await crud_user.email_exists(db, data.email):
        raise EmailAlreadyExistsException()

    user = await crud_user.create(db, data)

  
    await db.commit()
    await db.refresh(user)

   
    background_tasks.add_task(
        send_verification_email,
        to        = user.email,
        full_name = user.full_name,
        token     = user.verify_token,
    )

    return MessageResponse(
        message = "Account created! Please check your email to verify your account.",
        success = True,
    )




@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
   
    user = await crud_user.get_by_email(db, data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise InvalidCredentialsException()

   
    if not user.is_active:
        raise AccountDisabledException()

   
    if not user.is_verified:
        raise EmailNotVerifiedException()

   
    return create_token_pair(user.id)




@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    
    user_id = decode_token(data.refresh_token, expected_type="refresh")
    if not user_id:
        raise InvalidTokenException("Refresh token is invalid or expired. Please log in again.")

    user = await crud_user.get_by_id(db, UUID(user_id))
    if not user or not user.is_active:
        raise InvalidTokenException("User not found or account disabled")

    return create_token_pair(user.id)




@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: VerifyEmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
  
    user = await crud_user.get_by_verify_token(db, data.token)
    if not user:
        raise InvalidTokenException("Verification link is invalid or already used")

    await crud_user.verify_email(db, user)

   
    background_tasks.add_task(
        send_welcome_email,
        to        = user.email,
        full_name = user.full_name,
    )

    return MessageResponse(message="Email verified! You can now log in.")




@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    data: ForgotPasswordRequest,  
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await crud_user.get_by_email(db, data.email)

    
    if not user or user.is_verified:
        return MessageResponse(
            message="If this email exists and is unverified, a new link has been sent."
        )

    await crud_user.regenerate_verify_token(db, user)

    background_tasks.add_task(
        send_verification_email,
        to        = user.email,
        full_name = user.full_name,
        token     = user.verify_token,
    )

    return MessageResponse(
        message="If this email exists and is unverified, a new link has been sent."
    )




@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
  
    user = await crud_user.get_by_email(db, data.email)

    if user and user.is_active:
        token = await crud_user.set_reset_token(db, user)
        background_tasks.add_task(
            send_reset_password_email,
            to        = user.email,
            full_name = user.full_name,
            token     = token,
        )

   
    return MessageResponse(
        message="If an account with this email exists, a password reset link has been sent."
    )




@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    
    user = await crud_user.validate_reset_token(db, data.token)
    if not user:
        raise InvalidTokenException("Reset link is invalid or has expired")

    await crud_user.update_password(db, user, data.new_password)

    background_tasks.add_task(
        send_password_changed_email,
        to        = user.email,
        full_name = user.full_name,
    )

    return MessageResponse(message="Password reset successful. You can now log in.")



@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    
    return current_user