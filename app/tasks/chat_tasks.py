from uuid import UUID
from app.db.session import AsyncSessionLocal
from app.crud.crud_message import crud_message
from app.services.ai.llm import llm_service
from app.models.message import SenderType

async def process_user_message(session_id: UUID, user_id: UUID, message_id: UUID):
    async with AsyncSessionLocal() as db:
        try:
          
            user_msg = await crud_message.get_by_id(db, message_id)
            if not user_msg:
                print(f"Task Error: Message {message_id} not found.")
                return

           
            history_objs = await crud_message.get_session_messages(db, session_id, limit=5)
            chat_history = [
                {"role": m.sender.value, "content": m.content}
                for m in reversed(history_objs) if m.id != message_id
            ]

            # 3. Call the LLM 
            ai_reply_text = await llm_service.generate_reply(chat_history, user_msg.content)

            # 4. Save the AI's reply to Postgres
            await crud_message.create_text_message(
                db,
                session_id=session_id,
                user_id=user_id,
                sender=SenderType.ai,
                content=ai_reply_text,
            )
            
            
            await db.commit()
            
        except Exception as e:
            print(f"Error in background AI task: {e}")
            await db.rollback()


async def process_voice_message(session_id: UUID, user_id: UUID, message_id: UUID):
    """Temporary voice pipeline: reuse text reply flow until STT/TTS is wired."""
    await process_user_message(session_id=session_id, user_id=user_id, message_id=message_id)