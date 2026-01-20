import { useState } from 'preact/hooks';

interface Sector {
  slug: string;
  name: string;
}

interface Props {
  sectors: Sector[];
  compact?: boolean;
}

export default function AlertSubscription({ sectors, compact = false }: Props) {
  const [email, setEmail] = useState('');
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [frequency, setFrequency] = useState<'instant' | 'daily' | 'weekly'>('instant');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSectors, setShowSectors] = useState(false);

  const toggleSector = (slug: string) => {
    setSelectedSectors(prev =>
      prev.includes(slug)
        ? prev.filter(s => s !== slug)
        : [...prev, slug]
    );
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    if (!email.trim() || selectedSectors.length === 0) {
      setError('Email and at least one sector required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/alerts/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          sectors: selectedSectors,
          frequency,
          channels: ['email'],
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Subscription failed');
      }

      setSuccess(true);
      setEmail('');
      setSelectedSectors([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div class={`bg-green-900/20 border-2 border-green-500/30 ${compact ? 'p-4' : 'p-6'}`}>
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <div>
            <p class="font-bold text-green-400">SUBSCRIPTION CONFIRMED</p>
            <p class="text-sm text-neutral-400 mt-1">
              Check your email to verify your subscription.
            </p>
          </div>
        </div>
        <button
          onClick={() => setSuccess(false)}
          class="mt-4 text-sm text-neutral-500 hover:text-neutral-300"
        >
          Subscribe another email
        </button>
      </div>
    );
  }

  return (
    <div class={`bg-neutral-900 border-2 border-neutral-800 ${compact ? 'p-4' : 'p-6'}`}>
      {!compact && (
        <div class="mb-6">
          <h3 class="text-lg font-bold text-primary-accent mb-2">
            SECURITY ALERTS
          </h3>
          <p class="text-sm text-neutral-400">
            Get real-time notifications for security incidents in your sectors.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} class="space-y-4">
        {/* Email Input */}
        <div>
          <label class="block text-xs text-neutral-500 uppercase tracking-wider mb-2">
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onInput={(e) => setEmail(e.currentTarget.value)}
            placeholder="you@example.com"
            class="w-full bg-neutral-800 border-2 border-neutral-700 px-4 py-3 text-neutral-200 placeholder-neutral-600 focus:border-primary-accent focus:outline-none font-mono"
            required
          />
        </div>

        {/* Sector Selection */}
        <div>
          <button
            type="button"
            onClick={() => setShowSectors(!showSectors)}
            class="flex items-center justify-between w-full bg-neutral-800 border-2 border-neutral-700 px-4 py-3 text-left hover:border-neutral-600"
          >
            <span class="text-sm">
              {selectedSectors.length === 0
                ? 'Select sectors to monitor...'
                : `${selectedSectors.length} sector${selectedSectors.length > 1 ? 's' : ''} selected`}
            </span>
            <svg
              class={`w-4 h-4 text-neutral-500 transition-transform ${showSectors ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showSectors && (
            <div class="mt-2 border-2 border-neutral-700 bg-neutral-800 max-h-48 overflow-y-auto">
              {sectors.map(sector => (
                <button
                  key={sector.slug}
                  type="button"
                  onClick={() => toggleSector(sector.slug)}
                  class={`w-full flex items-center gap-3 px-4 py-2 text-left text-sm transition-colors ${
                    selectedSectors.includes(sector.slug)
                      ? 'bg-primary-accent/10 text-primary-accent'
                      : 'hover:bg-neutral-700 text-neutral-300'
                  }`}
                >
                  <div class={`w-4 h-4 flex items-center justify-center border ${
                    selectedSectors.includes(sector.slug)
                      ? 'border-primary-accent bg-primary-accent text-black'
                      : 'border-neutral-600'
                  }`}>
                    {selectedSectors.includes(sector.slug) && (
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  {sector.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Frequency Selection */}
        {!compact && (
          <div>
            <label class="block text-xs text-neutral-500 uppercase tracking-wider mb-2">
              Alert Frequency
            </label>
            <div class="flex gap-2">
              {(['instant', 'daily', 'weekly'] as const).map(freq => (
                <button
                  key={freq}
                  type="button"
                  onClick={() => setFrequency(freq)}
                  class={`flex-1 py-2 px-3 text-xs font-bold uppercase tracking-wider transition-colors ${
                    frequency === freq
                      ? 'bg-primary-accent text-black'
                      : 'bg-neutral-800 border border-neutral-700 text-neutral-400 hover:border-neutral-600'
                  }`}
                >
                  {freq}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div class="text-sm text-red-400 bg-red-900/20 border border-red-500/30 px-4 py-2">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || selectedSectors.length === 0}
          class="w-full bg-primary-accent text-black py-3 font-bold uppercase tracking-wider hover:bg-primary-accent/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'SUBSCRIBING...' : 'SUBSCRIBE TO ALERTS'}
        </button>

        <p class="text-[10px] text-neutral-600 text-center">
          We respect your privacy. Unsubscribe anytime.
        </p>
      </form>
    </div>
  );
}
