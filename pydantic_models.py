from enum import Enum

from pydantic import BaseModel


class RoomStatus(Enum):
    LOBBY = "Ожидание"
    PLAYING = "В игре"


class RoomInfo(BaseModel):
    id: str  # типа ABCD
    player_count: int
    status: RoomStatus


class RoomListResponse(BaseModel):
    rooms: list[RoomInfo]
