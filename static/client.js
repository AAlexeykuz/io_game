// СОКЕТ
const hostname = window.location.hostname;
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const url = new URL("/ws", `${protocol}://${hostname}`);
if (/^\d/.test(hostname)) url.port = "8000"; // если localtunnel (начинается не с цифры), то не ставим порт
const socket = new WebSocket(url);


// КАНВАС
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");


// encode на клиенте
function sendMovement(x,y) {
    if (socket.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({
            type: "movement",
            data: [x, y]
        });
        socket.send(message);
    }
}




// ПОЛУЧЕНИЕ ДАННЫХ JSON
fetch('http://127.0.0.1:8000/')
        .then(response => {
        if (response.ok) {
            socket.onmessage = function(event){
            let data = JSON.parse(event.data);


            // ТЕСТОВОЕ СОЗДАНИЕ ПЕРСОНАЖА
            let person = document.createElement('img')
            person.id = 'person'
            person.src = ''
            document.body.appendChild(person)
            person.src = '/static/textures/'+data[0][0]

            } 
        } else {
            throw new Error('Ошибка HTTP: ' + response.status);
        }})
    