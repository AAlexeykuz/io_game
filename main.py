import contextlib
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
from fastapi.responses import FileResponse
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
        self.player_nicknames: dict[int, str] = {}  # id игрока -> ник
        self.is_private: bool = True

        self._id_pool = IDPool()
        self._game: Game | None = None

    def get_status(self) -> RoomStatus:
        if self._game:
            return RoomStatus.PLAYING
        return RoomStatus.LOBBY

    def get_info(self, *params) -> dict:
        info = {
            "id": self.id,
            "player_count": len(self.players),
            "players": [
                self.player_nicknames[player_id]
                for player_id in sorted(self.players.keys())
            ],
            "leaderboard": self._game.get_leaderboard() if self._game else {},
            "status": self.get_status(),
        }
        return {key: value for key, value in info.items() if key in params}

    async def connect(self, websocket: WebSocket, nickname: str) -> int:
        if self.get_status() is RoomStatus.PLAYING:
            raise HTTPException(
                status_code=403,
                detail="Нельзя присоединиться к этой команте в данный момент",
            )
        await websocket.accept()
        player_id = self._id_pool.get_new_id()
        self.players[player_id] = websocket
        self.player_nicknames[player_id] = nickname
        if self._game:
            self._game.add_player(player_id, nickname)
        return player_id

    def disconnect(self, player_id: int) -> None:
        if self._game:
            self._game.remove_player(player_id)
        del self.players[player_id]

    def _is_host(self, player_id: int) -> bool:
        return player_id == list(self.players.keys())[0]

    async def handle_input(self, player_input: dict, player_id: int) -> None:
        if self._game:
            if (
                self._game.winner
                and self._is_host(player_id)
                and "back_to_menu" in player_input
            ):
                await self._end_game()
                return
            self._game.handle_client_input(player_input, player_id)
            return
        if "start" in player_input:
            if self._is_host(player_id):
                await self._start_game()
            else:
                await self.players[player_id].send_json(
                    {
                        "alert": "Только хост может начать игру.",
                    }
                )

    async def _end_game(self) -> None:
        if self._game is not None:
            await self._game.stop_loop()
            del self._game
            self._game = None
        for player_id in self.players:
            with contextlib.suppress(WebSocketDisconnect, KeyError):
                await self.players[player_id].send_json({"game_start": False})

    async def _start_game(self) -> None:
        self._game = Game(self.players, self._id_pool)
        for player_id in self.players:
            self._game.add_player(player_id, self.player_nicknames[player_id])
            with contextlib.suppress(WebSocketDisconnect, KeyError):
                await self.players[player_id].send_json({"game_start": True})
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
        return room_id

    def remove_room_if_empty(self, room_id: str) -> None:
        room = self.get_room(room_id)
        if room is not None and len(room.players) == 0:
            del self._rooms[room_id]

    def get_rooms_info(self) -> dict:
        return {
            "rooms": [
                room.get_info("id", "player_count", "status")
                for room in self._rooms.values()
            ]
        }

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


@app.get("/rooms/{room_id}")
async def get_room_info(room_id: str) -> dict:
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(404)
    return room.get_info("players", "leaderboard")


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
async def join_room(websocket: WebSocket, room_id: str, nickname: str) -> None:
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    player_id = await room.connect(websocket, nickname)
    logging.info(f"Client {player_id} joined {room_id}")
    try:
        while True:
            await room.handle_input(await websocket.receive_json(), player_id)
    except WebSocketDisconnect:
        room.disconnect(player_id)
        room_manager.remove_room_if_empty(room_id)
        logging.info(f"Client {player_id} left {room_id}")
