// Управление музыкой (рандомное переключение)
const MusicManager = (function() {
    // Пути к трекам
    const tracks = [
        '/static/music/track1.mp3',
        '/static/music/track2.mp3',
        '/static/music/track3.mp3',
        '/static/music/track4.mp3',
        '/static/music/track5.mp3',
        '/static/music/track6.mp3',
        '/static/music/track7.mp3',
        '/static/music/track8.mp3',
        '/static/music/track9.mp3',
        '/static/music/track10.mp3',
        '/static/music/track11.mp3',
        '/static/music/track12.mp3',
        '/static/music/track13.mp3',
        '/static/music/track14.mp3',
        '/static/music/track15.mp3',
        '/static/music/track16.mp3',
        '/static/music/track17.mp3',
        '/static/music/track18.mp3',
        '/static/music/track19.mp3',
        '/static/music/track20.mp3',
        '/static/music/track21.mp3',
        '/static/music/track22.mp3',
        '/static/music/track23.mp3',
        '/static/music/track24.mp3',
        '/static/music/track25.mp3',
        '/static/music/track26.mp3',
        '/static/music/track27.mp3',
        '/static/music/track28.mp3',
        '/static/music/track29.mp3',
        '/static/music/track30.mp3',
        '/static/music/track31.mp3',
        '/static/music/track32.mp3',
        '/static/music/track33.mp3'
    ];
    
    let currentSound = null;
    let currentTrackIndex = 0;   // индекс текущего трека
    let isPlaying = false;
    
    // Получить случайный индекс, отличный от предыдущего
    function getRandomIndex(previousIndex) {
        if (tracks.length === 1) return 0; // если всего один трек, он и будет
        
        let newIndex;
        do {
            newIndex = Math.floor(Math.random() * tracks.length);
        } while (newIndex === previousIndex);
        return newIndex;
    }
    
    function playTrack(index) {
        if (currentSound) {
            currentSound.stop();
        }
        const url = tracks[index];
        currentSound = new Howl({
            src: [url],
            loop: false,
            volume: 0.5,
            onend: function() {
                // Когда трек закончился, выбираем случайный следующий
                const nextIndex = getRandomIndex(currentTrackIndex);
                currentTrackIndex = nextIndex;
                playTrack(currentTrackIndex);
            },
            onplayerror: function(e) {
                console.warn('Ошибка воспроизведения:', e);
                // При ошибке пробуем переключиться на другой трек через 2 секунды
                setTimeout(() => {
                    if (isPlaying) {
                        const nextIndex = getRandomIndex(currentTrackIndex);
                        currentTrackIndex = nextIndex;
                        playTrack(currentTrackIndex);
                    }
                }, 2000);
            }
        });
        currentSound.play();
        isPlaying = true;
    }
    
    return {
        start: function() {
            if (isPlaying) return;
            // Начинаем со случайного трека (не обязательно с 0)
            currentTrackIndex = Math.floor(Math.random() * tracks.length);
            playTrack(currentTrackIndex);
        },
        stop: function() {
            if (currentSound) {
                currentSound.stop();
                currentSound = null;
            }
            isPlaying = false;
        }
    };
})();

window.MusicManager = MusicManager;