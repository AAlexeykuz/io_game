import logging
import random
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic_models import RoomListResponse, RoomStatus

# logging
Path("logs").mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/game.log"),
        logging.StreamHandler(),
    ],
)


class Room:
    def __init__(self) -> None:
        pass


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}  # id комнаты -> комната

    def generate_room_id(self, length=4) -> str:
        """Возвращает новый уникальный id комнаты.

        Args:
            length (int, optional): Длина id. Defaults to 4.
        """
        allowed_characters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        while True:
            new_room_id = "".join(
                random.choice(allowed_characters) for _ in range(length)
            )
            if all(room_id != new_room_id for room_id in self._rooms):
                break
        return new_room_id


# app fastapi
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    html_path = Path("client", "index.html")
    return FileResponse(html_path)


@app.get("/rooms", response_model=RoomListResponse)
async def get_rooms():
    # пока что захардкодено
    return {
        "rooms": [
            {
                "id": "ABCD",
                "player_count": 3,
                "status": RoomStatus.LOBBY,
            },
            {
                "id": "GHJK",
                "player_count": 2,
                "status": RoomStatus.PLAYING,
            },
        ],
    }
