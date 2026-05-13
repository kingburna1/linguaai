from uuid import UUID
from app.sockets import sio
from app.sockets.events import (
    EVENT_CALL_START,
    EVENT_CALL_END,
    EVENT_CALL_JOINED,
    EVENT_CALL_ENDED,
    EVENT_OFFER,
    EVENT_ANSWER,
    EVENT_ICE_CANDIDATE,
    EVENT_ERROR,
)
from app.db.session import AsyncSessionLocal
from app.crud.crud_session import crud_session
from app.models.session import SessionMode


def _call_room(session_id: str) -> str:
    return f"call:{session_id}"


# JOIN CALL 

@sio.event
async def call_start(sid, data):
   
    socket_session = await sio.get_session(sid)
    if not socket_session:
        await sio.emit(EVENT_ERROR, {"message": "Not authenticated"}, to=sid)
        return

    user_id    = socket_session.get("user_id")
    session_id = data.get("session_id")

    async with AsyncSessionLocal() as db:
        session = await crud_session.get_by_id(db, UUID(session_id))
        if not session or str(session.user_id) != user_id:
            await sio.emit(EVENT_ERROR, {"message": "Session not found"}, to=sid)
            return
        if session.mode not in [SessionMode.audio, SessionMode.video]:
            await sio.emit(EVENT_ERROR, {
                "message": "Session is not an audio or video call"
            }, to=sid)
            return
        if session.ended_at:
            await sio.emit(EVENT_ERROR, {"message": "Session has ended"}, to=sid)
            return

    room = _call_room(session_id)
    await sio.enter_room(sid, room)

    await sio.emit(EVENT_CALL_JOINED, {
        "session_id": session_id,
        "mode":       session.mode.value,
        "message":    "Call is ready. You can now send your WebRTC offer.",
    }, to=sid)

    print(f"[Socket] Call started: session={session_id} sid={sid}")


# END CALL 

@sio.event
async def call_end(sid, data):
   
    session_id = data.get("session_id")
    if not session_id:
        return

    room = _call_room(session_id)
    await sio.emit(EVENT_CALL_ENDED, {
        "session_id": session_id,
        "message":    "The call has ended.",
    }, room=room)

    await sio.leave_room(sid, room)
    print(f"[Socket] Call ended: session={session_id} sid={sid}")


# WEBRTC SIGNALING 

@sio.event
async def offer(sid, data):
   
    session_id = data.get("session_id")
    sdp        = data.get("sdp")

    if not session_id or not sdp:
        await sio.emit(EVENT_ERROR, {"message": "session_id and sdp are required"}, to=sid)
        return

    room = _call_room(session_id)

   
    await sio.emit(EVENT_ANSWER, {
        "session_id": session_id,
        "sdp":        sdp,  
        "message":    "Offer received. AI call server will respond shortly.",
    }, room=room, skip_sid=sid)

    print(f"[Socket] WebRTC offer received: session={session_id}")


@sio.event
async def answer(sid, data):
   
    session_id = data.get("session_id")
    sdp        = data.get("sdp")

    if session_id and sdp:
        await sio.emit(EVENT_ANSWER, {
            "session_id": session_id,
            "sdp":        sdp,
        }, room=_call_room(session_id), skip_sid=sid)


@sio.event
async def ice_candidate(sid, data):
    """
    Forwards ICE candidates between peers.
    ICE candidates are network path options WebRTC uses to
    find the best route between the browser and the AI server.

    Frontend:
        pc.onicecandidate = (e) => {
            if (e.candidate) {
                socket.emit("ice_candidate", {
                    session_id: "uuid",
                    candidate: e.candidate
                })
            }
        }
    """
    session_id = data.get("session_id")
    candidate  = data.get("candidate")

    if session_id and candidate:
        await sio.emit(EVENT_ICE_CANDIDATE, {
            "session_id": session_id,
            "candidate":  candidate,
        }, room=_call_room(session_id), skip_sid=sid)