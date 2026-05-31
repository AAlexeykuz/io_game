// ---------- Конфигурация ----------
const GameConfig = {
    WEBSOCKET_PORT: "8000",
    INTERPOLATION_OFFSET_MS: 50,
    MAX_STATE_BUFFER_SIZE: 20,
    MOVEMENT_KEY_MAP: {
        KeyW: "up",
        ArrowUp: "up",
        KeyS: "down",
        ArrowDown: "down",
        KeyA: "left",
        ArrowLeft: "left",
        KeyD: "right",
        ArrowRight: "right",
    },
};
const USERNAME_LIST_UPDATE_INTERVAL_MS = 1000;

// ---------- Утилиты ----------
const MathUtils = {
    lerp(start, end, t) {
        return start + (end - start) * t;
    },

    lerpAngle(a, b, t) {
        const { PI } = Math;
        const delta = ((((b - a + PI) % (2 * PI)) + 2 * PI) % (2 * PI)) - PI;
        return a + delta * t;
    },

    getMouseAngle(mouseX, mouseY, centerX, centerY) {
        const { atan2, PI } = Math;
        const dx = mouseX - centerX;
        const dy = mouseY - centerY;
        return atan2(dy, dx) + PI / 2;
    },
};

// ---------- Контроллер ввода ----------
class InputController {
    constructor(sendCallback) {
        this.sendData = sendCallback; // функция отправки данных на сервер
        this.movement = {
            up: false,
            down: false,
            left: false,
            right: false,
        };
        this.setupListeners();
    }

    setupListeners() {
        document.addEventListener("keydown", (e) => this.handleKey(e, true));
        document.addEventListener("keyup", (e) => this.handleKey(e, false));
        document.addEventListener("mousemove", (e) => this.handleMouseMove(e));
        document.addEventListener("click", (e) => this.handleMouseClick(e));
    }

    handleKey(event, isPressed) {
        const direction = GameConfig.MOVEMENT_KEY_MAP[event.code];
        if (!direction) return;
        this.movement[direction] = isPressed;
        this.updateDirection();
    }

    handleMouseMove(event) {
        const canvas = document.getElementById("gameCanvas");
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const angle = MathUtils.getMouseAngle(
            event.clientX,
            event.clientY,
            centerX,
            centerY,
        );
        this.sendData({ angle: angle });
    }

    handleMouseClick(event) {
        this.sendData({ shoot: true });
    }

    updateDirection() {
        let dx = 0,
            dy = 0;
        if (this.movement.left) dx -= 1;
        if (this.movement.right) dx += 1;
        if (this.movement.up) dy -= 1;
        if (this.movement.down) dy += 1;
        this.sendData({ movement: [dx, dy] });
    }
}

// ---------- Менеджер текстур ----------
class TextureManager {
    constructor() {
        this.cache = new Map();
    }

    get(name) {
        if (!this.cache.has(name)) {
            const img = new Image();
            img.src = `/static/textures/${name}`;
            this.cache.set(name, img);
        }
        return this.cache.get(name);
    }
}

// ---------- Интерполятор состояний ----------
class StateInterpolator {
    constructor() {
        this.states = [];
    }

    addState(textureData, textData, mapData) {
        this.states.push({
            timestamp: Date.now(),
            texture: textureData || [],
            text: textData || [],
            map: mapData ? [...mapData] : null,
        });

        if (this.states.length > GameConfig.MAX_STATE_BUFFER_SIZE) {
            this.states.shift();
        }
    }

    /**
     * Возвращает интерполированное состояние для заданного времени рендера
     */
    getInterpolatedState(renderTime) {
        if (this.states.length === 0) return null;

        let start = null;
        let end = null;

        for (let i = 0; i < this.states.length - 1; i++) {
            if (
                this.states[i].timestamp <= renderTime &&
                renderTime <= this.states[i + 1].timestamp
            ) {
                start = this.states[i];
                end = this.states[i + 1];
                break;
            }
        }

        if (!start || !end) {
            // Используем последнее известное состояние
            const last = this.states[this.states.length - 1];
            return { state: last, t: 0 };
        }

        const total = end.timestamp - start.timestamp;
        const portion = renderTime - start.timestamp;
        const t = Math.min(portion / total, 1.0);
        return { startState: start, endState: end, t };
    }
}

