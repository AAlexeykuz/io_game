import asyncio
import contextlib
import logging
import math
import random
import sys
import time
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect

from game.id_pool import IDPool

MAX_VISIBILITY_RADIUS: float = 1100
MAX_VISIBILITY_RADIUS_SQUARED: float = MAX_VISIBILITY_RADIUS**2


def is_visible(relative_x: float, relative_y: float) -> bool:
    return relative_x**2 + relative_y**2 < MAX_VISIBILITY_RADIUS_SQUARED


def normalize_vector(x: float, y: float) -> tuple[float, float]:
    length = (x**2 + y**2) ** 0.5
    if length != 0:
        x /= length
        y /= length
    return x, y


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

    def shift(self, shift_x: float, shift_y: float) -> None:
        self.x += shift_x
        self.y += shift_y

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
    initial_health: float = 100
    speed: float = 300
    nickname_offset: float = 65
    health_label_offset: float = 90
    shoot_cooldown: float = 0.05

    def __init__(
        self,
        obj_id: int,
        x: float,
        y: float,
        nickname_label_id: int,
        health_label_id: int,
        nickname: str,
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
            x=0,  # x, y = (0,0) т.к. они всё равно будут генерироваться
            y=0,
            angle=0,
            texture_path=texture_path,
            texture_width=100,
            texture_height=100,
            collision_radius=65,
        )  # временно захардкодено

        self.health: float = 0
        self.kill_count: int = 0
        self.last_shot_time: float = 0

        self.vx: float = 0.0
        self.vy: float = 0.0

        self.nick_label_id: int = nickname_label_id
        self.health_label_id: int = health_label_id
        self.nickname: str = nickname

        self.revive(x, y)

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    def set_velocity(self, vx: float, vy: float) -> None:
        normalized_vx, normalized_vy = normalize_vector(vx, vy)
        self.vx = normalized_vx
        self.vy = normalized_vy

    def move(self, delta_time: float) -> None:
        """
        Двигает игрока по установленной ему скорости
        """
        self.x += self.vx * self.speed * delta_time
        self.y += self.vy * self.speed * delta_time

    def revive(self, x: float, y: float) -> None:
        self.health = self.initial_health
        # в будущем будем рандомно генерировать
        self.x = x
        self.y = y
        self.angle = 0


class Game:
    TICK_RATE: float = 30  # сколько раз в секунду обновление состояния

    def __init__(
        self, websockets: dict[int, WebSocket], id_pool: IDPool
    ) -> None:
        self.websockets = websockets  # websockets от комнаты

        self.map_radius: float = (
            math.sqrt(len(websockets)) * 800
        )  # временный хардкод
        self.map_radius_squared: float = self.map_radius**2
        self.victory_kill_count: int = 7
        self.winner: Player | None = None

        # game objects
        self.players: dict[int, Player] = {}  # id вебсокета -> Player
        self.bullets: dict[int, Bullet] = {}  # id пули -> Bullet

        self.id_pool = id_pool
        # переменные для цикла
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def get_leaderboard(self) -> dict[str, int]:
        return {
            player.nickname: player.kill_count
            for player in sorted(
                self.players.values(), key=lambda x: x.kill_count, reverse=True
            )
        }

    def _get_alive_players(self) -> list[Player]:
        return [
            player for player in self.players.values() if not player.is_dead
        ]

    def _make_random_spawnpoint(self) -> tuple[float, float]:
        angle = random.random() * math.pi * 2
        radius = random.random() * self.map_radius
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        return x, y

    def add_player(self, player_id: int, nickname: str) -> None:
        if player_id not in self.players:
            x, y = self._make_random_spawnpoint()
            self.players[player_id] = Player(
                obj_id=player_id,
                nickname_label_id=self.id_pool.get_new_id(),
                health_label_id=self.id_pool.get_new_id(),
                x=x,
                y=y,
                nickname=nickname,
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
            width=17,
            height=17,
            angle=player.get_front_angle(),
            speed=500.0,
            owner_id=player_id,
            max_lifetime=3.0,
            damage=5,
            collision_radius=10,
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
        # пуля может быть уже удалена, если столкнулась с двумя игроками
        if bullet.id in self.bullets:
            del self.bullets[bullet.id]
        if player.is_dead and not self.winner:
            killer_id = bullet.owner_id
            if killer_id in self.players:
                killer = self.players[killer_id]
                killer.kill_count += 1
                killer.health = Player.initial_health
                if killer.kill_count == self.victory_kill_count:
                    self.winner = killer

    def _resolve_bullet_bullet_collision(
        self,
        bullet1: Bullet,
        bullet2: Bullet,
    ) -> None:
        if bullet1.id in self.bullets:
            del self.bullets[bullet1.id]
        if bullet2.id in self.bullets:
            del self.bullets[bullet2.id]

    def _resolve_player_map_collision(
        self, player: Player, center_distance: float
    ) -> None:
        direction_x, direction_y = normalize_vector(-player.x, -player.y)
        # когда эта функция вызывается, подразумевается, что center_distance > self.MAP_RADIUS
        border_distance = center_distance - self.map_radius
        shift_x = direction_x * border_distance
        shift_y = direction_y * border_distance
        player.shift(shift_x, shift_y)

    def _resolve_collisions(self) -> None:
        # пули-игроки
        for bullet in list(self.bullets.values()):
            for player in self._get_alive_players():
                if bullet.owner_id == player.id:
                    continue
                if are_colliding(bullet, player):  # type: ignore
                    self._resolve_bullet_player_collision(bullet, player)
        # пули-пули
        for bullet1 in list(self.bullets.values()):
            for bullet2 in list(self.bullets.values()):
                if bullet1.id == bullet2.id:
                    continue
                if are_colliding(bullet1, bullet2):  # type: ignore
                    print("BULLET-BULLET")
                    self._resolve_bullet_bullet_collision(bullet1, bullet2)
        # пули-карта
        for bullet in list(self.bullets.values()):
            if bullet.x**2 + bullet.y**2 < self.map_radius_squared:
                continue
            del self.bullets[bullet.id]
        # игроки-карта
        for player in self._get_alive_players():
            center_distance = math.dist((player.x, player.y), (0, 0))
            if center_distance < self.map_radius:
                continue
            self._resolve_player_map_collision(player, center_distance)

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
                    player.nick_label_id,
                    player.nickname,
                    relative_x,
                    relative_y + player.nickname_offset,
                ]
            )
            text_objects_to_show.append(
                [
                    player.health_label_id,
                    str(player.health),
                    relative_x,
                    relative_y + player.health_label_offset,
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
        client_info = {
            "texture": self._get_texture_objects_to_show(player.x, player.y),
            "text": self._get_text_objects_to_show(player.x, player.y),
            "map": [self.map_radius, -player.x, -player.y],
        }
        if self.winner:
            client_info["winner"] = self.winner.nickname
        elif player.is_dead:
            client_info["dead"] = True
        return client_info

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

        if "restart" in client_input:
            player.revive(*self._make_random_spawnpoint())
            return

        # in-game actions
        if player.is_dead:
            return
        if "movement" in client_input:
            player.set_velocity(*client_input["movement"])
        if "angle" in client_input:
            player.set_angle(client_input["angle"])
        if (
            "shoot" in client_input
            and time.time() - player.last_shot_time > player.shoot_cooldown
            and not self.winner
        ):
            self.add_bullet(player_id)
            player.last_shot_time = time.time()

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
