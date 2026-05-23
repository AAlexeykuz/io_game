import asyncio
import contextlib
import logging
import math
import random
import sys
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

from game.id_pool import IDPool

MAX_VISIBILITY_RADIUS_SQUARED: float = 1000**2


def is_visible(relative_x: float, relative_y: float) -> bool:
    return relative_x**2 + relative_y**2 < MAX_VISIBILITY_RADIUS_SQUARED


class GameObject:
    def __init__(
        self, obj_id: int, x: float, y: float, angle: float, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.id: int = obj_id
        self.x: float = x  # игровые единицы
        self.y: float = y  # игровые единицы
        self.angle: float = angle  # радианы

    def set_angle(self, angle: float) -> None:
        self.angle = angle

    def get_front_angle(self) -> float:
        return (self.angle - math.pi / 2) % (2 * math.pi)


class TextureComponent:
    def __init__(
        self,
        texture_path: str,
        texture_width: float,
        texture_height: float,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.texture_path = texture_path
        self.texture_width = texture_width
        self.texture_height = texture_height


class CircleCollisionComponent:
    def __init__(
        self,
        collision_radius: float,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.collision_radius = collision_radius


def are_colliding(
    object_1: "CircleCollisionObject", object_2: "CircleCollisionObject"
) -> bool:
    distance = math.dist((object_1.x, object_1.y), (object_2.x, object_2.y))
    return distance < object_1.collision_radius + object_2.collision_radius


class Bullet(GameObject, TextureComponent, CircleCollisionComponent):
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
        damage: float,
        collision_radius: float,
    ) -> None:
        super().__init__(
            obj_id=obj_id,
            x=x,
            y=y,
            angle=angle,
            texture_path="mentos.png",
            texture_width=width,
            texture_height=height,
            collision_radius=collision_radius,
        )
        self.damage: float = damage
        self.speed: float = speed
        self.owner_id: int = owner_id
        self.max_lifetime: float = max_lifetime
        self.age: float = 0.0

    def update(self, delta_time: float) -> None:
        """Обновление позиции и возраста пули"""
        self.x += self.speed * math.cos(self.angle) * delta_time
        self.y += self.speed * math.sin(self.angle) * delta_time
        self.age += delta_time

    def check_age(self) -> bool:
        return self.age >= self.max_lifetime


class Player(GameObject, TextureComponent, CircleCollisionComponent):
    speed: float = 300
    text_label_offset: float = 65

    def __init__(
        self, obj_id: int, text_label_id: int, x: float, y: float
    ) -> None:
        texture_path = "Characters/" + random.choice(
            [
                "Adaptant_V1.png",
                "Akiperic_V1.png",
                "Aslanec_V!.png",
                "BrokenCode_V1.png",
                "Fideranec_V1.png",
                "Frik_V1.png",
                "Patchist_V!.png",
                "SLOR_V1.png",
            ]
        )
        super().__init__(
            obj_id=obj_id,
            x=x,
            y=y,
            angle=0,
            texture_path=texture_path,
            texture_width=100,
            texture_height=100,
            collision_radius=65,
        )  # временно захардкодено

        self.health: float = 100

        self.vx: float = 0.0
        self.vy: float = 0.0

        self.text_label_id: int = text_label_id

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

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
    MAP_RADIUS: float = 2000

    def __init__(
        self, websockets: dict[int, WebSocket], id_pool: IDPool
    ) -> None:
        self.websockets = websockets  # websockets от комнаты

        # game objects
        self.players: dict[int, Player] = {}  # id вебсокета -> Player
        self.bullets: dict[int, Bullet] = {}  # id пули -> Bullet

        self.id_pool = id_pool
        # переменные для цикла
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def _get_alive_players(self) -> list[Player]:
        return [
            player for player in self.players.values() if not player.is_dead
        ]

    def add_player(self, player_id) -> None:
        if player_id not in self.players:
            self.players[player_id] = Player(
                obj_id=player_id,
                text_label_id=self.id_pool.get_new_id(),
                x=0,
                y=0,
            )

    def remove_player(self, player_id) -> None:
        if player_id in self.players:
            del self.players[player_id]

    def add_bullet(self, player_id: int) -> None:
        player = self.players[player_id]
        bullet_id = self.id_pool.get_new_id()
        bullet = Bullet(
            obj_id=bullet_id,
            x=player.x,
            y=player.y,
            width=45,
            height=45,
            angle=player.get_front_angle(),
            speed=500.0,
            owner_id=player_id,
            max_lifetime=3.0,
            damage=5,
            collision_radius=5,
        )
        self.bullets[bullet_id] = bullet

    def _remove_timed_out_bullets(self) -> None:  # удаление пули из списка
        for bullet in list(self.bullets.values()):
            if bullet.check_age():
                del self.bullets[bullet.id]

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
        # игроки
        for player in self._get_alive_players():
            player.move(delta_time)
        # жизненный цикл пуль
        for bullet in self.bullets.values():
            bullet.update(delta_time)
        self._remove_timed_out_bullets()
        # коллизии
        self._resolve_collisions()

    def _resolve_bullet_player_collision(
        self, bullet: Bullet, player: Player
    ) -> None:
        player.health -= bullet.damage
        del self.bullets[bullet.id]

    def _resolve_collisions(self) -> None:
        # пули-игроки
        for bullet in list(self.bullets.values()):
            for player in self._get_alive_players():
                if bullet.owner_id == player.id:
                    continue
                if are_colliding(bullet, player):  # type: ignore
                    self._resolve_bullet_player_collision(bullet, player)

    def _get_texture_objects(self) -> list["TextureObject"]:
        return self._get_alive_players() + list(self.bullets.values())  # type: ignore

    def _get_texture_objects_to_show(
        self, camera_x: float, camera_y: float
    ) -> list:
        texture_objects_to_show = []

        for texture_object in self._get_texture_objects():
            relative_x = texture_object.x - camera_x
            relative_y = texture_object.y - camera_y

            if not is_visible(relative_x, relative_y):
                continue

            texture_objects_to_show.append(
                [
                    texture_object.id,
                    texture_object.texture_path,
                    relative_x,
                    relative_y,
                    texture_object.texture_width,
                    texture_object.texture_height,
                    texture_object.angle,
                ]
            )
        return texture_objects_to_show

    def _get_text_objects_to_show(
        self, camera_x: float, camera_y: float
    ) -> list:
        text_objects_to_show = []
        for player in self._get_alive_players():
            relative_x = player.x - camera_x
            relative_y = player.y - camera_y

            if not is_visible(relative_x, relative_y):
                continue

            text_objects_to_show.append(
                [
                    player.text_label_id,
                    str(player.health),
                    relative_x,
                    relative_y + player.text_label_offset,
                ]
            )
        return text_objects_to_show

    def _get_client_info(self, player_id: int) -> dict:
        """Возвращает всю визуальную информацию для данного игрока

        Args:
            player_id (int): id игрока

        Returns:
            dict: json с визуальными данными
        """
        player = self.players[player_id]
        return {
            "texture": self._get_texture_objects_to_show(player.x, player.y),
            "text": self._get_text_objects_to_show(player.x, player.y),
        }

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
        player = self.players[player_id]

        # in-game actions
        if player.is_dead:
            return
        if "movement" in client_input:
            player.set_velocity(*client_input["movement"])
        if "angle" in client_input:
            player.set_angle(client_input["angle"])
        if "shoot" in client_input:
            self.add_bullet(player_id)

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


if TYPE_CHECKING:

    class TextureObject(GameObject, TextureComponent):
        pass

    class CircleCollisionObject(GameObject, CircleCollisionComponent):
        pass
