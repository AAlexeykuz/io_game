import logging

from fastapi import WebSocket, WebSocketDisconnect
import contextlib


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
        self.id: int = obj_id
        self.x: float = x  # игровые единицы
        self.y: float = y  # игровые единицы
        self.width: float = width  # игровые единицы
        self.height: float = height  # игровые единицы
        self.angle: float = angle  # радианы

    def get_bounds(self) -> tuple[float, float, float, float]:
        left = self.x - self.width / 2
        rigth = self.x + self.width / 2
        top = self.y + self.height / 2
        bottom = self.y - self.height / 2
        return left, rigth, top, bottom

    def set_angle(self, angle: float) -> None:
        self.angle = angle


class Player(GameObject):
    speed: float = 300

    def __init__(self, obj_id: int, x: float, y: float) -> None:
        super().__init__(obj_id, x, y, 50, 150, 0)  # временно захардкодено
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
        # player_id пока не используется, в будущем будем
        output = {
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
        return output

    async def broadcast_client_info(
        self, websockets: dict[int, WebSocket]
    ) -> None:
        # list() для создания копии, чтобы он не вызывал ошибку,
        # когда websockets поменяется в случае выхода/захода игрока
        for player_id, websocket in list(websockets.items()):
            with contextlib.suppress(WebSocketDisconnect):
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
        if "angle" in client_input:
            self.players[player_id].set_angle(client_input["angle"])


class CollisionManager:
    def __init__(self) -> None:
        pass

    def rect_collision(self, obj1: GameObject, obj2: GameObject) -> bool:
        l1, r1, t1, b1 = obj1.get_bounds()
        l2, r2, t2, b2 = obj2.get_bounds()
        return not (r1 <= l2 or l1 >= r2 or b1 <= t2 or t1 >= b2)

    def resolve_collision(self, obj1: GameObject, obj2: GameObject) -> None:
        l1, r1, t1, b1 = obj1.get_bounds()
        l2, r2, t2, b2 = obj2.get_bounds()
        # вычисляем пересечение
        overlap_left = r1 - l2
        overlap_right = l1 - r2
        overlap_top = b1 - t2
        overlap_bottom = b2 - t1

        min_overlap = min(
            overlap_left, overlap_right, overlap_top, overlap_bottom
        )

        # Смещение по x
        if min_overlap == (overlap_right, overlap_left):
            if overlap_left < overlap_right:
                dx = -overlap_left
            else:
                dx = overlap_right
            dy = 0
        # Смещение по y
        else:
            if overlap_top < overlap_bottom:
                dy = -overlap_top
            else:
                dy = overlap_bottom
            dx = 0

        # Смещение двух объектов(для игроков, для неподвижных препятствий второй объект сдвигаяться не должен)
        obj1.x += dx / 2
        obj2.x += dx / 2
        obj1.y -= dy / 2
        obj2.y -= dy / 2
