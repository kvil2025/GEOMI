import './SlopeHistogram.css';

export default function SlopeHistogram({ histogram, ranges, visible }) {
    if (!visible || !histogram || histogram.length === 0) return null;

    const maxPct = Math.max(...histogram.map((h) => h.percentage), 1);

    return (
        <div className="slope-histogram">
            <h5 className="slope-histogram-title">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="13" width="4" height="9" rx="1" />
                    <rect x="8" y="8" width="4" height="14" rx="1" />
                    <rect x="14" y="3" width="4" height="19" rx="1" />
                    <rect x="20" y="10" width="4" height="12" rx="1" />
                </svg>
                Distribución de Pendientes
            </h5>
            <div className="histogram-bars">
                {histogram.map((h, idx) => {
                    const range = ranges?.[idx];
                    const color = range?.color || '#888';
                    const barWidth = Math.max((h.percentage / maxPct) * 100, 2);
                    const label = h.max >= 999
                        ? `> ${h.min}%`
                        : `${h.min}–${h.max}%`;

                    return (
                        <div key={idx} className="histogram-row">
                            <span className="histogram-label">{label}</span>
                            <div className="histogram-bar-track">
                                <div
                                    className="histogram-bar-fill"
                                    style={{
                                        width: `${barWidth}%`,
                                        background: color,
                                    }}
                                />
                            </div>
                            <span className="histogram-value">
                                {h.percentage}%
                                <span className="histogram-count">({h.count})</span>
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
