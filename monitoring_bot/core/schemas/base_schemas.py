from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Union
from enum import Enum
from asyncio import Queue

# Arbor models


class ManagedObject(BaseModel):
    name: str
    id: int
    importance: Optional[str]


class Resource(BaseModel):
    cidr: Optional[str]
    ipVersion: int
    name: Optional[str]
    managedObjects: List[ManagedObject]


class Annotation(BaseModel):
    added: datetime
    author: str
    content: str


class Importance(Enum):
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class ArborElement(BaseModel):
    id: int
    type: str
    is_fast_detected: bool
    importance: Importance
    classification: str
    start: datetime
    ongoing: bool
    resource: Resource
    severity_pct: Union[int, str]
    misuseTypes: Optional[List[str]]
    # annotations: Optional[List[Annotation]]
    max_impact_bps: int
    max_impact_pps: int
    max_impact_boundary: str


class ClientAlert:
    alert_id: int
    type: str
    is_fast_detected: bool
    importance: str
    time: str
    linux_time: datetime
    ongoing: bool
    ip: str
    managed_object: str
    severity: str
    attack_type: str
    bps: int
    pps: int


# Application models
class ClientElement(BaseModel):
    alerts: List[str]
    api_key: str
    bot: str
    chat_id: int
    filter: str
    label: str
    name: str
    no_alert_bps: int
    no_sound_bps: int
    no_sound_pps: int
    type: str
    url: str


# queue model

class QueueElement(BaseModel):
    type: str
    chat_id: int
    text: str
    counter: int
    message_id: Optional[int]
    telegram_bot_token: str
    nosound: Optional[str]


messages_queue = Queue()


class MessageStatus(Enum):
    SEND = 'send'
    UPDATE = 'update'
    SKIP = 'skip'
