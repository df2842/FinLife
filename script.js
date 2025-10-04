document.addEventListener('DOMContentLoaded', () => {
    // Ensure this port matches the port in your app.py file
    const API_BASE_URL = 'http://127.0.0.1:5000';
    let gameId = null;
  
    // --- DOM ELEMENT SELECTION ---
    const loader = document.getElementById('loader');
    const instructionScreen = document.getElementById('instruction-screen');
    const startButton = document.getElementById('start-button');
    const gameContainer = document.getElementById('game-container');
    const gameContent = document.getElementById('game-content');
    const ageDisplay = document.getElementById('age-display');
    const moneyDisplay = document.getElementById('money-display');
    const storyText = document.getElementById('story-text');
    const choicesContainer = document.getElementById('choices-container');
    const nextYearContainer = document.getElementById('next-year-container');
    const nextYearButton = document.getElementById('next-year-button');
    const firstNameInput = document.getElementById('firstName');
    const lastNameInput = document.getElementById('lastName');
    const scorecardModal = document.getElementById('scorecard-modal');
  
    // --- UI FUNCTIONS ---
    function updateStatusUI(playerState) {
      ageDisplay.textContent = `Age: ${playerState.age}`;
      moneyDisplay.textContent = `$${Math.round(playerState.balance)}`;
    }
  
    function renderEvent(event) {
      if (!event || event.error) {
        storyText.textContent = `An AI error occurred: ${event.error || 'Unknown error'}. Please try advancing a year.`;
        choicesContainer.innerHTML = '';
        choicesContainer.classList.add('hidden');
        nextYearContainer.classList.remove('hidden');
        return;
      }
  
      storyText.textContent = event.scenario_description;
      choicesContainer.innerHTML = '';
  
      event.choices.forEach(choice => {
        const button = document.createElement('button');
        button.textContent = choice.description;
        const eventType = event.scenario_title.toLowerCase().includes("opportunity") ? 'job' : 'mcq';
        button.onclick = () => handleChoiceClick(choice, eventType);
        choicesContainer.appendChild(button);
      });
  
      choicesContainer.classList.remove('hidden');
      nextYearContainer.classList.add('hidden');
    }
  
    function showScorecard(summary) {
      if (!summary || summary.error) {
        scorecardModal.innerHTML = `
          <h2>Analysis Error</h2>
          <p>There was a problem generating your final financial summary. This can happen if the AI service is busy. Please try again.</p>
          <p>Error: ${summary ? summary.error : 'Unknown issue.'}</p>
          <button id="restart-button">Play Again</button>`;
      } else {
        scorecardModal.innerHTML = `
          <h2>${summary.persona_title}</h2>
          <p>${summary.summary}</p>
          <div class="decision-box">
            <h3>Best Decisions</h3>
            <p>${summary.best_decision}</p>
          </div>
          <div class="decision-box">
            <h3>Worst Decisions</h3>
            <p>${summary.worst_decision}</p>
          </div>
          <button id="restart-button">Play Again</button>`;
      }
  
      scorecardModal.classList.remove('hidden');
      document.getElementById('restart-button').onclick = () => window.location.reload();
    }
  
    // --- EVENT HANDLERS ---
    async function handleChoiceClick(choice, eventType) {
      choicesContainer.innerHTML = '<p>Processing decision...</p>';
      const endpoint = `/decision/${eventType}`;
  
      await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gameId: gameId, choice: choice })
      });
  
      const stateResponse = await fetch(`${API_BASE_URL}/game/state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gameId: gameId })
      });
  
      const data = await stateResponse.json();
      updateStatusUI(data.playerState);
  
      choicesContainer.classList.add('hidden');
      nextYearContainer.classList.remove('hidden');
    }
  
    nextYearButton.addEventListener('click', async () => {
      nextYearContainer.querySelector('button').textContent = 'Advancing...';
  
      const response = await fetch(`${API_BASE_URL}/game/advance-year`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gameId: gameId })
      });
  
      const data = await response.json();
      nextYearContainer.querySelector('button').textContent = 'Advance to Next Year';
  
      if (data.gameOver) {
        showScorecard(data.finalSummary);
      } else {
        updateStatusUI(data.playerState);
        renderEvent(data.nextEvent);
      }
    });
  
    // --- START GAME FUNCTION ---
    async function startGame() {
      const initialGameState = await getInitialGameState();
      updateGameUI(initialGameState);
    }
  
    // --- MAIN APPLICATION FLOW ---
  
    // 1. Handle the initial loading screen -> instruction screen transition
    window.addEventListener('load', () => {
      loader.classList.add('loader--hidden');
      instructionScreen.classList.remove('hidden');
    });
  
    // 2. Handle the instruction screen -> game screen transition
    instructionScreen.addEventListener('click', async () => {
      const defaultUserData = {
        firstName: "Player",
        lastName: "One"
      };
  
      instructionScreen.classList.add('loader--hidden');
      gameContent.classList.remove('hidden');
  
      try {
        const response = await fetch(`${API_BASE_URL}/game/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(defaultUserData)
        });
  
        if (!response.ok) {
          throw new Error(`Server responded with an error: ${response.status}`);
        }
  
        const data = await response.json();
        gameId = data.gameId;
        updateStatusUI(data.playerState);
        renderEvent(data.nextEvent);
      } catch (error) {
        console.error("Failed to start game:", error);
        alert("Could not start the game. Please make sure the backend server is running correctly.");
      }
    }, { once: true });
  });
  
