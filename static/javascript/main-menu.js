class MainMenuController {
    constructor(createButtonId) {
        this.createButton = document.getElementById(createButtonId);
        if (!this.createButton) {
            throw new Error(`Button with id "${createButtonId}" not found`);
        }
        this.API_URL = '/rooms';
        this.init();
    }

    init() {
        this.createButton.addEventListener('click', () => this.handleCreateGame());
    }

    async handleCreateGame() {
        try {
            const response = await fetch(this.API_URL, { method: 'POST' });

            if (response.ok) {
                const data = await response.json();
                window.location.href = `../static/html/game.html?id=${data.id}`;
            } else {
                const errorText = await response.text();
                this.showError(`Ошибка сервера: ${response.status}`, errorText);
            }
        } catch (error) {
            console.error('Ошибка клиента:', error);
            this.showError('Ошибка клиента. Проверьте соединение с интернетом.');
        }
    }

    showError(userMessage, detail = '') {
        alert(userMessage);
        if (detail) {
            console.error('Детали ошибки:', detail);
        }
    }
}

// Запуск при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    new MainMenuController('create-game-btn');
});