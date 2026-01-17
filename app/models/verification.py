from datetime import datetime
from sqlmodel import SQLModel, Field

class EmailVerification(SQLModel, table=True):
    __tablename__ = "email_verifications"

    email: str = Field(primary_key=True) # 이메일 하나당 하나의 인증코드만 유지
    code: str
    created_at: datetime = Field(default_factory=datetime.now)