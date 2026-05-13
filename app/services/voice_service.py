from typing import Optional
from uuid import UUID

from app.services.ai.stt import stt_service
from app.services.ai.tts import tts_service
from app.services.ai.llm import llm_service
from app.storage.supabase_storage import upload_audio, download_audio
from app.db.session import AsyncSessionLocal
from app.crud.crud_message import crud_message
from app.crud.crud_session import crud_session
from app.crud.crud_language import crud_language
from app.crud.crud_progress import crud_progress
from app.models.message import SenderType, MessageType


async def process_voice_message(
    message_id: UUID,
    session_id: UUID,
    user_id:    UUID,
) -> dict:

    async with AsyncSessionLocal() as db:
        try:
            msg = await crud_message.get_by_id(db, message_id)
            if not msg or not msg.audio_url:
                raise ValueError(f"Voice message {message_id} not found or has no audio")

           
            session = await crud_session.get_by_id(db, session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            language = await crud_language.get(db, session.language_id)
            lang_code = language.code if language else "en"
            lang_name = language.name if language else None

           
            audio_bytes = await download_audio(msg.audio_url)

            stt_result  = await stt_service.transcribe_bytes(
                audio_bytes   = audio_bytes,
                language_code = lang_code,
                audio_format  = ".webm",
            )
            transcript = stt_result["text"]

            if not transcript:
                transcript = "[Could not transcribe audio — please try again]"

            
            pronunciation_score = None
            if msg.ai_correction:
                pronunciation_score = await stt_service.score_pronunciation(
                    user_text     = transcript,
                    expected_text = msg.ai_correction,
                )

            
            history_objs = await crud_message.get_session_messages(
                db, session_id, limit=6
            )
            chat_history = [
                {"role": m.sender.value, "content": m.content or m.transcript or ""}
                for m in reversed(history_objs)
                if m.id != message_id
                and (m.content or m.transcript)
            ]

            from app.crud.crud_user import crud_user
            user = await crud_user.get_by_id(db, user_id)
            voice_gender = "female"
            if user and user.profile:
                voice_gender = user.profile.preferred_voice or "female"

            
            ai_text = await llm_service.generate_reply(
                chat_history  = chat_history,
                user_message  = transcript,
                language_name = lang_name,
            )

           
            ai_audio_url = await tts_service.synthesize(
                text          = ai_text,
                language_code = lang_code,
                voice_gender  = voice_gender,
                upload        = True,
            )

            
            ai_msg = await crud_message.create_voice_message(
                db,
                session_id    = session_id,
                user_id       = user_id,
                sender        = SenderType.ai,
                audio_url     = ai_audio_url,
                transcript    = ai_text,
                ai_correction = None,
            )

           
            msg.transcript          = transcript
            msg.pronunciation_score = pronunciation_score
            db.add(msg)

            await db.commit()
            await db.refresh(ai_msg)

            
            progress = await crud_progress.get_by_user_and_language(
                db, user_id, session.language_id
            )
            newly_unlocked = []
            if progress:
                newly_unlocked = await crud_progress.check_and_unlock_achievements(
                    db, progress
                )
                await db.commit()

            return {
                "transcript":          transcript,
                "ai_text":             ai_text,
                "ai_audio_url":        ai_audio_url,
                "pronunciation_score": pronunciation_score,
                "language":            lang_code,
                "ai_message_id":       str(ai_msg.id),
                "newly_unlocked":      [a.title for a in newly_unlocked],
            }

        except Exception as e:
            await db.rollback()
            print(f"[VoiceService] Error: {e}")
            raise


async def upload_voice_message(
    audio_bytes:  bytes,
    content_type: str = "audio/webm",
) -> str:
    url = await upload_audio(
        file_bytes   = audio_bytes,
        folder       = "voice_messages",
        content_type = content_type,
    )
    return url