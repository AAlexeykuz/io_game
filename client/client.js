// СОКЕТ
const hostname = window.location.hostname;
const protocol = window.location.protocol === "https:" ? "wss" : "ws";
const url = new URL("/ws", `${protocol}://${hostname}`);
if (/^\d/.test(hostname)) url.port = "8000"; // если localtunnel (начинается не с цифры), то не ставим порт
const socket = new WebSocket(url);


// КАНВАС
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");