// СОКЕТ
const hostname = window.location.hostname;
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const url = new URL("/ws", `${protocol}://${hostname}`);
if (/^\d/.test(hostname)) url.port = "8000"; // если localtunnel (начинается не с цифры), то не ставим порт
const socket = new WebSocket(url);


// КАНВАС
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");


// Состояние клавиш
let upPressed = false;    // W
let downPressed = false;  // S
let leftPressed = false;  // A
let rightPressed = false; // D

// Функция пересчета направления и отправки
function updateDirection() {
    let dx = 0;
    let dy = 0;

    if (leftPressed) dx -= 1;
    if (rightPressed) dx += 1;
    if (upPressed) dy -= 1;
    if (downPressed) dy += 1;

    sendMovement(dx, dy);
}

// Функция отправки направления на сервер
function sendMovement(dx, dy) {
    if (socket.readyState === WebSocket.OPEN) { // Проверка, открыто ли WebSocket-соединение
        const message = JSON.stringify({
            type: "movement",
            data: [dx, dy]
        });  // Преобразование объекта в строку JSON
        socket.send(message);
    }
}

// Обработчик нажатия клавиш
document.addEventListener('keydown', (e) => {
    const key = e.key;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd'].includes(key)) {
        e.preventDefault(); // Предотвращение прокрутки страницы
    }

    let changed = false;
    if (key === 'w' || key === 'ArrowUp') {
        upPressed = true;
        changed = true;
    }
    if (key === 's' || key === 'ArrowDown') {
        upPressed = true;
        changed = true;
    }
    if (key === 'a' || key === 'ArrowLeft') {
        upPressed = true;
        changed = true;
    }
    if (key === 'd' || key === 'ArrowRight') {
        upPressed = true;
        changed = true;
    }

    if (changed) {
        updateDirection();
    }
})

// Обработчик отпускания клавиш
document.addEventListener('keyup', (e) => {
    const key = e.key;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd'].includes(key)) {
        e.preventDefault(); // Предотвращение прокрутки страницы
    }

    let changed = false;
    if (key === 'w' || key === 'ArrowUp') {
        upPressed = false;
        changed = true;
    }
    if (key === 's' || key === 'ArrowDown') {
        upPressed = false;
        changed = true;
    }
    if (key === 'a' || key === 'ArrowLeft') {
        upPressed = false;
        changed = true;
    }
    if (key === 'd' || key === 'ArrowRight') {
        upPressed = false;
        changed = true;
    }

    if (changed) {
        updateDirection();
    }
})