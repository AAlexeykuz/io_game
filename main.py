import logging
import random
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
    def __init__(self, room_id: str) -> None:
        self.id: str = room_id
        self.status: RoomStatus = RoomStatus.LOBBY

    def get_info(self) -> dict:
        return {"id": self.id, "player_count": 0, "status": self.status}


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}  # id комнаты -> комната

    def generate_room_id(self, length: int = 4) -> str:
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

    def get_rooms_info(self) -> dict:
        return {"rooms": [room.get_info() for room in self._rooms.values()]}


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


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    favicon_path = Path("static", "favicon.ico")
    return FileResponse(favicon_path)


@app.websocket("/game")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    print(f"hello {websocket}")
