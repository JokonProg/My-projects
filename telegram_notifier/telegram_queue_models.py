from pydantic import BaseModel
from typing import Optional


class TelegramQueueElement(BaseModel):
    chat_id: int
    message_id: Optional[int]
    message_text: str
    telegram_bot_api_token: str
    client_id: int
    alert_id: int
    nosound: bool
