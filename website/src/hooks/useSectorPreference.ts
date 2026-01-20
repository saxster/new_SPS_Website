import { useState, useEffect } from 'preact/hooks';

export type Sector = 'jewellery' | 'corporate' | 'finance' | 'it_park' | 'residential' | 'industrial';

const STORAGE_KEY = 'sps_sector_preference';

export function useSectorPreference() {
    const [preferredSector, setPreferredSector] = useState<Sector | null>(null);

    // Initial load
    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY) as Sector;
        if (saved) {
            setPreferredSector(saved);
        }
    }, []);

    const setPreference = (sector: Sector) => {
        localStorage.setItem(STORAGE_KEY, sector);
        setPreferredSector(sector);
        // Dispatch custom event so other components can react
        window.dispatchEvent(new CustomEvent('sps_sector_change', { detail: sector }));
    };

    const clearPreference = () => {
        localStorage.removeItem(STORAGE_KEY);
        setPreferredSector(null);
        window.dispatchEvent(new CustomEvent('sps_sector_change', { detail: null }));
    };

    // Listen for changes in other components/tabs
    useEffect(() => {
        const handleEvent = (e: any) => {
            setPreferredSector(e.detail);
        };
        window.addEventListener('sps_sector_change', handleEvent);
        return () => window.removeEventListener('sps_sector_change', handleEvent);
    }, []);

    return { preferredSector, setPreference, clearPreference };
}
