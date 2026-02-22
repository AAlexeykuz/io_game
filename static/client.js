// СОКЕТ И URL
const hostname = window.location.hostname;

const url = new URL("/ws", `ws://${hostname}`);
url.port = "8000"

const socket = new WebSocket(url);

const httpUrl = new URL("/", `http://${hostname}`);
httpUrl.port = "8000";


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
            movement: [dx, dy],
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
    if (key === 'W' || key === 'ArrowUp' || key === 'w') {
        upPressed = true;
        changed = true;
    }
    if (key === 'S' || key === 'ArrowDown' || key === 's') {
        downPressed = true;
        changed = true;
    }
    if (key === 'A' || key === 'ArrowLeft' || key === 'a') {
        leftPressed = true;
        changed = true;
    }
    if (key === 'D' || key === 'ArrowRight' || key === 'd') {
        rightPressed = true;
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
    if (key === 'W' || key === 'ArrowUp' || key === 'w') {
        upPressed = false;
        changed = true;
    }
    if (key === 'S' || key === 'ArrowDown' || key === 's') {
        downPressed = false;
        changed = true;
    }
    if (key === 'A' || key === 'ArrowLeft' || key === 'a') {
        leftPressed = false;
        changed = true;
    }
    if (key === 'D' || key === 'ArrowRight' || key === 'd') {
        rightPressed = false;
        changed = true;
    }

    if (changed) {
        updateDirection();
    }
})




const texture = document.createElement('img');
function showTexture(texture_name, x, y, width) {
    
    texture.src = `/static/textures/${texture_name}`;
    

    texture.style.position = 'absolute';
    texture.style.left = x + 'px';
    texture.style.top = y + 'px';

    texture.style.width = width + 'px';

    // ПОВОРОТ ПЕРСОНАЖА
    document.addEventListener('mousemove', (e) => {
        const mouseX = e.clientX;
        const mouseY = e.clientY;
        
        const rect = texture.getBoundingClientRect();
        
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const dx = mouseX - centerX;
        const dy = mouseY - centerY;
        
        // Угол (радианы -> градусы)
        const angle = Math.atan2(dy, dx) * 180 / Math.PI;
        
        texture.style.rotate = angle + 'deg';
    });
    texture.className = 'texture';
    document.body.appendChild(texture);
    return texture;
}

// ПОЛУЧЕНИЕ ДАННЫХ JSON
fetch(httpUrl)
        .then(response => {
        if (response.ok) {
            socket.onmessage = function(event){
            document.querySelectorAll('.texture').forEach(e => e.remove());
            
            let data = JSON.parse(event.data);
            
            for (const t of data.texture) {
                const [name, x, y, w, h] = t;
                showTexture(name, x, y, w, h);
            }

            } 
        } else {
            throw new Error('Ошибка HTTP: ' + response.status);
        }})