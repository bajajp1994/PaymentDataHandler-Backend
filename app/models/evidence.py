from pydantic import BaseModel
from typing import Optional

class Evidence(BaseModel):
    payment_id: str
    file_name: str
    file_data: bytes
    file_type: str
