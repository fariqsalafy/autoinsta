import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession

API = "https://www.googleapis.com/upload/youtube/v3/videos"
TOKEN_PATH = os.environ.get("YT_TOKEN_PATH", "yt_token.json")


def get_session():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(
            TOKEN_PATH,
            ["https://www.googleapis.com/auth/youtube.upload"],
        )
    if not creds or not creds.valid:
        raise Exception("YouTube token invalid or missing. Need OAuth flow first.")
    return AuthorizedSession(creds)


def upload_shorts(file_path: str, title: str = "", description: str = "", tags: list | None = None, privacy: str = "public"):
    session = get_session()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": "24",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    with open(file_path, "rb") as fh:
        media = fh.read()

    headers = {
        "X-Upload-Content-Type": "video/*",
        "Content-Type": "application/json; charset=UTF-8",
    }
    init = session.post(
        API + "?part=snippet,status&uploadType=resumable",
        json=body,
        headers=headers,
        timeout=60,
    )
    upload_url = init.headers.get("Location")
    if not upload_url:
        return {"ok": False, "error": init.text}

    r = session.put(upload_url, data=media, headers={"Content-Type": "video/*"}, timeout=120)
    vid = r.json()
    if "id" not in vid:
        return {"ok": False, "error": r.text}

    video_id = vid["id"]
    return {
        "ok": True,
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
    }
