import uuid
import os
from pathlib import Path
from typing import Optional

from supabase import create_client, Client
from app.core.config import settings


# Supabase client 
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY,
)

BUCKET = settings.SUPABASE_STORAGE_BUCKET


# UPLOAD 

async def upload_audio(
    file_bytes: bytes,
    filename:   Optional[str] = None,
    folder:     str = "voice_messages",
    content_type: str = "audio/webm",
) -> str:
    
    # Uploads an audio file to Supabase Storage.
    # Returns the public URL of the uploaded file.

   
    if not filename:
        ext      = _ext_from_content_type(content_type)
        filename = f"{uuid.uuid4()}{ext}"

    path = f"{folder}/{filename}"

    supabase.storage.from_(BUCKET).upload(
        path         = path,
        file         = file_bytes,
        file_options = {"content-type": content_type, "upsert": "true"},
    )

    # Get public URL
    response = supabase.storage.from_(BUCKET).get_public_url(path)
    return response


async def upload_audio_file(
    file_path:    str,
    folder:       str = "ai_responses",
    content_type: str = "audio/wav",
) -> str:

    # Uploads an audio file from a local file path.
   
    path_obj  = Path(file_path)
    filename  = f"{uuid.uuid4()}{path_obj.suffix}"
    dest_path = f"{folder}/{filename}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    supabase.storage.from_(BUCKET).upload(
        path         = dest_path,
        file         = file_bytes,
        file_options = {"content-type": content_type, "upsert": "true"},
    )

    response = supabase.storage.from_(BUCKET).get_public_url(dest_path)
    return response


# DOWNLOAD 

async def download_audio(url: str) -> bytes:
    marker = f"/object/public/{BUCKET}/"
    if marker not in url:
        raise ValueError(f"URL does not belong to bucket '{BUCKET}': {url}")

    path = url.split(marker)[-1]
    response = supabase.storage.from_(BUCKET).download(path)
    return response


# DELETE 

async def delete_audio(url: str) -> bool:
    try:
        marker = f"/object/public/{BUCKET}/"
        if marker not in url:
            return False
        path = url.split(marker)[-1]
        supabase.storage.from_(BUCKET).remove([path])
        return True
    except Exception as e:
        print(f"[Storage] Delete failed: {e}")
        return False


# TEMP FILE HELPER 

def save_temp_audio(file_bytes: bytes, suffix: str = ".wav") -> str:
   
    import tempfile
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
        dir=tempfile.gettempdir(),
    )
    tmp.write(file_bytes)
    tmp.close()
    return tmp.name


def delete_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# INTERNAL HELPERS 

def _ext_from_content_type(content_type: str) -> str:
    mapping = {
        "audio/webm":  ".webm",
        "audio/wav":   ".wav",
        "audio/mpeg":  ".mp3",
        "audio/ogg":   ".ogg",
        "audio/mp4":   ".m4a",
        "audio/flac":  ".flac",
    }
    return mapping.get(content_type, ".audio")