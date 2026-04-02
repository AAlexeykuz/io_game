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

// МАТЕМАТИКА
const {PI, atan2} = Math


// настройка окна
function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resize()
window.addEventListener("resize", resize);


// Функция отправки направления на сервер
function sendData(data) {
    if (socket.readyState !== WebSocket.OPEN) {
        return
    }
    const message = JSON.stringify(data); 
    socket.send(message);
}

    
// Обработчик нажатия клавиш
const MOVEMENT_KEY_MAP = {
    "KeyW": "up", 
    "ArrowUp": "up",
    
    "KeyS": "down", 
    "ArrowDown": "down",

    "KeyA": "left",
    "ArrowLeft": "left",

    "KeyD": "right",
    "ArrowRight": "right"
};


const movement = {
    up: false,
    down: false,
    left: false,
    right: false
}


function handleMovement(event, isPressed) {
    const direction = MOVEMENT_KEY_MAP[event.code];
    if (!direction) return;
    movement[direction] = isPressed
    updateDirection();
}


document.addEventListener("keydown", event => handleMovement(event, true));
document.addEventListener("keyup", event => handleMovement(event, false));


// Функция пересчета направления и отправки
function updateDirection() {
    let dx = 0;
    let dy = 0;

    if (movement.left) dx -= 1;
    if (movement.right) dx += 1;
    if (movement.up) dy -= 1;
    if (movement.down) dy += 1;

    sendData({movement: [dx, dy]});
}


function getMouseAngle(mouseX, mouseY, centerX, centerY) {
    const dx = mouseX - centerX;
    const dy = mouseY - centerY;
    
    const angle = atan2(dy, dx) + PI / 2;
    return angle;
}


function SetupMouseTracking() {
    document.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const angle = getMouseAngle(e.x, e.y, centerX, centerY)

        sendData({
            angle: angle,
        })
    })
}


SetupMouseTracking()

const textureCache = {};


function getTexture(name) {
    if (!textureCache[name]) {
        const img = new Image();
        img.src = `/static/textures/${name}`;
        textureCache[name] = img;
    }
    return textureCache[name];
}

function lerp(start, end, t) {
    return start + (end - start) * t;
}

// lerp для углов, чтобы не поворачивал на 360 градусов
function lerpAngle(a, b, t) {
    const delta = ((b - a + PI) % (2 * PI) + 2 * PI) % (2 * PI) - PI;
    return a + delta * t;
}


function drawTexture(texture_name, x, y, size_x, size_y, angle) {
    const img = getTexture(texture_name);
    if (!img.complete) return;
    ctx.save();
    ctx.translate(x + size_x / 2, y + size_y / 2);
    ctx.rotate(angle);
    ctx.drawImage(img, -size_x / 2, -size_y / 2, size_x, size_y);
    ctx.restore();
}


// ПОЛУЧЕНИЕ ДАННЫХ JSON
socket.onmessage = function(event) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let data = JSON.parse(event.data);
    for (const t of data.texture) {
        const [id, texture_name, x, y, size_x, size_y, angle] = t;
        drawTexture(texture_name, x, y, size_x, size_y, angle);
    }
} 