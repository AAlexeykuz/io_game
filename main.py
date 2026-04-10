import logging
import random
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from game.game import Game
from game.id_pool import IDPool
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
        self.players: dict[int, WebSocket] = {}  # id из id_pool -> Websocket
        self.is_private: bool = True

        self._id_pool = IDPool()
        self._game: Game | None = None

    def get_status(self) -> RoomStatus:
        if self._game:
            return RoomStatus.PLAYING
        return RoomStatus.LOBBY

    def get_info(self) -> dict:
        return {
            "id": self.id,
            "player_count": len(self.players),
            "status": self.get_status(),
        }

    async def connect(self, websocket: WebSocket) -> int:
        await websocket.accept()
        player_id = self._id_pool.get_new_id()
        if self._game:
            self._game.add_player(player_id)
        self.players[player_id] = websocket
        return player_id

    def disconnect(self, player_id: int) -> None:
        if self._game:
            self._game.remove_player(player_id)
        del self.players[player_id]

    async def handle_input(self, player_input: dict, player_id: int) -> None:
        if self._game:
            self._game.handle_client_input(player_input, player_id)
            return
        if "start" in player_input:
            if player_id == list(self.players.keys())[0]:
                self.start_game()
            else:
                await self.players[player_id].send_json(
                    {"alert": "Только хост может начать игру."}
                )

    def start_game(self) -> None:
        self._game: Game = Game(self.players, self._id_pool)
        for player_id in self.players:
            self._game.add_player(player_id)
        self._game.start_loop()


class RoomManager:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}  # id комнаты -> комната

    def _generate_room_id(self, length: int = 4) -> str:
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

    def create_room(self) -> str:
        """Создаёт комнату, возвращает id."""
        room_id = self._generate_room_id()
        self._rooms[room_id] = Room(room_id)
        print("комнаты", self._rooms)
        return room_id

    def remove_room_if_empty(self, room_id: str) -> None:
        room = self.get_room(room_id)
        if room is not None and len(room.players) == 0:
            del self._rooms[room_id]

    def get_rooms_info(self) -> dict:
        return {"rooms": [room.get_info() for room in self._rooms.values()]}

    def get_room(self, room_id: str) -> Room | None:
        if room_id not in self._rooms:
            return None
        return self._rooms[room_id]


# app fastapi
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# room manager
room_manager = RoomManager()


@app.get("/")
async def root():
    html_path = Path("client", "index.html")
    return FileResponse(html_path)


@app.get("/rooms", response_model=RoomListResponse)
async def get_rooms():
    return room_manager.get_rooms_info()


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    favicon_path = Path("static", "favicon.ico")
    return FileResponse(favicon_path)


@app.post("/rooms", status_code=status.HTTP_201_CREATED)
async def create_room() -> dict:
    room_id = room_manager.create_room()
    logging.info(f"Room {room_id} created")
    return {"id": room_id}


@app.websocket("/rooms/{room_id}")
async def join_room(websocket: WebSocket, room_id: str) -> None:
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    player_id = await room.connect(websocket)
    logging.info(f"Client {player_id} joined {room_id}")
    try:
        while True:
            await room.handle_input(await websocket.receive_json(), player_id)
    except WebSocketDisconnect:
        room.disconnect(player_id)
        room_manager.remove_room_if_empty(room_id)
        logging.info(f"Client {player_id} left {room_id}")
