from dataclasses import dataclass


@dataclass(frozen=True)
class RawEmail:
    gmail_id: str
    thread_id: str
    sender: str
    subject: str
    received_at: str
    body_text: str
    source_link: str