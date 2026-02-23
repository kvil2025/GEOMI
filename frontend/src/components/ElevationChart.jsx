import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer,
} from 'recharts';
import './ElevationChart.css';

export default function ElevationChart({ data }) {
    if (!data || !data.profile || data.profile.length === 0) {
        return null;
    }

    const { profile, total_distance, min_elevation, max_elevation, elevation_gain } = data;

    return (
        <div className="elevation-panel glass-card animate-slide-up">
            <div className="elevation-header">
                <h3 className="elevation-title">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-teal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                    Perfil de Elevación
                </h3>
                <div className="elevation-stats">
                    <span className="stat">
                        <span className="stat-label">Dist.</span>
                        <span className="stat-value">{(total_distance / 1000).toFixed(1)} km</span>
                    </span>
                    <span className="stat">
                        <span className="stat-label">Min</span>
                        <span className="stat-value">{min_elevation} m</span>
                    </span>
                    <span className="stat">
                        <span className="stat-label">Max</span>
                        <span className="stat-value">{max_elevation} m</span>
                    </span>
                    <span className="stat">
                        <span className="stat-label">Ganancia</span>
                        <span className="stat-value text-accent">+{elevation_gain} m</span>
                    </span>
                </div>
            </div>

            <div className="elevation-chart-wrapper">
                <ResponsiveContainer width="100%" height={160}>
                    <AreaChart data={profile} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <defs>
                            <linearGradient id="elevGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#00d2ff" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#00d2ff" stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                        <XAxis
                            dataKey="distance"
                            tickFormatter={(v) => `${(v / 1000).toFixed(1)}`}
                            fontSize={10}
                            stroke="var(--text-muted)"
                            tick={{ fill: 'var(--text-muted)' }}
                        />
                        <YAxis
                            fontSize={10}
                            stroke="var(--text-muted)"
                            tick={{ fill: 'var(--text-muted)' }}
                            width={48}
                            tickFormatter={(v) => `${v}m`}
                        />
                        <Tooltip
                            contentStyle={{
                                background: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: '12px',
                                color: 'var(--text-primary)',
                            }}
                            formatter={(value) => [`${value} m`, 'Elevación']}
                            labelFormatter={(v) => `${(v / 1000).toFixed(2)} km`}
                        />
                        <Area
                            type="monotone"
                            dataKey="elevation"
                            stroke="#00d2ff"
                            strokeWidth={2}
                            fill="url(#elevGradient)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
