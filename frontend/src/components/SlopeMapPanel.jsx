import { useState } from 'react';
import './SlopeMapPanel.css';

const DEFAULT_RANGES = [
    { min: 0, max: 3, color: '#38a800', label: '0 – 3%' },
    { min: 3, max: 7, color: '#267300', label: '3 – 7%' },
    { min: 7, max: 12, color: '#a8a800', label: '7 – 12%' },
    { min: 12, max: 25, color: '#005500', label: '12 – 25%' },
    { min: 25, max: 50, color: '#ffff00', label: '25 – 50%' },
    { min: 50, max: 75, color: '#ff8c00', label: '50 – 75%' },
    { min: 75, max: 999, color: '#ff0000', label: '> 75%' },
];

export default function SlopeMapPanel({
    onStartDrawing,
    onGenerateSlope,
    slopeLoading,
    slopeData,
    slopeRectBbox,
    drawingMode,
    slopeRanges,
    onRangesChange,
}) {
    const [resolution, setResolution] = useState(30);

    const ranges = slopeRanges || DEFAULT_RANGES;

    const handleRangeColorChange = (idx, newColor) => {
        const updated = [...ranges];
        updated[idx] = { ...updated[idx], color: newColor };
        onRangesChange?.(updated);
    };

    const handleRangeMinChange = (idx, val) => {
        const updated = [...ranges];
        const num = parseFloat(val) || 0;
        updated[idx] = {
            ...updated[idx],
            min: num,
            label: num >= 75 ? `> ${num}%` : `${num} – ${updated[idx].max}%`,
        };
        onRangesChange?.(updated);
    };

    const handleRangeMaxChange = (idx, val) => {
        const updated = [...ranges];
        const num = parseFloat(val) || 0;
        updated[idx] = {
            ...updated[idx],
            max: num,
            label: updated[idx].min >= 75 ? `> ${updated[idx].min}%` : `${updated[idx].min} – ${num}%`,
        };
        onRangesChange?.(updated);
    };

    const handleDeleteRange = (idx) => {
        if (ranges.length <= 2) return;
        const updated = ranges.filter((_, i) => i !== idx);
        onRangesChange?.(updated);
    };

    const handleAddRange = () => {
        const lastMax = ranges[ranges.length - 1]?.max || 100;
        const newRange = {
            min: lastMax,
            max: lastMax + 25,
            color: '#ff6600',
            label: `${lastMax} – ${lastMax + 25}%`,
        };
        onRangesChange?.([...ranges, newRange]);
    };

    const handleGenerate = () => {
        if (!slopeRectBbox) return;
        onGenerateSlope?.(slopeRectBbox, resolution, ranges);
    };

    const stats = slopeData?.stats;

    return (
        <div className="sidebar-section slope-panel">
            <h4 className="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 20 L22 4" />
                    <path d="M2 20 L22 20" />
                    <path d="M22 4 L22 20" />
                </svg>
                Mapa de Pendientes
            </h4>

            {/* Step 1: Draw rectangle */}
            <button
                className={`slope-draw-btn ${drawingMode ? 'active' : ''} ${slopeRectBbox && !drawingMode ? 'has-bbox' : ''}`}
                onClick={onStartDrawing}
            >
                {drawingMode ? (
                    <>
                        <span className="map-loading-spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
                        Dibujando… (click + arrastrar)
                    </>
                ) : slopeRectBbox ? (
                    '✅ Zona seleccionada — Click para redibujar'
                ) : (
                    <>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="3" width="18" height="18" rx="1" strokeDasharray="4 2" />
                        </svg>
                        Seleccionar Zona en el Mapa
                    </>
                )}
            </button>

            {/* Step 2: Resolution */}
            <div className="slope-resolution">
                <label>Resolución:</label>
                <select value={resolution} onChange={(e) => setResolution(Number(e.target.value))}>
                    <option value={15}>Baja (15×15)</option>
                    <option value={30}>Media (30×30)</option>
                    <option value={50}>Alta (50×50)</option>
                    <option value={80}>Muy Alta (80×80)</option>
                </select>
            </div>

            {/* Step 3: Editable ranges */}
            <div className="slope-ranges">
                <div className="slope-ranges-title">
                    <span>Rangos de Pendiente (%)</span>
                </div>
                {ranges.map((r, idx) => (
                    <div key={idx} className="slope-range-row">
                        <div
                            className="slope-range-color"
                            style={{ background: r.color }}
                            title="Cambiar color"
                        >
                            <input
                                type="color"
                                value={r.color}
                                onChange={(e) => handleRangeColorChange(idx, e.target.value)}
                            />
                        </div>
                        <input
                            className="slope-range-input"
                            type="number"
                            value={r.min}
                            onChange={(e) => handleRangeMinChange(idx, e.target.value)}
                            min={0}
                            title="Mínimo %"
                        />
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>–</span>
                        <input
                            className="slope-range-input"
                            type="number"
                            value={r.max}
                            onChange={(e) => handleRangeMaxChange(idx, e.target.value)}
                            min={0}
                            title="Máximo %"
                        />
                        <span className="slope-range-label">%</span>
                        <button
                            className="slope-range-delete"
                            onClick={() => handleDeleteRange(idx)}
                            title="Eliminar rango"
                        >✕</button>
                    </div>
                ))}
                <button className="slope-add-range" onClick={handleAddRange}>
                    + Agregar Rango
                </button>
            </div>

            {/* Step 4: Generate */}
            <button
                className="slope-generate-btn"
                onClick={handleGenerate}
                disabled={!slopeRectBbox || slopeLoading}
            >
                {slopeLoading ? (
                    <>
                        <span className="map-loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                        Calculando Pendientes…
                    </>
                ) : (
                    <>🏔 Generar Mapa de Pendientes</>
                )}
            </button>

            {/* Stats */}
            {stats && (
                <div className="slope-stats">
                    <div className="slope-stat">
                        <div className="slope-stat-value">{stats.min_slope_pct?.toFixed(1) ?? stats.min_slope}%</div>
                        <div className="slope-stat-label">Mín</div>
                    </div>
                    <div className="slope-stat">
                        <div className="slope-stat-value">{stats.mean_slope_pct?.toFixed(1) ?? stats.mean_slope}%</div>
                        <div className="slope-stat-label">Media</div>
                    </div>
                    <div className="slope-stat">
                        <div className="slope-stat-value">{stats.max_slope_pct?.toFixed(1) ?? stats.max_slope}%</div>
                        <div className="slope-stat-label">Máx</div>
                    </div>
                </div>
            )}

            {/* Source indicator */}
            {slopeData?.source_label && (
                <div style={{
                    fontSize: '0.67rem', opacity: 0.6, marginTop: 6,
                    display: 'flex', alignItems: 'center', gap: 4,
                }}>
                    <span style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: slopeData.source === 'lidar' ? '#4caf50' :
                            slopeData.source === 'alos_world3d' ? '#2196f3' :
                                slopeData.source === 'open_elevation_srtm' ? '#ff9800' : '#f44336',
                        display: 'inline-block',
                    }} />
                    Fuente: {slopeData.source_label}
                </div>
            )}
        </div>
    );
}

/* ── Legend component (rendered inside MapView overlay) ── */
export function SlopeLegend({ ranges, visible }) {
    if (!visible || !ranges || ranges.length === 0) return null;

    return (
        <div className="slope-legend">
            <div className="slope-legend-title">Pendiente (%)</div>
            {ranges.map((r, idx) => (
                <div key={idx} className="slope-legend-item">
                    <div className="slope-legend-swatch" style={{ background: r.color }} />
                    <span>{r.min >= 75 ? `> ${r.min}%` : `${r.min} – ${r.max}%`}</span>
                </div>
            ))}
        </div>
    );
}

export { DEFAULT_RANGES };
