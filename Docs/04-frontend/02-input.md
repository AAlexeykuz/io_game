# Спецификация: Обработка ввода (фронтенд)

## Цель
Собирать действия игрока (клавиши, мышь) и отправлять их на сервер.

## События клавиатуры (движение)
- Отслеживаются клавиши W, A, S, D.
- Состояние каждой клавиши (нажата/отпущена) хранится в объекте `keys`.
- При изменении состояния (нажатие/отпускание) формируется пакет `move` и отправляется на сервер.
- Если клавиша удерживается, повторные пакеты не нужны — сервер получает только изменения.

## События мыши (направление)
- Отслеживается положение мыши относительно Canvas.
- Вычисляется угол от центра игрока до курсора мыши в градусах.
- При каждом движении мыши отправляется пакет `move` с обновлённым `mouse_angle` (даже если клавиши не менялись).

## События мыши (стрельба)
- Отслеживается клик левой кнопкой мыши (`mousedown`).
- При клике отправляется пакет `shoot`.
- Для избежания спама можно добавить задержку на клиенте, но основная защита — на сервере (cooldown).

## Формирование пакетов
Все пакеты отправляются через WebSocket в формате JSON (см. `02-networking/01-protocol.md`).

## Обработка потери фокуса
- Если окно теряет фокус (например, игрок переключился на другую вкладку), все клавиши сбрасываются, отправляется пакет `move` с отпущенными клавишами.
- Также можно приостановить отправку `shoot`, чтобы не стрелять в фоне.

## Пример кода (псевдокод)
```javascript
let keys = { up: false, down: false, left: false, right: false };
let mouseAngle = 0;

window.addEventListener('keydown', (e) => {
  if (e.code === 'KeyW') keys.up = true;
  if (e.code === 'KeyS') keys.down = true;
  if (e.code === 'KeyA') keys.left = true;
  if (e.code === 'KeyD') keys.right = true;
  sendMove();
});

window.addEventListener('keyup', (e) => { /* аналогично */ });

canvas.addEventListener('mousemove', (e) => {
  mouseAngle = computeAngle(e);
  sendMove();
});

canvas.addEventListener('mousedown', (e) => {
  if (e.button === 0) sendShoot();
});

function sendMove() {
  socket.send(JSON.stringify({
    type: 'move',
    keys: keys,
    mouse_angle: mouseAngle
  }));
}

function sendShoot() {
  socket.send(JSON.stringify({ type: 'shoot' }));
}
```