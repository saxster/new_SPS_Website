import { useState } from 'preact/hooks';
import type { Scenario, State } from '../../data/simulations/scenarios';
import './CrisisSimulator.css';

interface Props {
    scenario: Scenario;
}

export default function CrisisSimulator({ scenario }: Props) {
    const [currentStateId, setCurrentStateId] = useState(scenario.initialState);
    const [history, setHistory] = useState<string[]>([]);
    const [started, setStarted] = useState(false);

    const currentState = scenario.states[currentStateId];

    const handleChoice = (nextStateId: string) => {
        setHistory([...history, currentStateId]);
        setCurrentStateId(nextStateId);
    };

    const handleRestart = () => {
        setCurrentStateId(scenario.initialState);
        setHistory([]);
        setStarted(false);
    };

    if (!started) {
        return (
            <div class="simulator-start-card fade-in">
                <div class="sim-header">
                    <span class="sim-badge">{scenario.difficulty} LEVEL</span>
                    <span class="sim-sector">{scenario.sector.toUpperCase()}</span>
                </div>
                <h2 class="sim-title">{scenario.title}</h2>
                <p class="sim-desc">{scenario.description}</p>
                <button class="brutalist-button brutalist-button--primary w-full" onClick={() => setStarted(true)}>
                    INITIATE DRILL
                </button>
            </div>
        );
    }

    const isTerminal = currentState.isTerminal;
    const outcomeClass = currentState.outcome === 'success' ? 'outcome-success' : 
                         currentState.outcome === 'failure' ? 'outcome-failure' : 'outcome-partial';

    return (
        <div class="simulator-container fade-in">
            <div class="sim-status-bar">
                <span class="status-indicator status-pulse"></span>
                <span>LIVE SIMULATION // {scenario.title.toUpperCase()}</span>
            </div>

            <div class="sim-content">
                <p class="narrative-text whitespace-pre-line">{currentState.text}</p>
            </div>

            {!isTerminal ? (
                <div class="sim-choices">
                    {currentState.choices.map(choice => (
                        <button 
                            key={choice.id} 
                            class="choice-btn"
                            onClick={() => handleChoice(choice.nextState)}
                        >
                            <span class="choice-arrow">→</span>
                            {choice.text}
                        </button>
                    ))}
                </div>
            ) : (
                <div class={`sim-outcome ${outcomeClass}`}>
                    <h3 class="outcome-title">
                        {currentState.outcome === 'success' ? 'MISSION ACCOMPLISHED' : 
                         currentState.outcome === 'failure' ? 'CRITICAL FAILURE' : 'PARTIAL SUCCESS'}
                    </h3>
                    <button class="brutalist-button brutalist-button--secondary mt-4" onClick={handleRestart}>
                        REBOOT SIMULATION
                    </button>
                </div>
            )}
        </div>
    );
}
