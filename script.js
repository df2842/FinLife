document.addEventListener('DOMContentLoaded', () => {

    const loader = document.getElementById('loader');
    const instructionScreen = document.getElementById('instruction-screen');
    instructionScreen.addEventListener('click', () => {
    // The code inside here stays exactly the same
    instructionScreen.classList.add('loader--hidden');
    gameContent.classList.remove('hidden');
    startGame();
   });
    const gameContent = document.getElementById('game-content'); // Get the new wrapper
    const ageDisplay = document.getElementById('age-display');
    const moneyDisplay = document.getElementById('money-display');
    const storyText = document.getElementById('story-text');
    const choicesContainer = document.getElementById('choices-container');

    const mockApiData = {
        scenarios: {
            start: {
                text: "You are 16 years old. Summer has just begun. What do you do?",
                choices: [ { id: 'job', text: 'Get a summer job (+$1,200)' }, { id: 'camp', text: 'Go to a coding camp (-$500)' }, { id: 'relax', text: 'Relax at home (+$0)' } ]
            },
            after_summer: {
                text: "You are now 18. It's time to make a big decision. What path will you choose?",
                choices: [ { id: 'college', text: 'Go to college (-$40,000 Loan)' }, { id: 'army', text: 'Join the army (+$20,000 Signing Bonus)' } ]
            }
        }
    };
    let mockPlayerState = { age: 16, money: 500 };

    async function getInitialGameState() { return { ...mockPlayerState, scenario: mockApiData.scenarios.start }; }
    async function postChoiceToServer(choiceId) {
        if (choiceId === 'job') mockPlayerState.money += 1200;
        if (choiceId === 'camp') mockPlayerState.money -= 500;
        mockPlayerState.age = 18;
        return { ...mockPlayerState, scenario: mockApiData.scenarios.after_summer };
    }

    function updateGameUI(gameState) {
        ageDisplay.textContent = `Age: ${gameState.age}`;
        moneyDisplay.textContent = `$${gameState.money}`;
        storyText.textContent = gameState.scenario.text;
        choicesContainer.innerHTML = '';
        gameState.scenario.choices.forEach(choice => {
            const button = document.createElement('button');
            button.textContent = choice.text;
            button.dataset.choiceId = choice.id;
            button.addEventListener('click', handleChoiceClick);
            choicesContainer.appendChild(button);
        });
    }

    async function handleChoiceClick(event) {
        const choiceId = event.target.dataset.choiceId;
        choicesContainer.innerHTML = '<p>Loading...</p>';
        const newGameState = await postChoiceToServer(choiceId);
        updateGameUI(newGameState);
    }

    async function startGame() {
        const initialGameState = await getInitialGameState();
        updateGameUI(initialGameState);
    }

    // --- MAIN APPLICATION FLOW ---
    window.addEventListener('load', () => {
        loader.classList.add('loader--hidden');
        instructionScreen.classList.remove('hidden');
    });

    startButton.addEventListener('click', () => {
        instructionScreen.classList.add('loader--hidden');
        gameContent.classList.remove('hidden'); // Show the game content
        startGame();
    });
});