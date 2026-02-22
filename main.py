import asyncio
import contextlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game.game import Game

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    """
    Класс, который управляет соединениями вебсокетов и их соединением с игрой
    """

    def __init__(self) -> None:
        self.websockets: dict[UUID, WebSocket] = {}
        self.game: Game = Game()
        # переменные для цикла
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.start_loop()

    async def connect(self, websocket: WebSocket) -> UUID:
        """Соединяет вебсокет и присваивает ему уникальный ID.

        Args:
            websocket (WebSocket): Неприсоединённый вебсокет

        Returns:
            UUID: Уникальный ID этого вебсокета
        """
        await websocket.accept()
        websocket_id = uuid4()
        self.websockets[websocket_id] = websocket
        self.game.add_player(websocket_id, 0, 0)
        return websocket_id

    def disconnect(self, websocket_id: UUID) -> None:
        self.game.remove_player(websocket_id)
        del self.websockets[websocket_id]

    async def game_loop(self) -> None:
        interval = 1.0 / self.game.TICK_RATE
        loop = asyncio.get_running_loop()
        next_time = loop.time()
        last_time = next_time
        try:
            while not self._stop_event.is_set():
                # замер времени
                now = loop.time()
                delta_time = now - last_time
                last_time = now

                # просчитывание тика с нужным delta_time
                async with self._lock:
                    self.game.tick(delta_time)
                    await self.game.broadcast_client_info(self.websockets)

                # ожидание до следующего раза
                next_time += interval
                sleep_for = next_time - loop.time()
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                else:
                    next_time = loop.time()
        except asyncio.CancelledError:
            pass

    def start_loop(self) -> None:
        if self._loop_task is None or self._loop_task.done():
            self._stop_event.clear()
            self._loop_task = asyncio.create_task(self.game_loop())

    async def stop_loop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._stop_event.set()
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task


manager = ConnectionManager()


@app.get("/")
async def root():
    html_path = Path("client", "index.html")
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    websocket_id = await manager.connect(websocket)
    try:
        while True:
            manager.game.handle_client_input(
                await websocket.receive_json(),
                websocket_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket_id)
