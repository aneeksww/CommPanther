import json
from datetime import datetime, timezone

import httpx

from commpanther.errors import AppError
from commpanther.models.analysis import AnalysisResult


SYSTEM_PROMPT_TEMPLATE = """
Ты классификатор входящих писем.

Твоя задача — прочитать письмо и вернуть только один валидный JSON объект.

Не добавляй пояснения.
Не используй markdown.
Не оборачивай ответ в код.

Формат ответа:
{{
  "category": "urgent | important | later | no_action",
  "rationale": "почему выбрана категория",
  "summary": "краткая суть письма на русском",
  "key_details": ["важный факт 1", "важный факт 2"],
  "actions": ["действие 1", "действие 2"],
  "deadline": "ISO 8601 UTC дата или null",
  "deadline_status": "confirmed | unclear | absent"
}}

Правила:
1. Категория должна быть одной из четырёх значений.
2. Если явного дедлайна нет, deadline_status должен быть "absent", а deadline должен быть null.
3. Если дедлайн есть, но он не точный, deadline_status должен быть "unclear".
4. Если дедлайн точный, верни его в ISO 8601 UTC.
5. Ответ должен быть только JSON.

Текущая дата: {today}
"""


class LLMService:
    def __init__(
        self,
        api_url,
        api_key,
        model,
        timeout_seconds=60,
        use_json_format=True,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.use_json_format = use_json_format

    def analyze_email(self, email):
        today = datetime.now(timezone.utc).date().isoformat()

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(today=today).strip()

        user_prompt = (
            f"Тема: {email.subject}\n"
            f"От: {email.sender}\n"
            f"Получено: {email.received_at}\n"
            f"Текст письма:\n{email.body_text}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error = None

        for attempt in range(2):
            raw_answer = self._request(messages)
            cleaned_answer = _strip_code_fences(raw_answer)

            try:
                data = json.loads(cleaned_answer)
                return AnalysisResult.model_validate(data)
            except Exception as exc:
                last_error = exc

                messages.append({"role": "assistant", "content": raw_answer})
                messages.append({
                    "role": "user",
                    "content": "Ответ не прошёл валидацию. Верни только исправленный JSON без пояснений.",
                })

        raise AppError(
            code="LLM_INVALID_JSON",
            user_message="ИИ вернул некорректный результат.",
            retryable=True,
            details={"error": str(last_error)},
        )

    def _request(self, messages):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": messages,
        }

        if self.use_json_format:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = httpx.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise AppError(
                code="LLM_TIMEOUT",
                user_message="ИИ не ответил вовремя.",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="LLM_NETWORK_ERROR",
                user_message="Не удалось подключиться к сервису ИИ.",
                retryable=True,
                details={"error": str(exc)},
            ) from exc

        if response.status_code == 401:
            raise AppError(
                code="LLM_AUTH_ERROR",
                user_message="Неверный ключ доступа к сервису ИИ.",
                retryable=False,
                details={"status": response.status_code},
            )

        if response.status_code == 429:
            raise AppError(
                code="LLM_RATE_LIMIT",
                user_message="Слишком много запросов к сервису ИИ.",
                retryable=True,
                details={"status": response.status_code},
            )

        if response.status_code >= 500:
            raise AppError(
                code="LLM_SERVER_ERROR",
                user_message="Сервис ИИ временно недоступен.",
                retryable=True,
                details={"status": response.status_code},
            )

        if response.status_code != 200:
            raise AppError(
                code="LLM_API_ERROR",
                user_message="Ошибка при обращении к сервису ИИ.",
                retryable=True,
                details={
                    "status": response.status_code,
                    "body_preview": response.text[:200],
                },
            )

        try:
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise AppError(
                code="LLM_BAD_RESPONSE",
                user_message="Сервис ИИ вернул неожиданный формат ответа.",
                retryable=True,
                details={"error": str(exc)},
            ) from exc


def _strip_code_fences(text):
    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines)

    return text.strip()