from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import json

app = FastAPI()
app.mount(
    "/static", StaticFiles(directory="static"), name="static"
)  # Добавить после app = FastAPI()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)


manager = ConnectionManager()


@app.get("/")
async def root():
    html_path = Path("client", "index.html")
    return FileResponse(html_path)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.send_json(
                [
                    ["coca.png", 5, 10],
                    ["coca.png", 10, 15],
                    ["bullet", 3, 7],
                ]
            )
            message = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
