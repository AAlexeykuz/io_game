// ---------- Конфигурация ----------
const ROOMS_API_URL = '/rooms';
const UPDATE_INTERVAL_MS = 3000;

// ---------- Модель комнаты ----------
class Room {
    constructor(id, playerCount, status) {
        this.id = id;
        this.playerCount = playerCount;
        this.status = status;
    }
}

// ---------- Представление списка комнат ----------
class RoomListView {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container with id "${containerId}" not found`);
        }
        this.isUpdating = false;
    }

    /**
     * Создаёт DOM-элемент для одной комнаты
     */
    createRoomElement(room) {
        const div = document.createElement('div');
        div.className = 'roomList';

        const li = document.createElement('li');
        const span = document.createElement('span');
        span.id = room.id;
        span.innerHTML = `Код: ${room.id}<br>Количество игроков: ${room.playerCount}<br>Статус: ${room.status}`;
        li.appendChild(span);
        div.appendChild(li);

        const button = document.createElement('button');
        button.textContent = 'Присоединиться';

        // потом сделаем так
        button.classList.add('enter_true');
        // if (room.status === 'Ожидание') {
        //     button.classList.add('enter_true');
        // } else {
        //     button.classList.add('enter_false');
        // }

        button.addEventListener('click', () => {
            window.location.href = `../html/game.html?id=${room.id}`;
        });

        div.appendChild(button);
        return div;
    }

    /**
     * Очищает контейнер и отрисовывает список комнат
     */
    render(rooms) {
        this.container.innerHTML = '';
        const fragment = document.createDocumentFragment();
        rooms.forEach(roomData => {
            const room = new Room(roomData.id, roomData.player_count, roomData.status);
            fragment.appendChild(this.createRoomElement(room));
        });
        this.container.appendChild(fragment);
    }

    /**
     * Получает данные с сервера и запускает рендеринг
     */
    async fetchAndRender() {
        if (this.isUpdating) return; // защита от параллельных вызовов
        this.isUpdating = true;

        try {
            const response = await fetch(ROOMS_API_URL);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            this.render(data.rooms);
        } catch (error) {
            console.error('Ошибка при получении комнат:', error);
        } finally {
            this.isUpdating = false;
            // Планируем следующее обновление
            setTimeout(() => this.fetchAndRender(), UPDATE_INTERVAL_MS);
        }
    }

    /**
     * Запускает цикл обновлений
     */
    start() {
        this.fetchAndRender();
    }
}

// ---------- Точка входа ----------
document.addEventListener('DOMContentLoaded', () => {
    const view = new RoomListView('list');
    view.start();
});
