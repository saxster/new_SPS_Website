import { useState, useEffect, useRef } from 'preact/hooks';
import { useSectorPreference } from '../../hooks/useSectorPreference';
import { sanitizeAndFormatMessage } from '../../utils/sanitize';
import './AskExpertWidget.css';

interface Message {
    id: string;
    text: string;
    sender: 'user' | 'expert';
    timestamp: Date;
}

export default function AskExpertWidget() {
    const { preferredSector } = useSectorPreference();
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'init',
            text: "**SPS COMMANDER ONLINE.**\n\nSecure channel established. I am authorized to provide guidance on physical security, compliance (PSARA/NBC), and risk management.\n\n*Note: All communications are logged for quality assurance.*",
            sender: 'expert',
            timestamp: new Date()
        }
    ]);
    const [isTyping, setIsTyping] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    const toggleOpen = () => setIsOpen(!isOpen);

    const handleSubmit = async (e: Event) => {
        e.preventDefault();
        if (!query.trim() || isTyping) return;

        const userQuery = query;
        const userMsg: Message = {
            id: Date.now().toString(),
            text: userQuery,
            sender: 'user',
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setQuery('');
        setIsTyping(true);
        setError(null);

        try {
            const response = await fetch('/api/ask-expert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query: userQuery,
                    user_context: { sector: preferredSector }
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to get response');
            }

            const expertMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: data.response,
                sender: 'expert',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, expertMsg]);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Connection error.');
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: `**System Error:** ${err instanceof Error ? err.message : 'Transmission failed. Secure line unstable.'}`,
                sender: 'expert',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsTyping(false);
        }
    };

    // Scroll to bottom
    useEffect(() => {
        if (bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isOpen]);

    return (
        <div class="expert-widget-container">
            {!isOpen && (
                <button
                    class="expert-trigger"
                    onClick={toggleOpen}
                    aria-label="Open AI Expert Chat"
                    aria-expanded="false"
                >
                    <span class="status-dot"></span> ASK COMMANDER
                </button>
            )}

            {isOpen && (
                <div
                    class="expert-panel"
                    role="dialog"
                    aria-label="SPS AI Commander Chat"
                    aria-modal="true"
                >
                    <div class="expert-header">
                        <div class="header-title">
                            <span class="icon">🛡️</span> COMMANDER
                            <span class="ai-badge">AI</span>
                        </div>
                        <button
                            class="close-btn"
                            onClick={toggleOpen}
                            aria-label="Close chat"
                        >
                            ×
                        </button>
                    </div>
                    <div class="expert-body" role="log" aria-live="polite">
                        {messages.map(m => (
                            <div key={m.id} class={`message ${m.sender}`}>
                                <div
                                    class="msg-content"
                                    dangerouslySetInnerHTML={{__html: sanitizeAndFormatMessage(m.text)}}
                                />
                                <div class="msg-time">
                                    {m.timestamp.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        ))}
                        {isTyping && (
                            <div class="message expert typing">
                                <span class="typing-indicator">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </span>
                                DECRYPTING...
                            </div>
                        )}
                        <div ref={bottomRef} />
                    </div>
                    <form class="expert-input" onSubmit={handleSubmit}>
                        <input
                            type="text"
                            value={query}
                            onInput={(e) => setQuery(e.currentTarget.value)}
                            placeholder="Ask for security protocols..."
                            autoFocus
                            disabled={isTyping}
                            maxLength={1000}
                            aria-label="Type your security question"
                        />
                        <button
                            type="submit"
                            disabled={isTyping || !query.trim()}
                            aria-label="Send message"
                        >
                            {isTyping ? '...' : 'SEND'}
                        </button>
                    </form>
                    <div class="expert-disclaimer">
                        SPS Commander Alpha. Operational guidance only.
                    </div>
                </div>
            )}
        </div>
    );
}
