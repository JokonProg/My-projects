from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AlertIn(BaseModel):
    alert_id: int
    ongoing: bool
    managed_object: str
    message_id: Optional[int]
    client_type: str
    client_name: str
    client_label: str
    chat_id: int
    text: str
