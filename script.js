document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:5000';
    let gameId = null;
    let transactionLog = [];

    // --- DOM ELEMENTS ---
    const loader = document.getElementById('loader');
    const startScreen = document.getElementById('start-screen');
    const startButton = document.getElementById('start-button');
    const gameContent = document.getElementById('game-content');
    const ageDisplay = document.getElementById('age-display');
    const moneyDisplay = document.getElementById('money-display');
    const scenarioTitle = document.getElementById('scenario-title');
    const storyText = document.getElementById('story-text');
    const choicesContainer = document.getElementById('choices-container');
    const nextYearContainer = document.getElementById('next-year-container');
    const nextYearButton = document.getElementById('next-year-button');
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    const scorecardModal = document.getElementById('scorecard-modal');
    const historyButton = document.getElementById('history-button');
    const historyDropdown = document.getElementById('history-dropdown');

    // --- UI HELPERS ---
    function showLoader() { loader.classList.remove('hidden'); }
    function hideLoader() { loader.classList.add('hidden'); }

    function updateStatusUI(playerState) {
        if (!playerState) return;
        if (playerState.age) ageDisplay.textContent = `Age: ${playerState.age}`;
        if (playerState.hasOwnProperty('balance')) {
            moneyDisplay.textContent = `$${Math.round(playerState.balance).toLocaleString()}`;
        }
    }

    function renderEvent(event) {
        if (!event || event.error) {
            scenarioTitle.textContent = "An AI Error Occurred";
            storyText.textContent = `Problem generating the next event: ${event?.error || 'Unknown error'}. Try advancing a year.`;
            choicesContainer.innerHTML = '';
            choicesContainer.classList.add('hidden');
            nextYearContainer.classList.remove('hidden');
            return;
        }

        scenarioTitle.textContent = event.scenario_title;
        storyText.textContent = event.scenario_description;
        choicesContainer.innerHTML = '';

        event.choices.forEach(choice => {
            const button = document.createElement('button');
            button.textContent = choice.description;
            button.onclick = () => handleChoiceClick(choice);
            choicesContainer.appendChild(button);
        });

        choicesContainer.classList.remove('hidden');
        nextYearContainer.classList.add('hidden');
    }

    function showScorecard(summary) {
        document.getElementById('persona-title').textContent = summary.persona_title || "Analysis Complete";
        document.getElementById('summary-text').textContent = summary.summary || "No summary generated.";
        document.getElementById('best-decisions').innerHTML = Array.isArray(summary.best_decision)
            ? summary.best_decision.join('<br>') : summary.best_decision;
        document.getElementById('worst-decisions').innerHTML = Array.isArray(summary.worst_decision)
            ? summary.worst_decision.join('<br>') : summary.worst_decision;

        scorecardModal.classList.remove('hidden');
        document.getElementById('restart-button').onclick = () => window.location.reload();
    }

    function recalculateBalanceFromTransactions() {
        let balance = 5000;
        for (const tx of transactionLog) {
            if (tx.type === 'deposit') {
                balance += tx.amount;
            } else if (tx.type === 'withdrawal') {
                balance -= tx.amount;
            }
        }
        moneyDisplay.textContent = `$${Math.round(balance).toLocaleString()}`;
    }

    async function updateTransactionLogAndBalance() {
        try {
            const response = await fetch(`${API_BASE_URL}/game/history`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gameId })
            });
            const data = await response.json();
            transactionLog = data.transaction_history || [];
            recalculateBalanceFromTransactions();
        } catch (error) {
            console.error("Failed to fetch transaction log:", error);
        }
    }

    async function handleChoiceClick(choice) {
        showLoader();
        choicesContainer.innerHTML = '';

        const endpoint = choice.financial_impact.hasOwnProperty('action') ? '/decision/mcq' : '/decision/job';

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gameId, choice })
            });

            const data = await response.json();
            if (!response.ok || data.error) throw new Error(data.error || `Server error: ${response.status}`);

            scenarioTitle.textContent = "Decision Made";
            storyText.textContent = `You decided: ${choice.description}`;

            if (data.playerState) {
                updateStatusUI(data.playerState);
            }

            // --- NEW: Update transaction log & balance manually
            await updateTransactionLogAndBalance();

        } catch (error) {
            console.error("handleChoiceClick Error:", error);
            alert(`Error processing decision: ${error.message}`);
        } finally {
            hideLoader();
            choicesContainer.classList.add('hidden');
            nextYearContainer.classList.remove('hidden');
        }
    }

    nextYearButton.addEventListener('click', async () => {
        showLoader();
        try {
            const response = await fetch(`${API_BASE_URL}/game/advance-year`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gameId })
            });

            const data = await response.json();
            if (!response.ok || data.error) throw new Error(data.error || `Server error: ${response.status}`);

            if (data.gameOver) {
                showScorecard(data.finalSummary);
            } else {
                updateStatusUI(data.playerState);
                renderEvent(data.nextEvent);
                await updateTransactionLogAndBalance();
            }

        } catch (error) {
            console.error("advance-year Error:", error);
            scenarioTitle.textContent = "Error Advancing Year";
            storyText.textContent = `Error: ${error.message}. Could not advance.`;
        } finally {
            hideLoader();
        }
    });

    historyButton.addEventListener('click', async () => {
        const isVisible = historyDropdown.classList.toggle('show');
        if (!isVisible) return;

        historyDropdown.innerHTML = '<li>Loading...</li>';

        try {
            const response = await fetch(`${API_BASE_URL}/game/history`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gameId })
            });
            const data = await response.json();

            transactionLog = data.transaction_history || [];
            historyDropdown.innerHTML = '';

            if (transactionLog.length > 0) {
                transactionLog.forEach(item => {
                    const li = document.createElement('li');
                    const amountText = item.type === 'deposit'
                        ? `(+\$${Math.round(item.amount).toLocaleString()})`
                        : `(-\$${Math.round(item.amount).toLocaleString()})`;
                    li.innerHTML = `<strong>${item.transaction_date}</strong>: ${item.description || item.type} <span>${amountText}</span>`;
                    historyDropdown.appendChild(li);
                });
            } else {
                historyDropdown.innerHTML = '<li>No transactions yet.</li>';
            }

            recalculateBalanceFromTransactions();

        } catch (error) {
            console.error("Failed to load history:", error);
            historyDropdown.innerHTML = '<li>Error loading history</li>';
        }
    });

    // --- START GAME ---
    startButton.addEventListener('click', async () => {
        const firstName = firstNameInput.value.trim();
        const lastName = lastNameInput.value.trim();

        if (!firstName || !lastName) {
            alert("Please enter a first and last name.");
            return;
        }

        showLoader();
        startScreen.classList.add('hidden');
        gameContent.classList.remove('hidden');

        try {
            const response = await fetch(`${API_BASE_URL}/game/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ firstName, lastName })
            });

            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const data = await response.json();
            gameId = data.gameId;
            updateStatusUI(data.playerState);

            nextYearButton.click();

        } catch (error) {
            hideLoader();
            console.error("Failed to start game:", error);
            alert("Could not start the game. Make sure the backend is running.");
        }
    });
});
