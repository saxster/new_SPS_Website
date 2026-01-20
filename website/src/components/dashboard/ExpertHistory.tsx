import { useState, useEffect } from 'preact/hooks';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
  last_message_preview: string;
}

export default function ExpertHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/user/conversations')
      .then(res => res.ok ? res.json() : { conversations: [] })
      .then(data => {
        setConversations(data.conversations || []);
        setLoading(false);
      })
      .catch(() => {
        setConversations([]);
        setLoading(false);
      });
  }, []);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today ' + date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }
  };

  if (loading) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-6">
        <div class="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} class="h-20 bg-neutral-800 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-12 text-center">
        <svg class="w-16 h-16 mx-auto text-neutral-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <h3 class="text-lg font-bold text-neutral-400 mb-2">NO CONVERSATIONS YET</h3>
        <p class="text-sm text-neutral-600 mb-6">
          Start a conversation with the AI Expert to get security intelligence insights.
        </p>
        <a
          href="/"
          class="inline-flex items-center gap-2 bg-primary-accent text-black px-4 py-2 font-bold text-sm uppercase tracking-wider hover:bg-primary-accent/80 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Ask Expert
        </a>
      </div>
    );
  }

  return (
    <div class="bg-neutral-900 border-2 border-neutral-800">
      <div class="p-4 border-b-2 border-neutral-800 flex items-center justify-between">
        <span class="text-sm font-bold text-neutral-400 uppercase tracking-wider">
          {conversations.length} Conversation{conversations.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div class="divide-y divide-neutral-800">
        {conversations.map(conv => (
          <a
            key={conv.id}
            href={`/dashboard/conversations/${conv.id}`}
            class="block p-4 hover:bg-neutral-800/50 transition-colors group"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <svg class="w-4 h-4 text-primary-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  <h4 class="font-bold text-neutral-200 group-hover:text-primary-accent transition-colors truncate">
                    {conv.title}
                  </h4>
                </div>
                <p class="text-sm text-neutral-500 truncate">
                  {conv.last_message_preview}
                </p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-xs text-neutral-600 font-mono">
                  {formatDate(conv.created_at)}
                </p>
                <p class="text-xs text-neutral-700 mt-1">
                  {conv.message_count} messages
                </p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
