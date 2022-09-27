from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ManagedObjects(BaseModel):
    name: str
    id: int
    importance: Optional[str]


class Resource(BaseModel):
    cidr: Optional[str]
    ipVersion: int
    managedObjects: List[ManagedObjects]


class Annotation(BaseModel):
    added: datetime
    author: str
    content: str


class ArborAlert(BaseModel):
    alert_id: int = Field(None, alias='id')
    alert_type: str = Field(None, alias='type')
    is_fast_detected: bool
    importance: str
    classification: str
    device_gid: int
    device_name: str
    direction: str
    start: datetime
    duration: int
    ongoing: bool
    resource: Resource
    threshold: float
    severity_pct: int = 0
    unit: str
    misuseTypes: Optional[List[str]]
    annotations: Optional[List[Annotation]]
    max_impact_bps: int
    max_impact_pps: int
    max_impact_boundary: Optional[str]
    impact_bps_points: Optional[List[int]]
    impact_pps_points: Optional[List[int]]
    impact_recorded: Optional[List[int]]

