from pydantic import BaseModel


class PingOut(BaseModel):
    ok: bool
    echo: str
