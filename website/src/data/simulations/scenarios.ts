export interface Choice {
    id: string;
    text: string;
    nextState: string;
    feedback?: string; // Immediate feedback on the choice
    delta?: {
        time?: number; // Time elapsed (minutes)
        assets?: number; // Asset health change
    };
}

export interface State {
    id: string;
    text: string; // The narrative
    image?: string; // Optional context image
    choices: Choice[];
    isTerminal?: boolean; // End of scenario?
    outcome?: 'success' | 'failure' | 'partial';
}

export interface Scenario {
    id: string;
    title: string;
    description: string;
    difficulty: 'Recruit' | 'Officer' | 'Commander';
    sector: string;
    initialState: string;
    states: Record<string, State>;
}

export const SCENARIO_WAREHOUSE_FIRE: Scenario = {
    id: "fire-001",
    title: "The Midnight Alarm",
    description: "It is 02:14 AM. The main warehouse smoke detectors have triggered. You are the Night Duty Officer. Protocol dictates immediate action.",
    difficulty: "Officer",
    sector: "Industrial",
    initialState: "start",
    states: {
        "start": {
            id: "start",
            text: "It is 02:14 AM. You are in the Command Centre. The main fire panel starts screaming. Zone 4 (Chemical Storage) is showing 'SMOKE DETECTED'.\n\nYour CCTV monitor for Zone 4 is black—camera feed lost. What is your immediate first action?",
            choices: [
                {
                    id: "c1",
                    text: "Silence the alarm to stop the panic and check the panel.",
                    nextState: "silence_fail",
                    delta: { time: 5, assets: -10 }
                },
                {
                    id: "c2",
                    text: "Radio the patrol guard to physically verify the fire.",
                    nextState: "radio_guard",
                    delta: { time: 2, assets: 0 }
                },
                {
                    id: "c3",
                    text: "Trigger the site-wide Evacuation Siren immediately.",
                    nextState: "evacuate_early",
                    delta: { time: 0, assets: 0 }
                }
            ]
        },
        "silence_fail": {
            id: "silence_fail",
            text: "CRITICAL MISTAKE. You silenced the alarm. The panel shows 'Zone 4' but the siren is off. You assume it's a false alarm because the camera is dead.\n\nTen minutes later, the heat creates a backdraft explosion that blows out the warehouse windows. The fire has now spread to the main office.",
            choices: [],
            isTerminal: true,
            outcome: "failure"
        },
        "radio_guard": {
            id: "radio_guard",
            text: "You radio Guard Singh. 'Singh, check Zone 4 immediately.'\n\nSingh responds: 'Sir, I smell burning plastic. Smoke is coming under the shutter.'\n\nNow what?",
            choices: [
                {
                    id: "c2a",
                    text: "Tell Singh to open the shutter and use a fire extinguisher.",
                    nextState: "guard_injury",
                    delta: { time: 5, assets: -50 }
                },
                {
                    id: "c2b",
                    text: "Call the Fire Brigade (101) and sound the Evacuation Siren.",
                    nextState: "call_101",
                    delta: { time: 1, assets: 0 }
                }
            ]
        },
        "guard_injury": {
            id: "guard_injury",
            text: "Singh opens the shutter. The sudden rush of oxygen causes a FLASHBACK. He is severely burned. The fire engulfs the entrance.\n\nNow you have a fire out of control AND a casualty. You failed to prioritize human life.",
            choices: [],
            isTerminal: true,
            outcome: "failure"
        },
        "evacuate_early": {
            id: "evacuate_early",
            text: "The siren wails. The night shift workers start pouring out. You haven't verified the fire yet, but safety comes first.\n\nYou radio the patrol guard, who confirms: 'Sir, Zone 4 is ablaze.'\n\nThe Fire Brigade is called. Because you evacuated early, the roll call is completed by the time the fire engines arrive.",
            choices: [
                {
                    id: "c3a",
                    text: "Direct the fire engine to the main gate.",
                    nextState: "gate_delay",
                    delta: { time: 10, assets: -20 }
                },
                {
                    id: "c3b",
                    text: "Send a guard to the main gate to guide the fire engine to the Zone 4 access road.",
                    nextState: "success_perfect",
                    delta: { time: 0, assets: 0 }
                }
            ]
        },
        "call_101": {
            id: "call_101",
            text: "You dial 101. 'Fire at Plot 44, Industrial Area.' You hit the siren. The workers evacuate.\n\nThe fire engines arrive in 15 minutes. The fire is contained to Zone 4.",
            choices: [],
            isTerminal: true,
            outcome: "success"
        },
        "gate_delay": {
            id: "gate_delay",
            text: "The fire engine arrives at the Main Gate, but the internal roads are confusing. They take a wrong turn towards the Admin block.\n\nBy the time they reach Zone 4, the roof has collapsed. The asset loss is 80%, but no lives lost.",
            choices: [],
            isTerminal: true,
            outcome: "partial"
        },
        "success_perfect": {
            id: "success_perfect",
            text: "PERFECT EXECUTION. The guard guides the Fire Tender directly to the Zone 4 hydrant. They deploy water curtains immediately.\n\nThe fire is extinguished with only 10% stock loss. No injuries. You followed the 'Life Safety First' protocol perfectly.",
            choices: [],
            isTerminal: true,
            outcome: "success"
        }
    }
};
