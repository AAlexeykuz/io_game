document
    .getElementById("create-game-btn")
    .addEventListener("click", async () => {
        try {
            const response = await fetch("/rooms", {
                method: "POST",
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = `../static/html/game.html?id=${data.id}`;
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error("Ошибка сервера", response.status, errorData);
                alert(`Ошибка сервера: ${response.status}`);
            }
        } catch (error) {
            console.error("Ошибка клиента:", error);
            alert("Ошибка клиента. Проверьте своё соединение");
        }
    });
