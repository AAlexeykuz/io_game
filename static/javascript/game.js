// СОКЕТ И URL

const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);

const id = urlParams.get("id");

console.log(id);

const hostname = window.location.hostname;
const url = new URL(`/rooms/${id}`, `ws://${hostname}`);
url.port = "8000";
const socket = new WebSocket(url);
const httpUrl = new URL("/", `http://${hostname}`);
httpUrl.port = "8000";

socket.onclose = (event) => {
    if (event.code === 1006 || !event.wasClean) {
        alert(`Ошибка подключения`);
        window.location.href = "/";
    }
};
// КАНВАС
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");

// МАТЕМАТИКА
const { PI, atan2 } = Math;

// настройка окна
function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resize();
window.addEventListener("resize", resize);

// Функция отправки направления на сервер
function sendData(data) {
    if (socket.readyState !== WebSocket.OPEN) {
        return;
    }
    const message = JSON.stringify(data);
    socket.send(message);
}

// Обработчик нажатия клавиш
const MOVEMENT_KEY_MAP = {
    KeyW: "up",
    ArrowUp: "up",

    KeyS: "down",
    ArrowDown: "down",

    KeyA: "left",
    ArrowLeft: "left",

    KeyD: "right",
    ArrowRight: "right",
};

const movement = {
    up: false,
    down: false,
    left: false,
    right: false,
};

function handleMovement(event, isPressed) {
    const direction = MOVEMENT_KEY_MAP[event.code];
    if (!direction) return;
    movement[direction] = isPressed;
    updateDirection();
}

document.addEventListener("keydown", (event) => handleMovement(event, true));
document.addEventListener("keyup", (event) => handleMovement(event, false));

// Функция пересчета направления и отправки
function updateDirection() {
    let dx = 0;
    let dy = 0;

    if (movement.left) dx -= 1;
    if (movement.right) dx += 1;
    if (movement.up) dy -= 1;
    if (movement.down) dy += 1;

    sendData({ movement: [dx, dy] });
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

        const angle = getMouseAngle(e.x, e.y, centerX, centerY);

        sendData({
            angle: angle,
        });
    });
}

SetupMouseTracking();

const textureCache = {};

function getTexture(name) {
    if (!textureCache[name]) {
        const img = new Image();
        img.src = `/static/textures/${name}`;
        textureCache[name] = img;
    }
    return textureCache[name];
}

function drawTexture(textureName, x, y, width, height, angle) {
    const img = getTexture(textureName);
    if (!img.complete) return;
    ctx.save();
    ctx.translate(x, y); //перемещение в центр экрана
    ctx.rotate(angle);
    ctx.drawImage(img, -width / 2, -height / 2, width, height);
    ctx.restore();
}

// ПОЛУЧЕНИЕ ДАННЫХ JSON

let serverStates = []; // Буфер состояний от сервера (для интерполяции)
const INTERPOLATION_OFFSET = 50; // Задержка в мс для сглаживания

socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    console.log("data");
    serverStates.push({
        timestamp: Date.now(),
        texture: data.texture,
    });
    if (serverStates.length > 20) serverStates.shift();
};

// ИНТЕРПОЛЯЦИЯ, АНИМАЦИЯ

function lerp(start, end, t) {
    return start + (end - start) * t;
}

// lerp для углов, чтобы не поворачивал на 360 градусов
function lerpAngle(a, b, t) {
    const delta = ((((b - a + PI) % (2 * PI)) + 2 * PI) % (2 * PI)) - PI;
    return a + delta * t;
}

function gameLoop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const now = Date.now();
    const renderTime = now - INTERPOLATION_OFFSET; // время, для которого рендерится игра

    if (serverStates.length >= 2) {
        let startState = null;
        let endState = null;

        // Нахождение двух состояний между renderTime
        for (let i = 0; i < serverStates.length - 1; i++) {
            if (
                serverStates[i].timestamp <= renderTime &&
                renderTime <= serverStates[i + 1].timestamp
            ) {
                startState = serverStates[i];
                endState = serverStates[i + 1];
                break;
            }
        }

        // Интерполяция по этим состоянием
        if (startState && endState) {
            const total = endState.timestamp - startState.timestamp;
            const portion = renderTime - startState.timestamp;
            const t = portion / total; // Коэффициент интерполяции (от 0 до 1)
            renderInterpolatedState(startState, endState, t);
        } else if (serverStates.length > 0) {
            // Если данных не хватает, рисуем последнее известное состояние
            const last = serverStates[serverStates.length - 1];
            renderInterpolatedState(last, last, 0);
        }
    }

    requestAnimationFrame(gameLoop);
}

function renderInterpolatedState(startState, endState, t) {
    const endTextureMap = new Map(endState.texture.map((e) => [e[0], e]));

    //смещение для центрирование: половина размеров экрана
    const offsetX = canvas.width / 2;
    const offsetY = canvas.height / 2;

    for (const startTexture of startState.texture) {
        const [id, textureName, x1, y1, width, height, angle1] = startTexture;
        const endTexture = endTextureMap.get(id);

        if (endTexture) {
            const [, , x2, y2, , , angle2] = endTexture;

            const interpolatedX = lerp(x1, x2, t) + offsetX;
            const interpolatedY = lerp(y1, y2, t) + offsetY;
            const interpolatedAngle = lerpAngle(angle1, angle2, t);

            drawTexture(
                textureName,
                interpolatedX,
                interpolatedY,
                width,
                height,
                interpolatedAngle,
            );
        }
    }
}

requestAnimationFrame(gameLoop);

const start_button = document.getElementById("start-button");
start_button.addEventListener("click", function () {
    sendData(["start"]);
});
