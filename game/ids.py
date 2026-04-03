class IDPool:
    _next_new_id: int = 0

    @staticmethod
    def new_id() -> int:
        new_id = IDPool._next_new_id
        IDPool._next_new_id += 1
        return new_id