// ---------- Рендерер ----------
class GameRenderer {
    constructor(canvasId, textureManager) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext("2d");
        this.textureManager = textureManager;
        this.mapRadius = null;
        this.mapCenterX = null;
        this.mapCenterY = null;
        this.setupCanvasResize();
    }

    setupCanvasResize() {
        const resize = () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener("resize", resize);
    }

    setMapInfo(mapRadius, mapCenterX, mapCenterY) {
        this.mapRadius = mapRadius;
        this.mapCenterX = mapCenterX;
        this.mapCenterY = mapCenterY;
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawTexture(textureName, x, y, width, height, angle) {
        const img = this.textureManager.get(textureName);
        if (!img.complete) return;

        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(angle);
        this.ctx.drawImage(img, -width / 2, -height / 2, width, height);
        this.ctx.restore();
    }

    drawMap(radius, centerX, centerY) {
        if (radius === null || centerX === null || centerY === null) return;

        const offsetX = this.canvas.width / 2;
        const offsetY = this.canvas.height / 2;

        this.ctx.save();
        this.ctx.beginPath();
        this.ctx.arc(
            centerX + offsetX,
            centerY + offsetY,
            radius,
            0,
            Math.PI * 2,
        );
        this.ctx.fillStyle = "#ffffff"; // Цвет игровой зона
        this.ctx.fill();
        this.ctx.restore();
    }

    drawText(text, x, y) {
        this.ctx.save();
        this.ctx.font = "16px Arial";
        this.ctx.fillStyle = "#ffffff";
        this.ctx.textAlign = "center";
        this.ctx.textBaseline = "middle";

        // обводка текста
        this.ctx.strokeStyle = "#000000";
        this.ctx.lineWidth = 4;
        this.ctx.strokeText(text, x, y);

        this.ctx.fillText(text, x, y);
        this.ctx.restore();
    }

    /**
     * Рисует интерполированное состояние
     */
    renderInterpolatedState(stateA, stateB, t) {
        const offsetX = this.canvas.width / 2;
        const offsetY = this.canvas.height / 2;

        // КАРТА
        if (stateA.map && stateB.map) {
            const [r1, x1, y1] = stateA.map;
            const [r2, x2, y2] = stateB.map;

            const radius = MathUtils.lerp(r1, r2, t);
            const centerX = MathUtils.lerp(x1, x2, t);
            const centerY = MathUtils.lerp(y1, y2, t);

            this.drawMap(radius, centerX, centerY);
        } else if (stateA.map) {
            this.drawMap(stateA.map[0], stateA.map[1], stateA.map[2]);
        }

        // ТЕКСТУРЫ
        const endMap = new Map(stateB.texture.map((item) => [item[0], item]));

        for (const startItem of stateA.texture) {
            const [id, textureName, x1, y1, width, height, angle1] = startItem;
            const endItem = endMap.get(id);
            if (!endItem) continue;

            const [, , x2, y2, , , angle2] = endItem;

            const x = MathUtils.lerp(x1, x2, t) + offsetX;
            const y = MathUtils.lerp(y1, y2, t) + offsetY;
            const angle = MathUtils.lerpAngle(angle1, angle2, t);

            this.drawTexture(textureName, x, y, width, height, angle);
        }

        // ТЕКСТ
        const endTextMap = new Map(stateB.text.map((item) => [item[0], item]));

        for (const startItem of stateA.text) {
            const [id, text, x1, y1] = startItem;
            const endItem = endTextMap.get(id);
            if (!endItem) continue;

            const [, , x2, y2] = endItem;

            const x = MathUtils.lerp(x1, x2, t) + offsetX;
            const y = MathUtils.lerp(y1, y2, t) + offsetY;

            this.drawText(text, x, y);
        }
    }
}

// ---------- Клиент ----------
class GameClient {
    constructor(roomId) {
        this.roomId = roomId;
        this.socket = null;
        this.username = null;
        this.textureManager = new TextureManager();
        this.renderer = new GameRenderer("gameCanvas", this.textureManager);
        this.interpolator = new StateInterpolator();
        this.inputController = new InputController((data) =>
            this.sendData(data),
        );
        this.restartButton = null;
        this.menuElement = document.querySelector(".game-data");

        this.setupUsername();
        this.setupUI();
        this.startGameLoop();
        this.setupWebSocket();
        this.updateUserlistLoop();
    }

    setupUsername() {
        let name = prompt("Введите ник игрока");
        name = name.trim();
        if (!name || name === "") {
            const randomNumber = Math.floor(1000 + Math.random() * 9000); // 4-значное число
            this.username = `Player ${randomNumber}`;
        } else if (name.length > 20) {
            this.username = name.slice(0, 20);
        } else {
            this.username = name;
        }
    }

