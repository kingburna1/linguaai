
EVENT_CONNECT          = "connect"
EVENT_DISCONNECT       = "disconnect"
EVENT_ERROR            = "error"


EVENT_JOIN_SESSION     = "join_session"      # client → server: join a chat room
EVENT_LEAVE_SESSION    = "leave_session"     # client → server: leave a chat room
EVENT_SEND_MESSAGE     = "send_message"      # client → server: user sends text
EVENT_NEW_MESSAGE      = "new_message"       # server → client: new message arrived
EVENT_AI_TYPING        = "ai_typing"         # server → client: AI is generating reply
EVENT_AI_REPLY         = "ai_reply"          # server → client: AI reply ready
EVENT_MESSAGE_READ     = "message_read"      # client → server: mark message as read
EVENT_TYPING           = "typing"            # client → server: user is typing

#  VOICE 
EVENT_VOICE_MESSAGE    = "voice_message"     # client → server: voice message sent
EVENT_VOICE_REPLY      = "voice_reply"       # server → client: AI voice reply ready
EVENT_TRANSCRIPTION    = "transcription"     # server → client: STT result ready

#  CALLS 
EVENT_CALL_START       = "call_start"        # client → server: start audio/video call
EVENT_CALL_END         = "call_end"          # client → server: end the call
EVENT_CALL_JOINED      = "call_joined"       # server → client: call is ready
EVENT_CALL_ENDED       = "call_ended"        # server → client: call has ended

# WebRTC signaling
EVENT_OFFER            = "offer"             # client → server: WebRTC offer SDP
EVENT_ANSWER           = "answer"            # server → client: WebRTC answer SDP
EVENT_ICE_CANDIDATE    = "ice_candidate"     # both directions: ICE candidates

#  PROGRESS 
EVENT_ACHIEVEMENT      = "achievement"       # server → client: achievement unlocked
EVENT_XP_UPDATE        = "xp_update"        # server → client: XP changed

#  SYSTEM
EVENT_NOTIFICATION     = "notification"      # server → client: general notification