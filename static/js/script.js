document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initEventListeners();
    initPanorama();
    startNewRound();
});

let timerInterval, roundStartTime, score = 0, roundData = [], currentRound = 1;
const totalRounds = 5;
let guessCoords, map, marker, resultMap, player;

const elements = {
    timer: document.getElementById('timer'),
    currentRound: document.getElementById('currentRound'),
    score: document.getElementById('score'),
    guessButton: document.getElementById('guessButton'),
    closePopup: document.getElementById('closePopup'),
    closeMessagePopup: document.getElementById('closeMessagePopup'),
    exitToMenu: document.getElementById('exitToMenu'),
    playAgain: document.getElementById('playAgain'),
    resultPopup: document.getElementById('resultPopup'),
    resultMap: document.getElementById('resultMap'),
    message: document.getElementById('message'),
    messagePopup: document.getElementById('messagePopup'),
    gameOverPopup: document.getElementById('gameOverPopup'),
    gameOverReport: document.getElementById('gameOverReport')
};

const formatTime = seconds => `${Math.floor(seconds / 60)}:${seconds % 60 < 10 ? '0' : ''}${seconds % 60}`;

const updateInfo = () => {
    elements.currentRound.textContent = `${currentRound}/${totalRounds}`;
    elements.score.textContent = score;
};

const startTimer = duration => {
    let timer = duration;
    timerInterval = setInterval(() => {
        const minutes = String(Math.floor(timer / 60)).padStart(2, '0');
        const seconds = String(timer % 60).padStart(2, '0');
        elements.timer.textContent = `${minutes}:${seconds}`;

        if (--timer < 0) {
            clearInterval(timerInterval);
            showMessagePopup("Время вышло!");
            showGameOverPopup();
        }
    }, 1000);
};

const stopTimer = () => clearInterval(timerInterval);

const startNewRound = () => {
    updateInfo();
    stopTimer();
    startTimer(300);
    roundStartTime = Date.now();
};

const loadNewRound = () => {
    fetch('/next_location')
        .then(response => response.json())
        .then(data => {
            coord = data.coord;
            initPanorama();
            initMap();
            guessCoords = null;
            startNewRound();
        });
};

const getTimeRemaining = () => {
    const [minutes, seconds] = elements.timer.textContent.split(':').map(Number);
    return minutes * 60 + seconds;
};

const calculatePoints = distance => distance <= 25 ? 5000 : Math.round(Math.max(0, 5000 - 5 * (distance - 25)));

const getDistance = (coord1, coord2) => {
    const rad = x => x * Math.PI / 180;
    const R = 6378137;
    const dLat = rad(coord2.lat - coord1[0]);
    const dLong = rad(coord2.lng - coord1[1]);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(coord1[0])) * Math.cos(rad(coord2.lat)) * Math.sin(dLong / 2) ** 2;
    return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

const showResultPopup = (realCoords, guessCoords, distance) => {
    elements.resultPopup.style.display = 'flex';
    if (resultMap) resultMap.remove();
    resultMap = L.map(elements.resultMap).setView(realCoords, 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '© OpenStreetMap contributors'}).addTo(resultMap);

    L.marker(realCoords).addTo(resultMap);
    L.marker(guessCoords).addTo(resultMap);
    L.polyline([realCoords, [guessCoords.lat, guessCoords.lng]], {color: 'red'}).addTo(resultMap);

    document.getElementById('distance').textContent = `Расстояние: ${Math.round(distance)} метров`;
    document.getElementById('points').textContent = `Очки: ${calculatePoints(distance)}`;
};

const showMessagePopup = message => {
    elements.message.textContent = message;
    elements.messagePopup.style.display = 'flex';
};

const closeMessagePopup = () => elements.messagePopup.style.display = 'none';

const closePopup = () => {
    elements.resultPopup.style.display = 'none';
    if (currentRound < totalRounds) {
        currentRound++;
        loadNewRound();
    } else {
        showGameOverPopup();
    }
};

