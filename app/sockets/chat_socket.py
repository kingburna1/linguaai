from uuid import UUID
from app.sockets import sio
from app.sockets.events import (
    EVENT_JOIN_SESSION,
    EVENT_LEAVE_SESSION,
    EVENT_SEND_MESSAGE,
    EVENT_NEW_MESSAGE,
    EVENT_AI_TYPING,
    EVENT_AI_REPLY,
    EVENT_TYPING,
    EVENT_ERROR,
    EVENT_ACHIEVEMENT,
    EVENT_XP_UPDATE,
)
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.crud.crud_user import crud_user
from app.crud.crud_session import crud_session
from app.crud.crud_message import crud_message
from app.crud.crud_progress import crud_progress
from app.services.ai.llm import llm_service
from app.models.message import SenderType, MessageType


# ── HELPERS ───────────────────────────────────────────────────────────────────

async def _get_user_from_token(token: str):
    """
    Validates the JWT token sent during socket connection.
    Returns the user object or None if invalid.
    """
    user_id = decode_token(token, expected_type="access")
    if not user_id:
        return None
    async with AsyncSessionLocal() as db:
        return await crud_user.get_by_id(db, UUID(user_id))


def _session_room(session_id: str) -> str:
    """
    Each learning session gets its own Socket.IO room.
    Only the user in that session receives its events.
    Room name format: "session:{uuid}"
    """
    return f"session:{session_id}"


# ── CONNECTION ────────────────────────────────────────────────────────────────

@sio.event
async def connect(sid, environ, auth):
    """
    Called when a client connects via Socket.IO.

    The frontend must pass a JWT token in the auth object:
        socket = io("http://localhost:8001", { auth: { token: "Bearer eyJ..." } })

    If the token is missing or invalid, the connection is rejected.
    sid = socket ID — a unique ID for this specific connection.
    """
    token = None
    if auth and isinstance(auth, dict):
        raw = auth.get("token", "")
        # Strip "Bearer " prefix if present
        token = raw.replace("Bearer ", "").strip()

    if not token:
        print(f"[Socket] Connection rejected — no token (sid={sid})")
        return False  # False = reject the connection

    user = await _get_user_from_token(token)
    if not user or not user.is_active:
        print(f"[Socket] Connection rejected — invalid token (sid={sid})")
        return False

    # Store the user's id in the session so we can look it up later
    await sio.save_session(sid, {"user_id": str(user.id), "user_name": user.full_name})
    print(f"[Socket] ✅ Connected: {user.full_name} (sid={sid})")


@sio.event
async def disconnect(sid):
    """Called when a client disconnects (tab closed, network lost etc.)"""
    session = await sio.get_session(sid)
    name = session.get("user_name", "Unknown") if session else "Unknown"
    print(f"[Socket] ❌ Disconnected: {name} (sid={sid})")


# ── JOIN / LEAVE SESSION ROOM ─────────────────────────────────────────────────

@sio.event
async def join_session(sid, data):
    """
    Client joins the socket room for a specific learning session.
    Must be called before sending or receiving any chat messages.

    Frontend calls:
        socket.emit("join_session", { session_id: "uuid" })
    """
    session_id = data.get("session_id")
    if not session_id:
        await sio.emit(EVENT_ERROR, {"message": "session_id is required"}, to=sid)
        return

    socket_session = await sio.get_session(sid)
    user_id = socket_session.get("user_id") if socket_session else None

    # Verify the session belongs to this user
    async with AsyncSessionLocal() as db:
        session = await crud_session.get_by_id(db, UUID(session_id))
        if not session or str(session.user_id) != user_id:
            await sio.emit(EVENT_ERROR, {"message": "Session not found"}, to=sid)
            return

    room = _session_room(session_id)
    await sio.enter_room(sid, room)
    print(f"[Socket] User {user_id} joined room {room}")


@sio.event
async def leave_session(sid, data):
    """Client leaves the session room when navigating away."""
    session_id = data.get("session_id")
    if session_id:
        await sio.leave_room(sid, _session_room(session_id))


# ── TYPING INDICATOR ──────────────────────────────────────────────────────────

@sio.event
async def typing(sid, data):
    """
    Broadcasts a typing indicator to the session room.
    Called while the user is typing — frontend sends this every keystroke.

    Frontend:
        socket.emit("typing", { session_id: "uuid", is_typing: true })
    """
    session_id = data.get("session_id")
    if session_id:
        socket_session = await sio.get_session(sid)
        await sio.emit(
            EVENT_TYPING,
            {"is_typing": data.get("is_typing", True)},
            room=_session_room(session_id),
            skip_sid=sid,  # don't send back to the sender
        )


# ── SEND MESSAGE ──────────────────────────────────────────────────────────────

