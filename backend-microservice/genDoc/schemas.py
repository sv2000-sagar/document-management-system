# app/schemas.py

from pydantic import BaseModel, EmailStr

class DocGen(BaseModel):
    client: str
    vendor: str
    amount: int
    line1: str
    line2: str