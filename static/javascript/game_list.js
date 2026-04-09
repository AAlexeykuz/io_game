let list = document.getElementById("list");

class Room {
    constructor(id, count_player, status) {
        this.id = id;
        this.count_player = count_player;
        this.status = status;
    }

    CreateList(list) {
        let li = document.createElement('li');
        let div = document.createElement('div');
        let span = document.createElement('span');

        span.textContent = `Комната: ${this.id} | Количество игроков: ${this.count_player} | Статус: ${this.status}`;

        div.appendChild(span);
        li.appendChild(div);
        list.appendChild(li);
    }
}


async function fetchRooms() {
    try {
        const response = await fetch('/rooms');
        const data = await response.json();
        
        // Очищаем старый список перед отрисовкой нового
        const listElement = document.getElementById("list");
        listElement.innerHTML = '';

        data.rooms.forEach(roomData => {
            const room = new Room(roomData.id, roomData.player_count, roomData.status);
            room.CreateList(listElement);
        });
    } catch (error) {
        console.error("Ошибка при получении комнат:", error);
    } finally {
        let roomUpdateTimeout = 3000 // милисекунды
        setTimeout(fetchRooms, roomUpdateTimeout);
    }
}

// Запускаем первый раз
fetchRooms();