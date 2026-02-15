import asyncio

import websockets

# удалить потом из глобального контекста
connected_players = set()


async def handle_connection(websocket) -> None:
    connected_players.add(websocket)
    try:
        async for message in websocket:
            await asyncio.gather(
                *[user.send(message) for user in connected_players]
            )
    finally:
        connected_players.remove(websocket)


async def main() -> None:
    async with websockets.serve(handle_connection, "0.0.0.0", 8080):
        print("Сервер запущен")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
