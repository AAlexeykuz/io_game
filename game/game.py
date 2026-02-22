class Player:
    speed: float = 5

    def __init__(self, x: float, y: float) -> None:
        self.x: float = x
        self.y: float = y
        self.vx: float = 0.0  # направление движения по оси X
        self.vy: float = 0.0  # направление движения по оси Y

    def normalize_velocity(self) -> None:
        """Нормализует сохранённую скорость игрока"""
        length = (self.vx**2 + self.vy**2) ** 0.5
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
        self.players: dict[int, Player] = {}

    def add_player(self, player_id, x: float, y: float) -> None:
        if player_id not in self.players:
            self.players[player_id] = Player(x, y)

    def remove_player(self, player_id) -> None:
        if player_id in self.players:
            del self.players[player_id]

    def tick(self, delta_time: float) -> None:
        for player in self.players.values():
            player.move(delta_time)
