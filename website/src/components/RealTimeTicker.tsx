import { useState, useEffect, useRef } from 'preact/hooks';

export default function RealTimeTicker() {
    const [alerts, setAlerts] = useState<string[]>(["SYSTEM ONLINE. LISTENING FOR SIGNALS..."]);
    const ws = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Connect to the Signal Tower
        // In production, use wss:// and the real domain
        const socketUrl = import.meta.env.PUBLIC_WS_URL || 'ws://localhost:8000/ws';
        ws.current = new WebSocket(socketUrl);

        ws.current.onopen = () => {
            console.log('[SIGNAL TOWER] Connected');
            setAlerts(["SIGNAL TOWER: CONNECTED"]);
        };

        ws.current.onmessage = (event) => {
            try {
                // Determine if it's JSON or text
                if (event.data.startsWith('{')) {
                    const data = JSON.parse(event.data);
                    const timestamp = new Date().toLocaleTimeString();
                    const newAlert = `${timestamp} • [${data.severity.toUpperCase()}] ${data.title}`;
                    
                    setAlerts(prev => [newAlert, ...prev].slice(0, 5));
                }
            } catch (e) {
                console.error('Signal Parse Error:', e);
            }
        };

        ws.current.onclose = () => {
            console.log('[SIGNAL TOWER] Disconnected');
            setAlerts(prev => ["SIGNAL LOST. RECONNECTING...", ...prev]);
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    return (
        <div id="ticker-track" class="whitespace-nowrap flex items-center animate-ticker hover:paused">
            {alerts.map((alert, i) => (
                <div key={i} class="inline-flex items-center mx-8">
                    <span class={`w-2 h-2 rounded-full mr-3 animate-pulse ${alert.includes('CRITICAL') ? 'bg-red-500' : 'bg-primary-accent'}`}></span>
                    <span class="text-xs font-mono text-neutral-400 uppercase tracking-wider">
                        {alert}
                    </span>
                </div>
            ))}
        </div>
    );
}
