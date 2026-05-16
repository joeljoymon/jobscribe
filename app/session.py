import uuid
from fastapi import Request, Response


SESSION_COOKIE_NAME = "jobscribe_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year in seconds


def get_session_id(request: Request) -> str:
    """
    Reads session_id from cookie.
    Returns it if found.
    Returns None if not found — caller must generate one.
    """
    return request.cookies.get(SESSION_COOKIE_NAME)


def set_session_cookie(response: Response, session_id: str):
    """
    Sets the session cookie on the response.
    HttpOnly — JavaScript cannot read it (security).
    SameSite=Lax — protects against CSRF.
    Max age 1 year — persists across browser restarts.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax"
    )


def get_or_create_session_id(request: Request, response: Response) -> str:
    """
    Main function used everywhere.
    If cookie exists → return existing session_id.
    If not → generate new UUID, set cookie, return it.
    """
    session_id = get_session_id(request)
    if not session_id:
        session_id = str(uuid.uuid4())
        set_session_cookie(response, session_id)
    return session_id