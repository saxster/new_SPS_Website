import { useState, useEffect } from 'preact/hooks';
import { useSectorPreference } from '../../hooks/useSectorPreference';
import './SectorIntelligence.css';

interface Article {
    title: string;
    url: string;
    time: string;
    source: string;
    category: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
}

export default function SectorIntelligence() {
    const { preferredSector } = useSectorPreference();
    const [articles, setArticles] = useState<Article[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchNews = async () => {
            setLoading(true);
            try {
                const sectorParam = preferredSector || 'all';
                const res = await fetch(`/api/news-wire?sector=${sectorParam}`);
                const data = await res.json();
                setArticles(data.articles.slice(0, 5));
            } catch (e) {
                console.error("Failed to fetch sector news", e);
            } finally {
                setLoading(false);
            }
        };

        fetchNews();
    }, [preferredSector]);

    if (!preferredSector && articles.length === 0) return null;

    return (
        <div class="sector-intel-container">
            <div class="intel-header">
                <span class="pulse-icon"></span>
                <h3 class="intel-title">
                    {preferredSector ? `${preferredSector.toUpperCase()} SECTOR WATCH` : 'GLOBAL INTEL'}
                </h3>
                {preferredSector && <span class="optimized-badge">PERSONALIZED</span>}
            </div>

            <div class="intel-body">
                {loading ? (
                    <div class="loading-state">SCANNING SECTOR FREQUENCIES...</div>
                ) : articles.length > 0 ? (
                    <div class="articles-list">
                        {articles.map((a, i) => (
                            <a key={i} href={a.url} target="_blank" rel="noopener noreferrer" class={`article-item severity-${a.severity}`}>
                                <div class="article-meta">
                                    <span class="article-category">{a.category}</span>
                                    <span class="article-source">{a.source}</span>
                                </div>
                                <div class="article-title">{a.title}</div>
                                <div class="article-footer">
                                    {new Date(a.time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </a>
                        ))}
                    </div>
                ) : (
                    <div class="empty-state">No immediate sector-specific threats detected.</div>
                )}
            </div>
            
            <div class="intel-footer">
                SPS Hybrid Intelligence Stream // Real-time
            </div>
        </div>
    );
}
