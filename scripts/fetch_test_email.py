import sys

from commpanther.errors import AppError
from commpanther.integrations.gmail_client import GmailClient
from commpanther.integrations.google_auth import get_google_credentials


HELP_TEXT = """
\\help
Команда:
    python scripts/fetch_test_email.py

Опционально:
    python scripts/fetch_test_email.py --query "newer_than:7d" --max 5
"""


def get_option(name, default):
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def main():
    print(HELP_TEXT)

    query = get_option("--query", "newer_than:7d")
    max_results = int(get_option("--max", "3"))

    try:
        credentials = get_google_credentials(interactive=False)
        client = GmailClient(credentials)

        message_ids = client.list_message_ids(query=query, max_results=max_results)

        if not message_ids:
            print("Письма не найдены.")
            return

        for message_id in message_ids:
            email = client.get_email(message_id)
            print("-" * 80)
            print(f"gmail_id: {email.gmail_id}")
            print(f"subject: {email.subject}")
            print(f"sender: {email.sender}")
            print(f"received_at: {email.received_at}")
            print(f"source_link: {email.source_link}")
            print(f"body_preview: {email.body_text[:200]}")

    except AppError as exc:
        print(f"Ошибка: {exc.user_message}")
        print(f"Код ошибки: {exc.code}")


if __name__ == "__main__":
    main()