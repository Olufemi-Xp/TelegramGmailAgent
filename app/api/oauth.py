from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from app.logging_config import get_logger
from app.services.gmail_service import gmail_service

logger = get_logger(__name__)
router = APIRouter(prefix="/oauth", tags=["OAuth"])


@router.get("/google/callback", response_class=HTMLResponse)
async def google_oauth_callback(
    code: str = Query(..., description="Google authorization code"),
    state: str = Query(..., description="Telegram user ID state"),
):
    """Handles OAuth 2.0 callback redirect from Google Cloud."""
    try:
        user_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter. Missing user identifier.")

    try:
        await gmail_service.exchange_code_for_tokens(user_id=user_id, code=code)
    except Exception as e:
        logger.error(f"OAuth exchange failed for user {user_id}: {e}", exc_info=True)
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: system-ui, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: #e53e3e;">Authentication Failed</h2>
                    <p>{str(e)}</p>
                    <p>Please return to Telegram and try running <code>/gmail</code> again.</p>
                </body>
            </html>
            """,
            status_code=500,
        )

    return HTMLResponse(
        content="""
        <html>
            <body style="font-family: system-ui, sans-serif; text-align: center; padding: 50px; background-color: #f7fafc;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #38a169;">✅ Gmail Connected Successfully!</h2>
                    <p style="color: #4a5568; line-height: 1.6;">
                        Your Google account has been authenticated. Tokens have been encrypted at rest.
                    </p>
                    <p style="color: #718096; font-size: 14px;">
                        You can now return to your Telegram chat and use <code>/gmail</code> to view recent emails or draft responses.
                    </p>
                </div>
            </body>
        </html>
        """,
        status_code=200,
    )
