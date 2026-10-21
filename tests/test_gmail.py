import pytest
from app.config import settings
from app.services.gmail_service import GmailService


def test_gmail_oauth_url_generation():
    service = GmailService()
    settings.GOOGLE_CLIENT_ID = "fake-client-id"
    settings.GOOGLE_CLIENT_SECRET = "fake-client-secret"
    settings.GOOGLE_REDIRECT_URI = "https://app.example.com/oauth/google/callback"

    url = service.generate_auth_url(user_id=123456789)
    assert "accounts.google.com/o/oauth2/v2/auth" in url
    assert "client_id=fake-client-id" in url
    assert "state=123456789" in url
    assert "gmail.readonly" in url
    assert "gmail.compose" in url


def test_gmail_message_decoding_untrusted_delimiters():
    service = GmailService()
    fake_msg_payload = {
        "id": "msg_001",
        "threadId": "thread_001",
        "snippet": "Meeting tomorrow at 10am",
        "payload": {
            "headers": [
                {"name": "From", "value": "recruiter@company.com"},
                {"name": "Subject", "value": "Interview Next Steps"},
                {"name": "Date", "value": "Wed, 21 Oct 2026 10:00:00 GMT"},
            ],
            "body": {},
        },
    }

    decoded = service._decode_message(fake_msg_payload)
    assert decoded["id"] == "msg_001"
    assert decoded["from"] == "recruiter@company.com"
    assert decoded["subject"] == "Interview Next Steps"
    # Verify untrusted delimiters are attached
    assert "<<<UNTRUSTED_EMAIL_CONTENT>>>" in decoded["body"]
    assert "<<<END_UNTRUSTED_EMAIL_CONTENT>>>" in decoded["body"]


def test_send_email_not_implemented():
    service = GmailService()
    # Sending email should NEVER exist as an enabled method
    assert not hasattr(service, "send_email")
    assert not hasattr(service, "send_message")
