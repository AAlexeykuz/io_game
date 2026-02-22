DTIME = 1/20

class Player:
    speed: float = 5

    def __init__(self, x: float, y: float):
        self.x: float = x #начальная координата x
        self.y: float = y #начальная координата y
        self.vx: float = 0.0 #направление движения по оси X
        self.vy: float = 0.0 #направление движения по оси Y
    
    def normalize_velocity(self) -> None:
        length = (self.vx**2 + self.vy**2)**0.5
        self.vx /= length
        self.vy /= length

    def set_velocity(self, vx: float, vy: float) -> None:
        self.vx = vx
        self.vy = vy
        self.normalize_velocity()

    def move(self, x:float, y: float) -> None:
        self.x += self.vx * self.speed * DTIME
        self.y += self.vy * self.speed * DTIME
