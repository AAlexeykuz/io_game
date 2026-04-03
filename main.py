import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from game.game import Game
from game.ids import IDPool

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
logging.info("New Session Started")

# app fastapi
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    """
    Класс, который управляет соединениями вебсокетов и их соединением с игрой
    """

    def __init__(self) -> None:
        self.websockets: dict[int, WebSocket] = {}
        self.game: Game = Game(self.websockets)
        self.game.start_loop()

    async def connect(self, websocket: WebSocket):
        """Соединяет вебсокет и присваивает ему уникальный ID.

        Args:
            websocket (WebSocket): Неприсоединённый вебсокет

        Returns:
            UUID: Уникальный ID этого вебсокета
        """
        await websocket.accept()
        websocket_id = IDPool.new_id()
        self.websockets[websocket_id] = websocket
        self.game.add_player(websocket_id, 0, 0)
        return websocket_id

    def disconnect(self, websocket_id: int) -> None:
        self.game.remove_player(websocket_id)
        del self.websockets[websocket_id]


manager = ConnectionManager()


@app.get("/")
async def root():
    html_path = Path("client", "index.html")
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    websocket_id = await manager.connect(websocket)
    logging.info(f"Client {websocket_id} connected")
    try:
        while True:
            manager.game.handle_client_input(
                await websocket.receive_json(),
                websocket_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket_id)
        logging.info(f"Client {websocket_id} disconnected")
