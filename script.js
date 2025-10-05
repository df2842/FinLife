document.addEventListener('DOMContentLoaded', () => {
    // CRITICAL FIX: Ensure this port matches the port in your app.py file
    const API_BASE_URL = 'http://127.0.0.1:5000';
    let gameId = null;

    // --- DOM ELEMENT SELECTION ---
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
    const jumpAgeInput = document.getElementById('jump-age-input');
    const jumpButton = document.getElementById('jump-button');
    const historyButton = document.getElementById('history-button');
    const historyDropdown = document.getElementById('history-dropdown');

    // --- UI HELPER FUNCTIONS ---
    function showLoader() { loader.classList.remove('hidden'); }
    function hideLoader() { loader.classList.add('hidden'); }

    function updateStatusUI(playerState) {
        ageDisplay.textContent = `Age: ${playerState.age}`;
        // Use toLocaleString for better number formatting (e.g., $50,000)
        moneyDisplay.textContent = `$${Math.round(playerState.balance).toLocaleString()}`;
    }

    function renderEvent(event) {
        if (!event || event.error) {
            scenarioTitle.textContent = "An AI Error Occurred";
            storyText.textContent = `There was a problem generating the next event: ${event ? event.error : 'Unknown error'}. Please try advancing a year.`;
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
            // Check for 'action' (MCQ) or 'income' (Job) to determine event type
            button.onclick = () => handleChoiceClick(choice);
            choicesContainer.appendChild(button);
        });

        choicesContainer.classList.remove('hidden');
        nextYearContainer.classList.add('hidden');
    }

    function showScorecard(summary) {
        document.getElementById('persona-title').textContent = summary.persona_title || "Analysis Complete";
        document.getElementById('summary-text').textContent = summary.summary || "Could not generate summary.";
        // Assuming best_decision and worst_decision are arrays of strings
        document.getElementById('best-decisions').innerHTML = Array.isArray(summary.best_decision)
            ? summary.best_decision.join('<br>') : summary.best_decision;
        document.getElementById('worst-decisions').innerHTML = Array.isArray(summary.worst_decision)
            ? summary.worst_decision.join('<br>') : summary.worst_decision;

        scorecardModal.classList.remove('hidden');
        document.getElementById('restart-button').onclick = () => window.location.reload();
    }

    // --- API & EVENT HANDLERS ---
    async function handleChoiceClick(choice) {
        showLoader();
        choicesContainer.innerHTML = '';

        // Determine endpoint by checking for a unique key in the financial_impact
        const endpoint = choice.financial_impact.hasOwnProperty('action') ? '/decision/mcq' : '/decision/job';

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gameId, choice })
        });

        const data = await response.json();

        // Check for and log any errors from the backend decision processing
        if (!response.ok || data.error) {
            console.error("Decision Error:", data.error || `Server error: ${response.status}`);
            alert(`Error processing decision: ${data.error || 'Check console for server status.'}`);
            hideLoader();
            choicesContainer.classList.add('hidden');
            nextYearContainer.classList.remove('hidden');
            return;
        }

        // FIX FOR BALANCE LAG: Use the playerState returned directly from the decision endpoint
        updateStatusUI(data.playerState);

        // Show the chosen option in the story panel
        scenarioTitle.textContent = "Decision Made";
        storyText.textContent = `You decided: ${choice.description}`;

        hideLoader();
        choicesContainer.classList.add('hidden');
        nextYearContainer.classList.remove('hidden');
    }

    nextYearButton.addEventListener('click', async () => {
        showLoader();
        const response = await fetch(`${API_BASE_URL}/game/advance-year`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gameId })
        });
        const data = await response.json();
        hideLoader();

        if (data.gameOver) {
            showScorecard(data.finalSummary);
        } else if (!response.ok || data.error) {
            // Handle critical errors during year advance
            scenarioTitle.textContent = "Error Advancing Year";
            storyText.textContent = `Error: ${data.error}. The game could not advance. Check the console.`;
            choicesContainer.innerHTML = '';
            choicesContainer.classList.add('hidden');
            nextYearContainer.classList.remove('hidden');
        } else {
            updateStatusUI(data.playerState);
            renderEvent(data.nextEvent);
        }
    });

    historyButton.addEventListener('click', async () => {
        // Toggle visibility
        const isVisible = historyDropdown.classList.toggle('show');
        if (!isVisible) return; // Hide if already shown

        historyDropdown.innerHTML = '<li>Loading...</li>';
        const response = await fetch(`${API_BASE_URL}/game/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ gameId })
        });
        const data = await response.json();
        historyDropdown.innerHTML = '';

        if (data.transaction_history && data.transaction_history.length > 0) {
            data.transaction_history.forEach(item => {
                const li = document.createElement('li');
                // Format the transaction type and amount
                const amountText = item.type === 'deposit' ? `(+$${Math.round(item.amount).toLocaleString()})`
                                  : `(-$${Math.round(item.amount).toLocaleString()})`;
                li.innerHTML = `<strong>${item.transaction_date}</strong>: ${item.description || item.type} <span>${amountText}</span>`;
                historyDropdown.appendChild(li);
            });
        } else {
            historyDropdown.innerHTML = '<li>No transactions yet.</li>';
        }
    });

    // --- MAIN GAME START ---
    startButton.addEventListener('click', async () => {
        const firstName = firstNameInput.value;
        const lastName = lastNameInput.value;

        if (!firstName || !lastName) {
            alert("Please enter a first and last name.");
            return;
        }

        showLoader();
        startScreen.classList.add('hidden');
        gameContent.classList.remove('hidden');

        try {
            // 1. Start the game
            const response = await fetch(`${API_BASE_URL}/game/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ firstName, lastName })
            });

            if (!response.ok) throw new Error(`Server error: ${response.status}`);

            const data = await response.json();
            gameId = data.gameId;
            updateStatusUI(data.playerState);

            // 2. Immediately advance to the first year (age 17) to get the first event
            nextYearButton.click();

        } catch (error) {
            hideLoader();
            console.error("Failed to start game:", error);
            alert("Could not start the game. Please make sure the backend server is running correctly (check console for error).");
        }
    });
});