    async updateUserlistLoop() {
        this.list = document.getElementById("userlist");

        try {
            const urlParams = new URLSearchParams(window.location.search);
            const request = `/rooms/${urlParams.get("id")}`;
            console.log(request);
            const response = await fetch(request);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();

            this.list.innerHTML = "";
            for (let i = 0; i < data.players.length; i++) {
                let li = document.createElement("li");
                li.classList.add("section-userlist");
                li.textContent = data.players[i];
                this.list.appendChild(li);
            }
        } catch (error) {
            console.error("Ошибка при получении списка игроков:", error);
        } finally {
            this.isUpdatingUserlist = false;
            // Планируем следующее обновление
            setTimeout(
                () => this.updateUserlistLoop(),
                USERNAME_LIST_UPDATE_INTERVAL_MS,
            );
        }
    }

    setupWebSocket() {
        const hostname = window.location.hostname;
        const wsUrl = new URL(`/rooms/${this.roomId}`, `ws://${hostname}`);
        wsUrl.port = GameConfig.WEBSOCKET_PORT;
        wsUrl.searchParams.append("nickname", this.username);

        this.socket = new WebSocket(wsUrl);

        this.socket.onclose = (event) => {
            if (event.code === 1006 || !event.wasClean) {
                alert("Ошибка подключения к серверу");
                window.location.href = "/";
            }
        };

        this.socket.onmessage = (event) => this.handleMessage(event);
    }

    handleMessage(event) {
        const data = JSON.parse(event.data);

        if (data.alert) alert(data.alert);

        if (data.game_start !== undefined) {
            if (data.game_start) {
                if (this.menuElement) this.menuElement.classList.add("hide");
                if (this.renderer.canvas)
                    this.renderer.canvas.classList.remove("hide");
            } else {
                if (this.menuElement) this.menuElement.classList.remove("hide");
                if (this.renderer.canvas)
                    this.renderer.canvas.classList.add("hide");
            }
        }

        if (data.texture || data.text || data.map)
            this.interpolator.addState(data.texture, data.text, data.map);

        if (data.dead) this.showRestartButton();
        else this.hideRestartButton();
    }

    showRestartButton() {
        // Проверяем, чтобы кнопка уже не была на экране
        if (document.getElementById("restart-btn")) return;

        const button = document.createElement("button");
        button.id = "restart-btn";
        button.innerText = "Начать заново";

        // Стили перенести в CSS
        Object.assign(button.style, {
            position: "fixed",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            padding: "15px 30px",
            fontSize: "20px",
            zIndex: "1000",
            cursor: "pointer",
            backgroundColor: "#ff4757",
            color: "white",
            border: "none",
            borderRadius: "5px",
            boxShadow: "0 4px 6px rgba(0,0,0,0.3)",
        });

        button.onclick = () => {
            this.sendData({ restart: true });
        };

        document.body.appendChild(button);
        this.restartButton = button;
    }

    hideRestartButton() {
        if (this.restartButton !== null) this.restartButton.remove();
    }

    sendData(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }

    setupUI() {
        const roomIdElement = document.getElementById("room_id");
        if (roomIdElement) {
            roomIdElement.textContent = `Код комнаты: ${this.roomId}`;
        }

        const startButton = document.getElementById("start-button");
        if (startButton) {
            startButton.addEventListener("click", () => {
                this.sendData(["start"]);
            });
        }
    }

    startGameLoop() {
        const loop = () => {
            this.render();
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    render() {
        this.renderer.clear();

        const now = Date.now();
        const renderTime = now - GameConfig.INTERPOLATION_OFFSET_MS;

        const interpolated = this.interpolator.getInterpolatedState(renderTime);
        if (!interpolated) return;

        if (interpolated.startState && interpolated.endState) {
            this.renderer.renderInterpolatedState(
                interpolated.startState,
                interpolated.endState,
                interpolated.t,
            );
        } else if (interpolated.state) {
            // Рендер без интерполяции (последнее известное состояние)
            this.renderer.renderInterpolatedState(
                interpolated.state,
                interpolated.state,
                0,
            );
        }
    }
}

// ---------- Инициализация ----------
document.addEventListener("DOMContentLoaded", () => {
    const urlParams = new URLSearchParams(window.location.search);
    const roomId = urlParams.get("id");

    if (!roomId) {
        alert("Не указан ID комнаты");
        window.location.href = "/";
        return;
    }

    window.gameClient = new GameClient(roomId);
});
