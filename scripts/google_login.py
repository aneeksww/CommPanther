import sys

from commpanther.integrations.google_auth import get_google_credentials


HELP_TEXT = """
\\help
Команда:
    python scripts/google_login.py

Что делает:
    Открывает браузер для входа в Google аккаунт.

"""


def main():
    print(HELP_TEXT)

    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "help"}:
        return

    get_google_credentials(interactive=True)

    print("Google авторизация сохранена.")


if __name__ == "__main__":
    main()