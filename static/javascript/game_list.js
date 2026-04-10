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

        span.innerHTML = `Количество игроков: ${this.count_player}<br>Статус: ${this.status}`;
        span.id = `${this.id}`

        li.appendChild(span);
        div.appendChild(li);
        list.appendChild(div);

        div.classList.add('roomList');

        const button = document.createElement('button');
        button.textContent = 'Присоединиться';
        div.appendChild(button);

        if(this.status == 'Ожидание'){
            button.classList.add('enter_true')
        } else {
            button.classList.add('enter_false')
        }
    }
    
}
// Данные для примера!!!!
const room1 = new Room(1, 2, "Ожидание");
const room2 = new Room(4, 3, "В игре");

room2.CreateList(list);
room1.CreateList(list);
room1.CreateList(list);
//

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