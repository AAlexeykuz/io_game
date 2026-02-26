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
// Начальная позиция персонажа
let textureX = 0;
let textureY = 0;

// Состояние клавиш
let upPressed = false;    // W
let downPressed = false;  // S
let leftPressed = false;  // A
let rightPressed = false; // D
const MOVE_SPEED = 1.5;

function updateDirection() {
    if (leftPressed) textureX -= MOVE_SPEED;
    if (rightPressed) textureX += MOVE_SPEED;
    if (upPressed) textureY -= MOVE_SPEED;
    if (downPressed) textureY += MOVE_SPEED;

    // sendMovement(dx, dy);
}
// Функция отправки направления на сервер
function sendMovement(dx, dy) {
    if (socket.readyState === WebSocket.OPEN) { // Проверка, открыто ли WebSocket-соединениеx
        const message = JSON.stringify({
            movement: [dx, dy],
        });  // Преобразование объекта в строку JSON
        socket.send(message);
    }
}

    
// Обработчик нажатия клавиш
document.addEventListener('keydown', (e) => {
    const code = e.code;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyW', 'KeyA', 'KeyS', 'KeyD'].includes(code)) {
        e.preventDefault(); // Предотвращение прокрутки страницы
    }

    let changed = false;
    if (code === 'KeyW' || code === 'ArrowUp') {
        upPressed = true;
        changed = true;
    }
    if (code === 'KeyS' || code === 'ArrowDown') {
        downPressed = true;
        changed = true;
    }
    if (code === 'KeyA' || code === 'ArrowLeft') {
        leftPressed = true;
        changed = true;
    }
    if (code === 'KeyD' || code === 'ArrowRight') {
        rightPressed = true;
        changed = true;
    }

    if (changed) {
        updateDirection();
    }
})

// Обработчик отпускания клавиш
document.addEventListener('keyup', (e) => {
    const code = e.code;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyW', 'KeyA', 'KeyS', 'KeyD'].includes(code)) {
        e.preventDefault(); // Предотвращение прокрутки страницы
    }

    let changed = false;
    if (code === 'KeyW' || code === 'ArrowUp') {
        upPressed = false;
        changed = true;
    }
    if (code === 'KeyS' || code === 'ArrowDown') {
        downPressed = false;
        changed = true;
    }
    if (code === 'KeyA' || code === 'ArrowLeft') {
        leftPressed = false;
        changed = true;
    }
    if (code === 'KeyD' || code === 'ArrowRight') {
        rightPressed = false;
        changed = true;
    }

    if (changed) {
        updateDirection();
    }
})

const texture = document.createElement('img');
let textureInitialized = false;

function showTexture(texture_name, x, y, width) {
    
    // Инициализация (только первый раз)
    if (!textureInitialized) {
        texture.src = `../static/textures/${texture_name}`;
        texture.style.position = 'absolute';
        texture.className = 'texture';
        document.body.appendChild(texture);
        textureInitialized = true;
        
        // Добавляем обработчик мыши только один раз
        setupMouseTracking();
    }
    
    // Обновляем размер
    texture.style.width = width + 'px';
}

// Функция для анимации (постоянно обновляет позицию)
function animate() {
    if (textureInitialized) {
        // Обновляем позицию на основе нажатых клавиш
        updateDirection();
        
        // Применяем новую позицию к текстуре
        texture.style.left = textureX + 'px';
        texture.style.top = textureY + 'px';
    }
    requestAnimationFrame(animate);
}

function setupMouseTracking() {
    document.addEventListener('mousemove', (e) => {
        const mouseX = e.clientX;
        const mouseY = e.clientY;
        
        const rect = texture.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const dx = mouseX - centerX;
        const dy = mouseY - centerY;
        
        const angle = Math.atan2(dy, dx) * 180 / Math.PI + 90;
        texture.style.rotate = angle + 'deg';
    });
}

// Запускаем анимацию (ТОЛЬКО ОДИН РАЗ)
animate();

// Показываем начальную текстуру
showTexture('coca.png', textureX, textureY, 50);
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
