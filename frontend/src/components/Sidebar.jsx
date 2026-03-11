import { useState, useEffect } from 'react';
import FileDropZone from './FileDropZone';
import IntersectionPanel from './IntersectionPanel';
import SlopeMapPanel from './SlopeMapPanel';
import './Sidebar.css';

export default function Sidebar({
    onFileLoad,
    onLoadConcessions,
    onLoadGeology,
    geologyLoading,
    geoSimplify,
    onGeoSimplifyChange,
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
    onExportSlope,
    slopeRectBbox,
    slopeRanges,
    onRangesChange,
    onShapefileUpload,
    onExportShapefile,
}) {
    const [collapsed, setCollapsed] = useState(false);
    const [lidarFiles, setLidarFiles] = useState([]);
    const [uploadingLidar, setUploadingLidar] = useState(false);
    const [shpUploading, setShpUploading] = useState(false);

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
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="url(#brandGrad)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                <defs>
                                    <linearGradient id="brandGrad" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#22d3ee" />
                                        <stop offset="50%" stopColor="#0ea5e9" />
                                        <stop offset="100%" stopColor="#8b5cf6" />
                                    </linearGradient>
                                </defs>
                                <circle cx="12" cy="12" r="10" />
                                <path d="M2 12h20" />
                                <path d="M12 2a15 15 0 0 1 4 10 15 15 0 0 1-4 10" />
                                <path d="M12 2a15 15 0 0 0-4 10 15 15 0 0 0 4 10" />
                            </svg>
                        </div>
                        <div>
                            <h1 className="brand-title">GeologgIA Map</h1>
                            <span className="brand-subtitle">Inteligencia Geológica</span>
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
                    <div className="basemap-toggle">
                        <button
                            className="basemap-btn"
                            onClick={() => onBaseMapChange?.('carto')}
                            style={{
                                background: baseMap === 'carto' ? 'rgba(14,165,233,0.2)' : 'transparent',
                                color: baseMap === 'carto' ? '#0ea5e9' : 'rgba(255,255,255,0.4)',
                            }}
                        >🗺 Estándar</button>
                        <button
                            className="basemap-btn"
                            onClick={() => onBaseMapChange?.('topo')}
                            style={{
                                background: baseMap === 'topo' ? 'rgba(16,185,129,0.2)' : 'transparent',
                                color: baseMap === 'topo' ? '#10b981' : 'rgba(255,255,255,0.4)',
                            }}
                        >⛰ Topográfico</button>
                    </div>

                    <div className="layer-toggle">
                        <label className="layer-label">
                            <span className="layer-dot" style={{ background: '#0ea5e9' }} />
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

                    <div className="layer-toggle">
                        <label className="layer-label">
                            <span className="layer-dot" style={{ background: '#FFE066' }} />
                            Geología de Chile
                        </label>
                        <input
                            type="checkbox"
                            className="toggle"
                            checked={layers.geology}
                            onChange={() => onToggleLayer('geology')}
                        />
                    </div>
                </div>

                {/* Geology Panel */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 22c-4.97 0-9-2.24-9-5v-4" />
                            <path d="M3 8c0-2.76 4.03-5 9-5s9 2.24 9 5" />
                            <path d="M21 8v4c0 2.76-4.03 5-9 5" />
                            <path d="M3 13c0 2.76 4.03 5 9 5" />
                        </svg>
                        Mapa Geológico
                    </h4>

                    <p style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', margin: '0 0 8px 0' }}>
                        Litología de la zona visible con colores por unidad geológica.
                    </p>

                    {/* Resolution toggle */}
                    <div className="resolution-toggle">
                        <button
                            className={`toggle-btn ${geoSimplify ? 'toggle-btn--active' : 'toggle-btn--inactive'}`}
                            onClick={() => onGeoSimplifyChange?.(true)}
                        >
                            ⚡ Rápida
                        </button>
                        <button
                            className={`toggle-btn ${!geoSimplify ? 'toggle-btn--active' : 'toggle-btn--inactive'}`}
                            onClick={() => onGeoSimplifyChange?.(false)}
                        >
                            🔬 Alta Res
                        </button>
                    </div>

                    <button
                        className="btn btn-primary"
                        onClick={() => onLoadGeology?.(geoSimplify)}
                        disabled={geologyLoading}
                        style={{ width: '100%' }}
                    >
                        {geologyLoading ? (
                            <>
                                <span className="map-loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                                Cargando Geología…
                            </>
                        ) : (
                            <>🪨 Cargar Mapa Geológico</>
                        )}
                    </button>

                    <p style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', margin: '6px 0 0 0', lineHeight: 1.3 }}>
                        ⚡ Rápida: geometrías simplificadas, carga instantánea.<br/>
                        🔬 Alta Resolución: detalle completo de polígonos.
                    </p>
                </div>

                {/* Slope Map Panel (NEW) */}
                <SlopeMapPanel
                    onStartDrawing={onStartDrawing}
                    onGenerateSlope={onGenerateSlope}
                    onExportSlope={onExportSlope}
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

                {/* Shapefile Import / Export */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        Importar / Exportar
                    </h4>

                    {/* Shapefile Upload */}
                    <label
                        className="shp-upload-label"
                        style={{ cursor: shpUploading ? 'wait' : 'pointer' }}
                    >
                        {shpUploading ? (
                            <><span className="map-loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Procesando…</>
                        ) : (
                            <>📂 Cargar Shapefile (.shp)</>
                        )}
                        <input
                            type="file"
                            accept=".shp,.shx,.dbf,.prj,.cpg"
                            multiple
                            style={{ display: 'none' }}
                            disabled={shpUploading}
                            onChange={async (e) => {
                                const files = Array.from(e.target.files || []);
                                if (files.length === 0) return;
                                setShpUploading(true);
                                try {
                                    await onShapefileUpload?.(files);
                                } finally {
                                    setShpUploading(false);
                                }
                                e.target.value = '';
                            }}
                        />
                    </label>

                    <p className="shp-help-text" style={{ marginBottom: 10 }}>
                        Selecciona .shp + .shx + .dbf (y opcionalmente .prj, .cpg).
                        Se reproyectará automáticamente a WGS84.
                    </p>

                    {/* Export Shapefile */}
                    <button
                        className="btn btn-ghost"
                        style={{ width: '100%', fontSize: '0.78rem', gap: 6 }}
                        onClick={() => onExportShapefile?.()}
                    >
                        📥 Exportar a Shapefile
                    </button>

                    <p className="shp-help-text" style={{ marginTop: 4 }}>
                        Exporta todas las capas visibles como .shp (ZIP).
                    </p>
                </div>

                {/* File drop GeoJSON */}
                <div className="sidebar-section">
                    <h4 className="section-title">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        Importar GeoJSON
                    </h4>
                    <FileDropZone onFileLoad={onFileLoad} />
                </div>

                {/* Intersection results */}
                <IntersectionPanel data={intersectionData} loading={intersectionLoading} />
            </aside>
        </>
    );
}
