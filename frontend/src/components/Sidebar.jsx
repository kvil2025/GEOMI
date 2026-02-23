import { useState, useEffect } from 'react';
import FileDropZone from './FileDropZone';
import IntersectionPanel from './IntersectionPanel';
import SlopeMapPanel from './SlopeMapPanel';
import './Sidebar.css';

export default function Sidebar({
    onFileLoad,
    onLoadConcessions,
    concessionsLoading,
    slopeLoading,
    slopeSource,
    slopeData,
    intersectionData,
    intersectionLoading,
    layers,
    onToggleLayer,
    baseMap,
    onBaseMapChange,
    drawingMode,
    onStartDrawing,
    onGenerateSlope,
    slopeRectBbox,
    slopeRanges,
    onRangesChange,
}) {
    const [collapsed, setCollapsed] = useState(false);
    const [lidarFiles, setLidarFiles] = useState([]);
    const [uploadingLidar, setUploadingLidar] = useState(false);

    // Fetch LiDAR files on mount
    useEffect(() => {
        fetch('/dem/lidar/list')
            .then(r => r.ok ? r.json() : { files: [] })
            .then(d => setLidarFiles(d.files || []))
            .catch(() => { });
    }, []);

    const handleLidarUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setUploadingLidar(true);
        try {
            const form = new FormData();
            form.append('file', file);
            const resp = await fetch('/dem/upload', { method: 'POST', body: form });
            const data = await resp.json();
            if (resp.ok) {
                const listResp = await fetch('/dem/lidar/list');
                const listData = await listResp.json();
                setLidarFiles(listData.files || []);
                alert(`✅ ${data.message}`);
            } else {
                alert(`❌ ${data.detail || 'Error al subir'}`);
            }
        } catch (err) {
            alert(`❌ Error: ${err.message}`);
        }
        setUploadingLidar(false);
        e.target.value = '';
    };

    const handleDeleteLidar = async (filename) => {
        if (!confirm(`¿Eliminar ${filename}?`)) return;
        try {
            await fetch(`/dem/lidar/${filename}`, { method: 'DELETE' });
            setLidarFiles(prev => prev.filter(f => f.filename !== filename));
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    return (
        <>
            <button
                className="sidebar-toggle btn-icon"
                onClick={() => setCollapsed((c) => !c)}
                title={collapsed ? 'Abrir panel' : 'Cerrar panel'}
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    {collapsed ? (
                        <polyline points="9 18 15 12 9 6" />
                    ) : (
                        <polyline points="15 18 9 12 15 6" />
                    )}
                </svg>
            </button>

            <aside className={`sidebar glass-card ${collapsed ? 'sidebar--collapsed' : ''}`}>
                {/* Header */}
                <div className="sidebar-header">
                    <div className="sidebar-brand">
                        <div className="brand-icon">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="url(#brandGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <defs>
                                    <linearGradient id="brandGrad" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#00d2ff" />
                                        <stop offset="100%" stopColor="#7c3aed" />
                                    </linearGradient>
                                </defs>
                                <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
                                <line x1="12" y1="22" x2="12" y2="15.5" />
                                <polyline points="22 8.5 12 15.5 2 8.5" />
                            </svg>
                        </div>
                        <div>
                            <h1 className="brand-title">Mining Intel</h1>
                            <span className="brand-subtitle">Dashboard Chile</span>
                        </div>
                    </div>
                </div>

                {/* Layer toggles */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polygon points="12 2 2 7 12 12 22 7 12 2" />
                            <polyline points="2 17 12 22 22 17" />
                            <polyline points="2 12 12 17 22 12" />
                        </svg>
                        Capas
                    </h4>

                    {/* Base map selector */}
                    <div style={{
                        display: 'flex', gap: 4, marginBottom: 12,
                        background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: 3,
                    }}>
                        <button
                            onClick={() => onBaseMapChange?.('carto')}
                            style={{
                                flex: 1, padding: '6px 0', borderRadius: 6,
                                border: 'none', cursor: 'pointer', fontSize: '0.7rem',
                                fontWeight: 600, transition: 'all 0.2s',
                                background: baseMap === 'carto' ? 'rgba(0,210,255,0.25)' : 'transparent',
                                color: baseMap === 'carto' ? '#00d2ff' : 'rgba(255,255,255,0.5)',
                            }}
                        >🗺 Estándar</button>
                        <button
                            onClick={() => onBaseMapChange?.('topo')}
                            style={{
                                flex: 1, padding: '6px 0', borderRadius: 6,
                                border: 'none', cursor: 'pointer', fontSize: '0.7rem',
                                fontWeight: 600, transition: 'all 0.2s',
                                background: baseMap === 'topo' ? 'rgba(76,175,80,0.25)' : 'transparent',
                                color: baseMap === 'topo' ? '#4caf50' : 'rgba(255,255,255,0.5)',
                            }}
                        >⛰ Topográfico</button>
                    </div>

                    <div className="layer-toggle">
                        <label className="layer-label">
                            <span className="layer-dot" style={{ background: '#00d2ff' }} />
                            Concesiones Mineras
                        </label>
                        <input
                            type="checkbox"
                            className="toggle"
                            checked={layers.concessions}
                            onChange={() => onToggleLayer('concessions')}
                        />
                    </div>

                    <div className="layer-toggle">
                        <label className="layer-label">
                            <span className="layer-dot" style={{ background: '#38a800' }} />
                            Mapa de Pendientes
                        </label>
                        <input
                            type="checkbox"
                            className="toggle"
                            checked={layers.slope}
                            onChange={() => onToggleLayer('slope')}
                        />
                    </div>

                    <div className="layer-toggle">
                        <label className="layer-label">
                            <span className="layer-dot" style={{ background: '#7c3aed' }} />
                            Datos del Usuario
                        </label>
                        <input
                            type="checkbox"
                            className="toggle"
                            checked={layers.userData}
                            onChange={() => onToggleLayer('userData')}
                        />
                    </div>
                </div>

                {/* Slope Map Panel (NEW) */}
                <SlopeMapPanel
                    onStartDrawing={onStartDrawing}
                    onGenerateSlope={onGenerateSlope}
                    slopeLoading={slopeLoading}
                    slopeData={slopeData}
                    slopeRectBbox={slopeRectBbox}
                    drawingMode={drawingMode}
                    slopeRanges={slopeRanges}
                    onRangesChange={onRangesChange}
                />

                {/* Actions */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="3" />
                            <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1" />
                        </svg>
                        Acciones
                    </h4>

                    <div className="action-buttons">
                        <button
                            className="btn btn-primary"
                            onClick={onLoadConcessions}
                            disabled={concessionsLoading}
                            style={{ width: '100%' }}
                        >
                            {concessionsLoading ? (
                                <>
                                    <span className="map-loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                                    Cargando…
                                </>
                            ) : (
                                <>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                                        <circle cx="12" cy="10" r="3" />
                                    </svg>
                                    Cargar Concesiones
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* LiDAR Upload */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                            <polyline points="17 8 12 3 7 8" />
                            <line x1="12" y1="3" x2="12" y2="15" />
                        </svg>
                        Datos Topográficos (LiDAR)
                    </h4>

                    <label
                        className="btn btn-ghost"
                        style={{
                            width: '100%', cursor: 'pointer',
                            textAlign: 'center', display: 'block',
                            fontSize: '0.8rem',
                        }}
                    >
                        {uploadingLidar ? 'Subiendo…' : '📡 Cargar GeoTIFF (.tif)'}
                        <input
                            type="file"
                            accept=".tif,.tiff"
                            onChange={handleLidarUpload}
                            style={{ display: 'none' }}
                            disabled={uploadingLidar}
                        />
                    </label>

                    {lidarFiles.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                            {lidarFiles.map(f => (
                                <div key={f.filename} style={{
                                    display: 'flex', justifyContent: 'space-between',
                                    alignItems: 'center', fontSize: '0.7rem',
                                    padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.1)',
                                }}>
                                    <span style={{ opacity: 0.8 }} title={f.filename}>
                                        📄 {f.filename.length > 18
                                            ? f.filename.slice(0, 15) + '…'
                                            : f.filename}
                                        <span style={{ opacity: 0.5, marginLeft: 4 }}>
                                            ({f.size_mb} MB)
                                        </span>
                                    </span>
                                    <button
                                        onClick={() => handleDeleteLidar(f.filename)}
                                        style={{
                                            background: 'none', border: 'none',
                                            color: '#f44336', cursor: 'pointer',
                                            fontSize: '0.7rem', padding: '2px 4px',
                                        }}
                                        title="Eliminar"
                                    >✕</button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* File drop */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        Importar Datos
                    </h4>
                    <FileDropZone onFileLoad={onFileLoad} />
                </div>

                {/* Intersection results */}
                <IntersectionPanel data={intersectionData} loading={intersectionLoading} />
            </aside>
        </>
    );
}
