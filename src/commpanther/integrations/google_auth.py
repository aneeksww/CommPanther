from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from commpanther.config import paths
from commpanther.errors import AppError


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_client_secret_path() -> Path:
    paths.auth_dir.mkdir(parents=True, exist_ok=True)

    local_secret = paths.auth_dir / "client_secret.json"
    project_secret = Path(__file__).resolve().parents[3] / "secrets" / "client_secret.json"

    if local_secret.exists():
        return local_secret

    if project_secret.exists():
        return project_secret

    raise AppError(
        code="CONFIG_NOT_FOUND",
        user_message="Не найден файл client_secret.json для Google авторизации.",
        details={
            "expected_local_path": str(local_secret),
            "expected_project_path": str(project_secret),
        },
    )


def get_google_credentials(scopes=GOOGLE_SCOPES, interactive=True):
    paths.auth_dir.mkdir(parents=True, exist_ok=True)

    token_path = paths.auth_dir / "token.json"
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as exc:
            token_path.unlink(missing_ok=True)

            if not interactive:
                raise AppError(
                    code="AUTH_EXPIRED",
                    user_message="Срок авторизации Google истёк. Выполните вход повторно.",
                    details={"reason": str(exc)},
                ) from exc
        else:
            token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds

    if not interactive:
        raise AppError(
            code="AUTH_REQUIRED",
            user_message="Нужно подключить Google-аккаунт.",
        )

    secret_path = get_client_secret_path()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(secret_path),
        scopes,
    )

    creds = flow.run_local_server(
        port=0,
        prompt="consent",
        access_type="offline",
    )

    token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds