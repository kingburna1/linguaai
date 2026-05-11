from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.crud.crud_progress import progress as crud_progress
from app.crud.crud_language import crud_language
from app.core.exceptions import NotFoundException
from app.schemas.progress import ProgressOut, ProgressSummary
from app.schemas.auth import MessageResponse
from app.api.deps import get_current_verified_user
from app.models.user import User

router = APIRouter()


#  GET ALL MY PROGRESS

@router.get("/me", response_model=List[ProgressOut])
async def get_my_progress(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	return await crud_progress.get_user_progress(db, current_user.id)


#  GET MY DASHBOARD PROGRESS

@router.get("/me/dashboard", response_model=List[ProgressOut])
async def get_my_progress_dashboard(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	return await crud_progress.get_user_progress_for_dashboard(db, current_user.id)


#  GET MY PROGRESS SUMMARY

@router.get("/me/summary", response_model=List[ProgressSummary])
async def get_my_progress_summary(
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	summary_rows = await crud_progress.get_user_progress_summary(db, current_user.id)
	summaries: List[ProgressSummary] = []

	for row in summary_rows:
		language = await crud_language.get(db, row.language_id)
		progress = await crud_progress.get_by_user_and_language(
			db, current_user.id, row.language_id
		)

		summaries.append(
			ProgressSummary(
				language_id=row.language_id,
				language_name=language.name if language else None,
				language_flag=language.flag_emoji if language else None,
				total_xp=row.max_xp or 0,
				streak_days=progress.streak_days if progress else 0,
				total_sessions=progress.total_sessions if progress else 0,
			)
		)

	return summaries


#  GET MY PROGRESS IN A LANGUAGE

@router.get("/language/{language_id}", response_model=ProgressOut)
async def get_my_language_progress(
	language_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	language = await crud_language.get(db, language_id)
	if not language:
		raise NotFoundException("Language")

	user_progress = await crud_progress.get_by_user_and_language(
		db, current_user.id, language_id
	)
	if not user_progress:
		raise NotFoundException("Progress")

	return user_progress


#  RESET MY PROGRESS IN A LANGUAGE

@router.patch("/language/{language_id}/reset", response_model=MessageResponse)
async def reset_my_language_progress(
	language_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	language = await crud_language.get(db, language_id)
	if not language:
		raise NotFoundException("Language")

	reset_ok = await crud_progress.reset_user_progress(db, current_user.id, language_id)
	if not reset_ok:
		raise NotFoundException("Progress")

	await db.commit()
	return MessageResponse(message="Progress reset successfully.")


#  DELETE MY PROGRESS IN A LANGUAGE

@router.delete("/language/{language_id}", response_model=MessageResponse)
async def delete_my_language_progress(
	language_id: UUID,
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_verified_user),
):
	language = await crud_language.get(db, language_id)
	if not language:
		raise NotFoundException("Language")

	deleted = await crud_progress.delete_by_user_and_language(
		db, current_user.id, language_id
	)
	if not deleted:
		raise NotFoundException("Progress")

	await db.commit()
	return MessageResponse(message="Progress deleted successfully.")
