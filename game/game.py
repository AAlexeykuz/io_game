import asyncio
import contextlib
import logging
import random
import sys

from fastapi import WebSocket, WebSocketDisconnect

from game.id_pool import IDPool


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
        self.texture = random.choice(["fanta.png", "coca.png", "sprite.png"])

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
    TICK_RATE: float = 30  # сколько раз в секунду обновление состояния

    def __init__(
        self, websockets: dict[int, WebSocket], id_pool: IDPool
    ) -> None:
        # TODO переделать для новой системы комнат
        self.websockets = websockets  # websockets от комнаты
        self.players: dict[int, Player] = {}  # id вебсокета -> Player
        self.id_pool = id_pool
        # переменные для цикла
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def add_player(self, player_id) -> None:
        if player_id not in self.players:
            self.players[player_id] = Player(player_id, 0, 0)

    def remove_player(self, player_id) -> None:
        if player_id in self.players:
            del self.players[player_id]

    def start_loop(self) -> None:
        if self._loop_task is None or self._loop_task.done():
            self._stop_event.clear()
            self._loop_task = asyncio.create_task(self._game_loop())

    async def stop_loop(self) -> None:
        if self._loop_task and not self._loop_task.done():
            self._stop_event.set()
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task

    def _tick(self, delta_time: float) -> None:
        for player in self.players.values():
            player.move(delta_time)

    def _get_client_info(self, player_id: int) -> dict:
        """Возвращает всю визуальную информацию для данного игрока

        Args:
            player_id (int): id игрока

        Returns:
            dict: json с визуальными данными
        """
        player = self.players.get(player_id)
        if not player:
            return {"texture": []}
        # центр камеры - позиция игрока, для которого предназначены данные
        cam_x = player.x
        cam_y = player.y

        relative_objects = []
        for player in self.players.values():
            # вычисление положение объекта, относительно текущего игрока
            rel_x = player.x - cam_x
            rel_y = player.y - cam_y
            relative_objects.append(
                [
                    player.id,
                    player.texture,
                    rel_x,  # относительная координата по x
                    rel_y,  # относительная координата по y
                    player.width,
                    player.height,
                    player.angle,
                ]
            )

        return {"texture": relative_objects}

    async def _broadcast_client_info(
        self, websockets: dict[int, WebSocket]
    ) -> None:
        # list() для создания копии, чтобы он не вызывал ошибку,
        # когда websockets поменяется в случае выхода/захода игрока
        for player_id, websocket in list(websockets.items()):
            with contextlib.suppress(WebSocketDisconnect, RuntimeError):
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

    async def _game_loop(self) -> None:
        """Главный цикл игры"""
        interval = 1.0 / self.TICK_RATE
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
                    self._tick(delta_time)
                    await self._broadcast_client_info(self.websockets)

                # ожидание до следующего раза
                next_time += interval
                sleep_for = next_time - loop.time()
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                else:
                    next_time = loop.time()
        except asyncio.CancelledError:
            pass
        except Exception:
            logging.error(
                "Unexpected exception in a game loop",
                exc_info=sys.exc_info(),
            )


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

        # Смещение двух объектов (для игроков, для неподвижных препятствий второй объект сдвигаться не должен)
        obj1.x += dx / 2
        obj2.x += dx / 2
        obj1.y -= dy / 2
        obj2.y -= dy / 2
