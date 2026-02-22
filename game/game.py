from uuid import UUID

from fastapi import WebSocket


class Player:
    speed: float = 300

    def __init__(self, x: float, y: float) -> None:
        self.x: float = x
        self.y: float = y
        self.vx: float = 0.0  # направление движения по оси X
        self.vy: float = 0.0  # направление движения по оси Y

    def normalize_velocity(self) -> None:
        """Нормализует сохранённую скорость игрока"""
        length = (self.vx**2 + self.vy**2) ** 0.5
        if length != 0:
            self.vx /= length
            self.vy /= length

    def set_velocity(self, vx: float, vy: float) -> None:
        self.vx = vx
        self.vy = vy
        self.normalize_velocity()

    def move(self, delta_time: float) -> None:
        """
        Двигает игрока по установленной ему скорости
        """
        self.x += self.vx * self.speed * delta_time
        self.y += self.vy * self.speed * delta_time


class Game:
    TICK_RATE: float = 20  # 20 раз в секунду обновление состояния

    def __init__(self) -> None:
        self.players: dict[UUID, Player] = {}  # id вебсокета -> Player

    def add_player(self, player_id, x: float, y: float) -> None:
        if player_id not in self.players:
            self.players[player_id] = Player(x, y)

    def remove_player(self, player_id) -> None:
        if player_id in self.players:
            del self.players[player_id]

    def tick(self, delta_time: float) -> None:
        for player in self.players.values():
            player.move(delta_time)

    def _get_client_info(self, player_id) -> dict:
        """Возвращает

        Args:
            player_id (_type_): _description_

        Returns:
            dict: _description_
        """
        # player_id пока не используется, в будущем будем для оптимизации
        return {
            "texture": [
                ["coca.png", player.x, player.y, 50, 50]
                for player in self.players.values()
            ],
        }

    async def broadcast_client_info(
        self, websockets: dict[UUID, WebSocket]
    ) -> None:
        for player_id in self.players:
            if player_id not in websockets:
                continue
            websocket = websockets[player_id]
            await websocket.send_json(self._get_client_info(player_id))

    def handle_client_input(
        self,
        client_input: dict,
        player_id: UUID,
    ) -> None:
        """Обрабатывает любой ввод со стороны клиента.

        Args:
            client_input (str): Ввод клиента
            websocket_id (UUID): ID вебсокета клиента
        """
        if "movement" in client_input:
            self.players[player_id].set_velocity(*client_input["movement"])
