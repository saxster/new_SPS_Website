import { useState } from 'preact/hooks';

export default function CommandSearch() {
    const [query, setQuery] = useState('');
    const [answer, setAnswer] = useState('');
    const [loading, setLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);

    const handleAsk = async (e: Event) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setAnswer(''); // Clear previous

        try {
            const res = await fetch('/api/ask-commander', { // We'll create this proxy
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            setAnswer(data.answer);
        } catch (e) {
            setAnswer("COMM LINK FAILURE. RETRY.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Trigger Button */}
            <button 
                onClick={() => setIsOpen(true)}
                class="fixed bottom-8 right-8 z-50 w-14 h-14 bg-primary-accent rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(0,255,65,0.3)] hover:scale-110 transition-transform group"
            >
                <span class="text-2xl group-hover:animate-pulse">💬</span>
            </button>

            {/* Chat Overlay */}
            {isOpen && (
                <div class="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
                    <div class="w-full max-w-2xl bg-neutral-900 border border-primary-accent/30 rounded-lg shadow-2xl overflow-hidden flex flex-col max-h-[80vh]">
                        {/* Header */}
                        <div class="p-4 border-b border-neutral-800 flex justify-between items-center bg-black">
                            <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                                <span class="w-2 h-2 bg-primary-accent rounded-full animate-pulse"></span>
                                Ask The Commander
                            </h3>
                            <button onClick={() => setIsOpen(false)} class="text-neutral-500 hover:text-white">✕</button>
                        </div>

                        {/* Output Area */}
                        <div class="flex-1 p-6 overflow-y-auto font-mono text-sm bg-black/50 min-h-[300px]">
                            {!answer && !loading && (
                                <p class="text-neutral-600 text-center mt-20">
                                    // SECURITY CLEARANCE: ALPHA<br/>
                                    // ACCESSING KNOWLEDGE VAULT...<br/>
                                    // WAITING FOR QUERY.
                                </p>
                            )}
                            
                            {loading && (
                                <div class="text-primary-accent animate-pulse">
                                    {'>'} ANALYZING VECTOR EMBEDDINGS...<br/>
                                    {'>'} SYNTHESIZING INTELLIGENCE...
                                </div>
                            )}

                            {answer && (
                                <div class="prose prose-invert prose-sm max-w-none">
                                    <p class="text-primary-accent mb-2">{'>'} RESPONSE RECEIVED:</p>
                                    <div class="text-gray-300 leading-relaxed whitespace-pre-wrap">{answer}</div>
                                </div>
                            )}
                        </div>

                        {/* Input Area */}
                        <form onSubmit={handleAsk} class="p-4 border-t border-neutral-800 bg-neutral-900 flex gap-4">
                            <input 
                                type="text" 
                                value={query}
                                onInput={(e) => setQuery(e.currentTarget.value)}
                                placeholder="E.g., 'What are the risks for ATMs in Mumbai?'"
                                class="flex-1 bg-black border border-neutral-700 text-white px-4 py-3 rounded focus:border-primary-accent focus:outline-none font-mono text-sm"
                            />
                            <button 
                                type="submit" 
                                disabled={loading}
                                class="px-6 py-3 bg-primary-accent text-black font-bold uppercase tracking-wider hover:bg-white transition-colors disabled:opacity-50"
                            >
                                SEND
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
}
