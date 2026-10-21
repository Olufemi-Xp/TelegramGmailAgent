from typing import Any, Dict
from bs4 import BeautifulSoup
import httpx
from app.config import settings
from app.logging_config import get_logger
from app.security.url_safety import is_safe_url

logger = get_logger(__name__)


async def fetch_and_extract_url(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Safely extracts text and title from a web URL with SSRF protection."""
    is_safe, reason = is_safe_url(url)
    if not is_safe:
        return {"error": f"URL access blocked: {reason}", "url": url}

    headers = {
        "User-Agent": "Personal-AI-Assistant/1.0 (Mozilla/5.0 compatible; Research Bot)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            resp = await client.get(url, headers=headers)
            
            # Check redirect destination URL safety as well
            if resp.history:
                final_url = str(resp.url)
                final_safe, final_reason = is_safe_url(final_url)
                if not final_safe:
                    return {"error": f"Redirected to unsafe URL: {final_reason}", "url": final_url}

            if resp.status_code != 200:
                return {"error": f"HTTP status {resp.status_code} when fetching page.", "url": url}

            # Check content length limit (max 5MB)
            if len(resp.content) > 5 * 1024 * 1024:
                return {"error": "Page size exceeds maximum download limit (5MB).", "url": url}

            content_type = resp.headers.get("content-type", "").lower()
            if "html" not in content_type and "text" not in content_type:
                return {"error": f"Unsupported content type '{content_type}'.", "url": url}

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove scripts, styles, iframes
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
            text = soup.get_text(separator="\n", strip=True)

            # Delimit untrusted content
            clean_text = f"<<<UNTRUSTED_WEB_CONTENT>>>\n{text[:max_chars]}\n<<<END_UNTRUSTED_WEB_CONTENT>>>"

            return {
                "title": title,
                "url": str(resp.url),
                "content": clean_text,
                "length": len(text),
            }

    except Exception as e:
        logger.warning(f"Failed to fetch URL {url}: {e}")
        return {"error": f"Failed to fetch content from URL: {str(e)}", "url": url}