const showGameOverPopup = () => {
    elements.gameOverPopup.style.display = 'flex';
    const totalDistance = roundData.reduce((acc, data) => acc + data.distance, 0);
    const totalTime = roundData.reduce((acc, data) => acc + (data.time.split(':')[0] * 60 + parseInt(data.time.split(':')[1])), 0);
    elements.gameOverReport.innerHTML = roundData.map(data => `Раунд ${data.round}: ${data.distance} м - ${data.points} очков - ${data.time}`).join('<br>') +
        `<br>Итого: ${totalDistance} м - ${score} очков - ${formatTime(totalTime)}`;

    // Сохранить попытку, если все раунды пройдены и таймер не истек
    if (currentRound >= totalRounds && getTimeRemaining() > 0) {
        fetch('/save_attempt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                total_distance: totalDistance,
                total_points: score,
                total_time: formatTime(totalTime)
            })
        }).then(response => response.json())
            .then(data => {
                if (data.error) {
                    showMessagePopup(data.error);
                }
            });
    }
};

const exitToMenu = () => window.location.href = '/';

const playAgain = () => {
    elements.gameOverPopup.style.display = 'none';
    currentRound = 1;
    score = 0;
    roundData = [];
    loadNewRound();
};

const initMap = () => {
    if (map) map.remove();
    map = L.map('map').setView([53.347378, 83.77841], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '© OpenStreetMap contributors'}).addTo(map);

    map.on('click', e => {
        guessCoords = e.latlng;
        if (marker) map.removeLayer(marker);
        marker = L.marker(guessCoords).addTo(map);
    });

    const mapContainer = document.getElementById('mapContainer');
    mapContainer.addEventListener('mouseenter', () => {
        mapContainer.style.width = '800px';
        mapContainer.style.height = '600px';
        setTimeout(() => map.invalidateSize(), 300);
    });

    mapContainer.addEventListener('mouseleave', () => {
        mapContainer.style.width = '400px';
        mapContainer.style.height = '300px';
        setTimeout(() => map.invalidateSize(), 300);
    });
};

const initEventListeners = () => {
    const events = [
        {element: elements.guessButton, event: 'click', handler: checkGuess},
        {element: elements.closePopup, event: 'click', handler: closePopup},
        {element: elements.closeMessagePopup, event: 'click', handler: closeMessagePopup},
        {element: elements.exitToMenu, event: 'click', handler: exitToMenu},
        {element: elements.playAgain, event: 'click', handler: playAgain},
    ];
    events.forEach(({element, event, handler}) => {
        element.removeEventListener(event, handler);
        element.addEventListener(event, handler);
    });
};

const checkGuess = () => {
    if (!guessCoords) {
        showMessagePopup("Пожалуйста, выберите место на карте.");
    } else {
        const realCoords = coord;
        const distance = getDistance(realCoords, guessCoords);
        const points = calculatePoints(distance);

        stopTimer();

        const timeSpent = 300 - getTimeRemaining();
        roundData.push({
            round: currentRound,
            distance: Math.round(distance),
            points: points,
            time: formatTime(timeSpent)
        });

        score += points;

        showResultPopup(realCoords, guessCoords, distance);
    }
};

const loadAnotherLocation = () => {
    fetch('/next_location')
        .then(response => response.json())
        .then(data => {
            coord = data.coord;
            initPanorama();
        });
};

const initPanorama = () => {
    ymaps.ready(() => {
        if (player) {
            player.destroy();
            player = null;
        }
        if (!ymaps.panorama.isSupported()) return;
        ymaps.panorama.createPlayer('player', coord).done(it => {
                player = it
                const removeMarkers = () => player.getPanorama()
                    .getMarkers()
                    .forEach(marker => marker.properties.unsetAll());
                removeMarkers();
                player.events.add('panoramachange', removeMarkers);
            },
            error => {
                if (error.message === "No panoramas") {
                    loadAnotherLocation();
                } else {
                    alert(error.message)
                }
            }
        );
    });
};