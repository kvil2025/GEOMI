import './IntersectionPanel.css';

export default function IntersectionPanel({ data, loading }) {
    if (loading) {
        return (
            <div className="intersection-section">
                <h4 className="section-title">Intersecciones</h4>
                <div className="intersection-loading">
                    <div className="map-loading-spinner" />
                    <span>Calculando…</span>
                </div>
            </div>
        );
    }

    if (!data) return null;

    const { features = [], summary = {} } = data;

    return (
        <div className="intersection-section animate-slide-up">
            <h4 className="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-teal)" strokeWidth="2">
                    <circle cx="9" cy="12" r="7" />
                    <circle cx="15" cy="12" r="7" />
                </svg>
                Intersecciones
                {features.length > 0 && (
                    <span className="badge badge-teal">{features.length}</span>
                )}
            </h4>

            <div className="intersection-summary">
                <div className="summary-item">
                    <span className="summary-label">Concesiones en zona</span>
                    <span className="summary-value">{summary.concessions_in_bbox || 0}</span>
                </div>
                <div className="summary-item">
                    <span className="summary-label">Intersectando</span>
                    <span className="summary-value text-accent">{summary.intersecting || 0}</span>
                </div>
            </div>

            {features.length === 0 ? (
                <p className="text-muted text-sm" style={{ textAlign: 'center', padding: '8px 0' }}>
                    No se encontraron intersecciones
                </p>
            ) : (
                <div className="intersection-list">
                    {features.map((f, i) => (
                        <div key={i} className="intersection-card">
                            <div className="intersection-card-header">
                                <span className="intersection-name">
                                    {f.properties?.nombre || f.properties?.NOMBRE || `Concesión ${i + 1}`}
                                </span>
                                <span className="badge badge-teal">{f.properties?.overlap_pct?.toFixed(1)}%</span>
                            </div>
                            {f.properties?.tipo && (
                                <span className="text-xs text-muted">{f.properties.tipo}</span>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
