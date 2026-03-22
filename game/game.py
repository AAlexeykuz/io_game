from fastapi import WebSocket


class GameObject:
    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        width: float,
        height: float,
        angle: float,
    ) -> None:
        self.id = obj_id
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.height: float = height
        self.angle: float = angle


class Player(GameObject):
    speed: float = 300

    def __init__(self, obj_id: int, x: float, y: float) -> None:
        super().__init__(obj_id, x, y, 50, 50, 0)  # временно захардкодено
        self.vx: float = 0.0
        self.vy: float = 0.0

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
        self.players: dict[int, Player] = {}  # id вебсокета -> Player

    def add_player(self, player_id, x: float, y: float) -> None:
        if player_id not in self.players:
            self.players[player_id] = Player(player_id, x, y)

    def remove_player(self, player_id) -> None:
        if player_id in self.players:
            del self.players[player_id]

    def tick(self, delta_time: float) -> None:
        for player in self.players.values():
            player.move(delta_time)

    def _get_client_info(self, player_id: int) -> dict:
        """Возвращает всю визуальную информацию для данного игрока

        Args:
            player_id (int): id игрока

        Returns:
            dict: json с визуальными данными
        """
        # player_id пока не используется, в будущем будем для оптимизации
        return {
            "texture": [
                [
                    player.id,
                    "coca.png",
                    player.x,
                    player.y,
                    player.width,
                    player.height,
                    player.angle,
                ]
                for player in self.players.values()
            ],
        }

    async def broadcast_client_info(
        self, websockets: dict[int, WebSocket]
    ) -> None:
        for player_id in self.players:
            if player_id not in websockets:
                continue
            websocket = websockets[player_id]
            await websocket.send_json(self._get_client_info(player_id))

    def handle_client_input(
        self,
        client_input: dict,
        player_id: int,
    ) -> None:
        """Обрабатывает любой ввод со стороны клиента.

        Args:
            client_input (str): Ввод клиента
            player_id (int): ID вебсокета клиента
        """
        if "movement" in client_input:
            self.players[player_id].set_velocity(*client_input["movement"])
