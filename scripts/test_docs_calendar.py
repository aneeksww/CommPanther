import sys
from datetime import datetime, timedelta

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from commpanther.errors import AppError
from commpanther.integrations.google_auth import get_google_credentials


HELP_TEXT = """
\\help
Команда:
    python scripts/test_docs_calendar.py

Что делает:
    Создаёт тестовый Google Doc и записывает в него текст.
    Создаёт тестовое событие Google Calendar с двумя напоминаниями.
    Перечитывает оба объекта, чтобы подтвердить, что они реально созданы.
"""


def create_test_doc(credentials):
    docs = build("docs", "v1", credentials=credentials)

    doc = docs.documents().create(
        body={"title": "CommPanther — тестовый документ"},
    ).execute()

    doc_id = doc["documentId"]

    text = (
        "CommPanther — проверка Google Docs API\n"
        "Категория: Срочно\n"
        "Тема: Тестовое письмо\n"
        "Отправитель: test@example.com\n"
        "Краткое содержание: проверка записи в документ.\n"
        "Статус дедлайна: подтверждён\n"
    )

    docs.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {"insertText": {"location": {"index": 1}, "text": text}},
            ],
        },
    ).execute()

    check = docs.documents().get(documentId=doc_id).execute()
    print(f"Документ создан и перечитан: {check['title']}")

    return doc_id, f"https://docs.google.com/document/d/{doc_id}/edit"


def create_test_event(credentials):
    calendar = build("calendar", "v3", credentials=credentials)

    start = (datetime.now().astimezone() + timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0,
    )
    end = start + timedelta(minutes=30)

    event = {
        "summary": "CommPanther — тестовое событие",
        "description": "Проверка Google Calendar API.",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 1440},
            ],
        },
    }

    created = calendar.events().insert(
        calendarId="primary",
        body=event,
    ).execute()

    check = calendar.events().get(
        calendarId="primary",
        eventId=created["id"],
    ).execute()
    print(f"Событие создано и перечитано, статус: {check['status']}")

    return created["id"], created.get("htmlLink", "")


def main():
    print(HELP_TEXT)

    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "help"}:
        return

    try:
        credentials = get_google_credentials(interactive=False)

        doc_id, doc_link = create_test_doc(credentials)
        print(f"doc_id: {doc_id}")
        print(f"Ссылка на документ: {doc_link}")

        event_id, event_link = create_test_event(credentials)
        print(f"event_id: {event_id}")
        print(f"Ссылка на событие: {event_link}")

        print("Открой ссылки под тем же Google-аккаунтом и проверь результат глазами.")

    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        print(f"Ошибка Google API, статус: {status}")
        print(exc)
    except AppError as exc:
        print(f"Ошибка: {exc.user_message}")
        print(f"Код ошибки: {exc.code}")


if __name__ == "__main__":
    main()