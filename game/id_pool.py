class IDPool:
    """Класс, возвращающий id как целые числа последовательно.
    Каждый новый экземпляр класса - своя система id для каждой комнаты."""

    def __init__(self) -> None:
        self._last_id = -1

    def reset(self) -> None:
        self._last_id = -1

    def get_new_id(self) -> int:
        self._last_id += 1
        return self._last_id