@sio.event
async def send_message(sid, data):
    """
    Main chat event — user sends a text message via socket.

    Flow:
      1. Validate user and session
      2. Save the user message to the database
      3. Emit the message back to confirm it was received
      4. Emit "ai_typing" indicator to show AI is thinking
      5. Call the LLM to generate a reply
      6. Save the AI reply to the database
      7. Emit "ai_reply" to the session room

    Frontend:
        socket.emit("send_message", {
            session_id: "uuid",
            content: "Hello, teach me French"
        })

    Frontend listens:
        socket.on("new_message", (msg) => { ... })
        socket.on("ai_typing",   ()    => { showTypingIndicator() })
        socket.on("ai_reply",    (msg) => { hideTypingIndicator(); showReply(msg) })
    """
    socket_session = await sio.get_session(sid)
    if not socket_session:
        await sio.emit(EVENT_ERROR, {"message": "Not authenticated"}, to=sid)
        return

    user_id    = socket_session.get("user_id")
    session_id = data.get("session_id")
    content    = (data.get("content") or "").strip()

    if not session_id or not content:
        await sio.emit(EVENT_ERROR, {"message": "session_id and content are required"}, to=sid)
        return

    room = _session_room(session_id)

    async with AsyncSessionLocal() as db:
        try:
            # 1. Validate session
            session = await crud_session.get_by_id(db, UUID(session_id))
            if not session or str(session.user_id) != user_id:
                await sio.emit(EVENT_ERROR, {"message": "Session not found"}, to=sid)
                return
            if session.ended_at:
                await sio.emit(EVENT_ERROR, {"message": "Session has ended"}, to=sid)
                return

            # 2. Save user message
            user_msg = await crud_message.create_text_message(
                db,
                session_id = UUID(session_id),
                user_id    = UUID(user_id),
                sender     = SenderType.user,
                content    = content,
            )
            await db.commit()
            await db.refresh(user_msg)

            # 3. Confirm message received
            await sio.emit(EVENT_NEW_MESSAGE, {
                "id":         str(user_msg.id),
                "sender":     "user",
                "content":    user_msg.content,
                "msg_type":   "text",
                "created_at": user_msg.created_at.isoformat(),
            }, room=room)

            # 4. Show AI typing indicator
            await sio.emit(EVENT_AI_TYPING, {"is_typing": True}, room=room)

            # 5. Fetch chat history for context
            history_objs = await crud_message.get_session_messages(
                db, UUID(session_id), limit=10
            )
            chat_history = [
                {"role": m.sender.value, "content": m.content or ""}
                for m in reversed(history_objs)
                if m.id != user_msg.id and m.content
            ]

            # 6. Get language name for context
            from app.crud.crud_language import crud_language
            from app.services.ai.rag import rag_service

            language      = await crud_language.get(db, session.language_id)
            lang_code     = language.code if language else "en"
            lang_name     = language.name if language else None

            # 7. Use RAG pipeline (retrieves content + generates response)
            rag_result = await rag_service.generate_with_context(
                user_message  = content,
                language_code = lang_code,
                language_name = lang_name or "English",
                chat_history  = chat_history,
            )
            ai_text = rag_result["reply"]

            # 8. Save AI reply
            ai_msg = await crud_message.create_text_message(
                db,
                session_id = UUID(session_id),
                user_id    = UUID(user_id),
                sender     = SenderType.ai,
                content    = ai_text,
            )
            await db.commit()
            await db.refresh(ai_msg)

            # 9. Push AI reply — hide typing indicator + show message
            await sio.emit(EVENT_AI_TYPING, {"is_typing": False}, room=room)
            await sio.emit(EVENT_AI_REPLY, {
                "id":         str(ai_msg.id),
                "sender":     "ai",
                "content":    ai_msg.content,
                "msg_type":   "text",
                "created_at": ai_msg.created_at.isoformat(),
            }, room=room)

            # 10. Check and push any newly unlocked achievements
            progress = await crud_progress.get_by_user_and_language(
                db, UUID(user_id), session.language_id
            )
            if progress:
                newly_unlocked = await crud_progress.check_and_unlock_achievements(
                    db, progress
                )
                await db.commit()
                for achievement in newly_unlocked:
                    await sio.emit(EVENT_ACHIEVEMENT, {
                        "title":      achievement.title,
                        "icon":       achievement.icon,
                        "xp_reward":  achievement.xp_reward,
                    }, to=sid)

        except Exception as e:
            await sio.emit(EVENT_AI_TYPING, {"is_typing": False}, room=room)
            await sio.emit(EVENT_ERROR, {"message": f"AI error: {str(e)}"}, to=sid)
            await db.rollback()
            print(f"[Socket] Error in send_message: {e}")