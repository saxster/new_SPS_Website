import { useState, useEffect } from 'preact/hooks';

interface Sector {
  slug: string;
  name: string;
  icon: string;
}

interface Props {
  sectors: Sector[];
}

export default function SectorPreferences({ sectors }: Props) {
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    // Fetch user's current sector preferences
    fetch('/api/user/preferences')
      .then(res => res.ok ? res.json() : { sectors: [] })
      .then(data => {
        setSelectedSectors(data.sectors || []);
        setLoading(false);
      })
      .catch(() => {
        setSelectedSectors([]);
        setLoading(false);
      });
  }, []);

  const toggleSector = (slug: string) => {
    setSelectedSectors(prev =>
      prev.includes(slug)
        ? prev.filter(s => s !== slug)
        : [...prev, slug]
    );
    setSaved(false);
  };

  const savePreferences = async () => {
    setSaving(true);
    try {
      const res = await fetch('/api/user/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sectors: selectedSectors }),
      });

      if (res.ok) {
        setSaved(true);
        // Trigger refresh of threat briefing
        window.dispatchEvent(new CustomEvent('sectors-updated'));
      }
    } catch (err) {
      console.error('Failed to save preferences:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div class="bg-neutral-900 border-2 border-neutral-800 p-6">
        <div class="animate-pulse space-y-3">
          <div class="h-4 bg-neutral-800 rounded w-1/2"></div>
          <div class="space-y-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} class="h-8 bg-neutral-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div class="bg-neutral-900 border-2 border-neutral-800">
      <div class="p-4 border-b-2 border-neutral-800">
        <h3 class="text-sm font-bold text-neutral-400 uppercase tracking-wider">
          Tracked Sectors
        </h3>
        <p class="text-xs text-neutral-600 mt-1">
          Select sectors to personalize your briefing
        </p>
      </div>

      <div class="p-4 space-y-2 max-h-64 overflow-y-auto">
        {sectors.map(sector => (
          <button
            key={sector.slug}
            onClick={() => toggleSector(sector.slug)}
            class={`w-full flex items-center gap-3 p-3 border-2 transition-all text-left ${
              selectedSectors.includes(sector.slug)
                ? 'bg-primary-accent/10 border-primary-accent text-primary-accent'
                : 'border-neutral-700 hover:border-neutral-600 text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <div class={`w-6 h-6 flex items-center justify-center border ${
              selectedSectors.includes(sector.slug)
                ? 'border-primary-accent bg-primary-accent text-black'
                : 'border-neutral-600'
            }`}>
              {selectedSectors.includes(sector.slug) && (
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <span class="text-sm font-medium">{sector.name}</span>
          </button>
        ))}
      </div>

      <div class="p-4 border-t-2 border-neutral-800 flex items-center justify-between">
        <span class="text-xs text-neutral-500 font-mono">
          {selectedSectors.length} SELECTED
        </span>
        <button
          onClick={savePreferences}
          disabled={saving}
          class={`px-4 py-2 text-xs font-bold uppercase tracking-wider transition-all ${
            saved
              ? 'bg-green-900/30 text-green-400 border border-green-500/30'
              : 'bg-primary-accent text-black hover:bg-primary-accent/80'
          }`}
        >
          {saving ? 'SAVING...' : saved ? 'SAVED' : 'SAVE'}
        </button>
      </div>
    </div>
  );
}
