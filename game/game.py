import asyncio
import contextlib
import logging
import math
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
        angle: float,
        width: float,
        height: float,
    ) -> None:
        self.id: int = obj_id
        self.x: float = x  # игровые единицы
        self.y: float = y  # игровые единицы
        self.angle: float = angle  # радианы
        self.width: float = width
        self.height: float = height

    def set_angle(self, angle: float) -> None:
        self.angle = angle

    def get_bounds(self) -> tuple[float, float, float, float]:
        left = self.x - self.width / 2
        rigth = self.x + self.width / 2
        top = self.y + self.height / 2
        bottom = self.y - self.height / 2
        return left, rigth, top, bottom


class TextureObject(GameObject):
    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        angle: float,
        texture_path: str,
        width: float,
        height: float,
    ) -> None:
        super().__init__(obj_id, x, y, angle, width, height)
        self.texture_path = texture_path


class Bullet(TextureObject):
    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        angle: float,
        width: float,
        height: float,
        speed: float,  # скорость пули
        owner_id: int,  # id игрока, отправившего пулю
        max_lifetime: float,  # секунд до автоудаления
    ) -> None:
        super().__init__(
            obj_id,
            x,
            y,
            angle,
            "mentos.png",
            width,
            height,
        )
        self.speed = speed
        self.owner_id = owner_id
        self.max_lifetime = max_lifetime  # это тоже
        self.age = 0.0  # Это не нужно, удалить.

    def update(
        self, delta_time: float
    ) -> None:  # Обновление позиции и возраста пули
        self.x += self.speed * math.cos(self.angle) * delta_time
        self.y += self.speed * math.sin(self.angle) * delta_time
        self.age += delta_time

    def check_age(self) -> bool:  # проверка возраста пули
        return self.age >= self.max_lifetime

    # пока не используется
    def if_out_of_map(
        self, world_width: float, world_height: float
    ) -> bool:  # проверка, что пуля не выходит за карту
        left, right, top, bottom = self.get_bounds()
        return (
            right < 0 or left > world_width or bottom < 0 or top > world_height
        )


class Player(TextureObject):
    speed: float = 300

    def __init__(self, obj_id: int, x: float, y: float) -> None:
        texture_path = random.choice(["fanta.png", "coca.png", "sprite.png"])
        super().__init__(
            obj_id,
            x,
            y,
            0,
            texture_path,
            50,
            150,
        )  # временно захардкодено

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
    """WORLD_WIDTH =   # ширина игравого поля
    WORLD_HEIGHT =   # высота игрового поля"""

    def __init__(
        self, websockets: dict[int, WebSocket], id_pool: IDPool
    ) -> None:
        self.websockets = websockets  # websockets от комнаты
        self.players: dict[int, Player] = {}  # id вебсокета -> Player
        self.bullets: dict[int, Bullet] = {}  # id пули -> Bullet
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

    def add_bullet(self, player_id: int, angle: float) -> None:
        player = self.players[player_id]
        bullet_id = self.id_pool.get_new_id()
        bullet = Bullet(
            obj_id=bullet_id,
            x=player.x,
            y=player.y,
            width=20,
            height=20,
            angle=angle,
            speed=300.0,
            owner_id=player_id,
            max_lifetime=3.0,
        )
        self.bullets[bullet_id] = bullet

    def remove_bullets(
        self, delta_time: float
    ) -> None:  # удаление пули из списка
        delete_bullets = []
        for bullet_id, bullet in self.bullets.items():
            bullet.update(delta_time)
            if bullet.check_age():  # позже добавить bullet.if_out_of_map(self.WORLD_WIDTH, self.WORLD_HEIGHT)
                delete_bullets.append(bullet_id)
        for del_bullet in delete_bullets:
            del self.bullets[del_bullet]

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
        self.remove_bullets(delta_time)

    def _get_texture_objects(self) -> list[TextureObject]:
        return list((self.players | self.bullets).values())

    def _get_client_info(self, player_id: int) -> dict:
        """Возвращает всю визуальную информацию для данного игрока

        Args:
            player_id (int): id игрока

        Returns:
            dict: json с визуальными данными
        """
        player = self.players[player_id]
        # центр камеры - позиция игрока, для которого предназначены данные
        camera_x = player.x
        camera_y = player.y

        texture_objects_to_show = []

        for texture_object in self._get_texture_objects():
            # вычисление положение объекта, относительно текущего игрока
            relative_x = texture_object.x - camera_x
            relative_y = texture_object.y - camera_y
            texture_objects_to_show.append(
                [
                    texture_object.id,
                    texture_object.texture_path,
                    relative_x,  # относительная координата по x
                    relative_y,  # относительная координата по y
                    texture_object.width,
                    texture_object.height,
                    texture_object.angle,
                ]
            )

        return {"texture": texture_objects_to_show}

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
        if "shoot" in client_input:
            self.add_bullet(player_id, client_input["shoot"])

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
