// ---------- Конфигурация ----------
const GameConfig = {
    WEBSOCKET_PORT: '8000',
    INTERPOLATION_OFFSET_MS: 50,
    MAX_STATE_BUFFER_SIZE: 20,
    MOVEMENT_KEY_MAP: {
        KeyW: 'up',
        ArrowUp: 'up',
        KeyS: 'down',
        ArrowDown: 'down',
        KeyA: 'left',
        ArrowLeft: 'left',
        KeyD: 'right',
        ArrowRight: 'right',
    },
};

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
        document.addEventListener('keydown', (e) => this.handleKey(e, true));
        document.addEventListener('keyup', (e) => this.handleKey(e, false));
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    }

    handleKey(event, isPressed) {
        const direction = GameConfig.MOVEMENT_KEY_MAP[event.code];
        if (!direction) return;
        this.movement[direction] = isPressed;
        this.updateDirection();
    }

    handleMouseMove(event) {
        const canvas = document.getElementById('gameCanvas');
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const angle = MathUtils.getMouseAngle(event.clientX, event.clientY, centerX, centerY);
        this.sendData({ angle });
    }

    updateDirection() {
        let dx = 0, dy = 0;
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
        this.states = []; // { timestamp, texture }
    }

    addState(textureData) {
        this.states.push({
            timestamp: Date.now(),
            texture: textureData,
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
            if (this.states[i].timestamp <= renderTime && renderTime <= this.states[i + 1].timestamp) {
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
        this.ctx = this.canvas.getContext('2d');
        this.textureManager = textureManager;
        this.setupCanvasResize();
    }

    setupCanvasResize() {
        const resize = () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener('resize', resize);
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

    /**
     * Рисует интерполированное состояние
     */
    renderInterpolatedState(stateA, stateB, t) {
        const offsetX = this.canvas.width / 2;
        const offsetY = this.canvas.height / 2;

        // Создаём Map для быстрого доступа к конечным объектам по id
        const endMap = new Map(stateB.texture.map(item => [item[0], item]));

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
    }
}

// ---------- Клиент ----------
class GameClient {
    constructor(roomId) {
        this.roomId = roomId;
        this.socket = null;
        this.textureManager = new TextureManager();
        this.renderer = new GameRenderer('gameCanvas', this.textureManager);
        this.interpolator = new StateInterpolator();
        this.inputController = new InputController((data) => this.sendData(data));

        this.setupWebSocket();
        this.setupUI();
        this.startGameLoop();
    }

    setupWebSocket() {
        const hostname = window.location.hostname;
        const wsUrl = new URL(`/rooms/${this.roomId}`, `ws://${hostname}`);
        wsUrl.port = GameConfig.WEBSOCKET_PORT;

        this.socket = new WebSocket(wsUrl);

        this.socket.onclose = (event) => {
            if (event.code === 1006 || !event.wasClean) {
                alert('Ошибка подключения к серверу');
                window.location.href = '/';
            }
        };

        this.socket.onmessage = (event) => this.handleMessage(event);
    }

    handleMessage(event) {
        const data = JSON.parse(event.data);

        if (data.alert) {
            alert(data.alert);
        }

        if (data.texture) {
            this.interpolator.addState(data.texture);
        }
    }

    sendData(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        }
    }

    setupUI() {
        const roomIdElement = document.getElementById('room_id');
        if (roomIdElement) {
            roomIdElement.textContent = `Код комнаты: ${this.roomId}`;
        }

        const startButton = document.getElementById('start-button');
        if (startButton) {
            startButton.addEventListener('click', () => {
                this.sendData(['start']);
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
                interpolated.t
            );
        } else if (interpolated.state) {
            // Рендер без интерполяции (последнее известное состояние)
            this.renderer.renderInterpolatedState(
                interpolated.state,
                interpolated.state,
                0
            );
        }
    }
}

// ---------- Инициализация ----------
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const roomId = urlParams.get('id');

    if (!roomId) {
        alert('Не указан ID комнаты');
        window.location.href = '/';
        return;
    }

    window.gameClient = new GameClient(roomId);
});