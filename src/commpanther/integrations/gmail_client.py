import base64
import re
from datetime import timezone
from email.utils import parseaddr, parsedate_to_datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from commpanther.errors import AppError
from commpanther.models.email import RawEmail


BODY_LIMIT = 20000


class GmailClient:
    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    def list_message_ids(self, query=None, max_results=20):
        message_ids = []
        page_token = None

        try:
            while len(message_ids) < max_results:
                batch_size = min(max_results - len(message_ids), 100)

                request = self.service.users().messages().list(
                    userId="me",
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token,
                )

                response = request.execute()

                for item in response.get("messages", []):
                    message_ids.append(item["id"])

                page_token = response.get("nextPageToken")

                if not page_token:
                    break

        except HttpError as exc:
            raise _map_gmail_error(exc) from exc

        return message_ids[:max_results]

    def get_email(self, message_id):
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except HttpError as exc:
            raise _map_gmail_error(exc) from exc

        payload = message.get("payload", {})

        subject = _get_header(payload, "subject")
        sender_raw = _get_header(payload, "from")
        date_raw = _get_header(payload, "date")

        sender = parseaddr(sender_raw)[1] or sender_raw
        received_at = _parse_date(date_raw)
        body_text = _extract_body(payload)

        return RawEmail(
            gmail_id=message["id"],
            thread_id=message.get("threadId", message["id"]),
            sender=sender,
            subject=subject,
            received_at=received_at,
            body_text=body_text,
            source_link=f"https://mail.google.com/mail/u/0/#all/{message['id']}",
        )


def _get_header(payload, name):
    for header in payload.get("headers", []):
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")

    return ""


def _parse_date(raw_date):
    if not raw_date:
        return ""

    try:
        parsed = parsedate_to_datetime(raw_date)
    except Exception:
        return raw_date

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).isoformat()


def _extract_body(payload):
    plain_parts = []
    html_parts = []

    _walk_parts(payload, plain_parts, html_parts)

    if plain_parts:
        text = "\n".join(plain_parts)
    elif html_parts:
        text = _strip_html("\n".join(html_parts))
    else:
        text = ""

    return text.strip()[:BODY_LIMIT]


def _walk_parts(part, plain_parts, html_parts):
    mime_type = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data")

    if body_data:
        content_type = part.get("body", {}).get("contentType", "")
        decoded_text = _decode_base64_data(body_data, content_type)

        if mime_type == "text/plain":
            plain_parts.append(decoded_text)
        elif mime_type == "text/html":
            html_parts.append(decoded_text)

    for child in part.get("parts", []):
        _walk_parts(child, plain_parts, html_parts)


def _decode_base64_data(data, content_type):
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded)

    charset = "utf-8"

    if "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip()

    if not charset:
        charset = "utf-8"

    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _strip_html(html_text):
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _map_gmail_error(exc):
    status = getattr(exc.resp, "status", None)

    if status == 401:
        return AppError(
            code="AUTH_EXPIRED",
            user_message="Срок авторизации Google истёк. Выполните вход повторно.",
            retryable=False,
            details={"status": status},
        )

    if status == 403:
        return AppError(
            code="GMAIL_PERMISSION_DENIED",
            user_message="Нет доступа к Gmail API.",
            retryable=False,
            details={"status": status},
        )

    if status == 429:
        return AppError(
            code="GMAIL_RATE_LIMIT",
            user_message="Слишком много запросов к Gmail. Повторите позже.",
            retryable=True,
            details={"status": status},
        )

    return AppError(
        code="GMAIL_API_ERROR",
        user_message="Не удалось получить письма из Gmail.",
        retryable=True,
        details={"status": status},
    )