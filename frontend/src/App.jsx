import { useState, useCallback, useRef } from 'react';
import MapView from './components/MapView';
import Sidebar from './components/Sidebar';
import ElevationChart from './components/ElevationChart';
import ToastProvider, { showToast } from './components/Toast';
import { useApi } from './hooks/useApi';
import {
    fetchConcessions,
    fetchSlope,
    exportSlopeGeoJSON,
    postIntersection,
    postElevationProfile,
    fetchGeology,
    uploadShapefile,
    exportShapefile,
} from './services/api';
import { DEFAULT_RANGES } from './components/SlopeMapPanel';
import './App.css';

export default function App() {
    const mapRef = useRef(null);
    const [bbox, setBbox] = useState(null);

    // Layer visibility
    const [layers, setLayers] = useState({
        concessions: true,
        slope: true,
        userData: true,
        geology: false,
    });

    // Data states
    const [concessions, setConcessions] = useState(null);
    const [userGeoJSON, setUserGeoJSON] = useState(null);
    const [slopeData, setSlopeData] = useState(null);
    const [elevationData, setElevationData] = useState(null);
    const [baseMap, setBaseMap] = useState('carto');

    // Geology states
    const [geologyData, setGeologyData] = useState(null);
    const [geologyLegend, setGeologyLegend] = useState(null);
    const [geoSimplify, setGeoSimplify] = useState(true);

    // Slope map interactive states
    const [drawingMode, setDrawingMode] = useState(false);
    const [slopeRectBbox, setSlopeRectBbox] = useState(null);
    const [slopeRanges, setSlopeRanges] = useState(DEFAULT_RANGES);

    // API hooks
    const concessionsApi = useApi(fetchConcessions);
    const slopeApi = useApi(fetchSlope);
    const intersectionApi = useApi(postIntersection);
    const elevationApi = useApi(postElevationProfile);
    const geologyApi = useApi(fetchGeology);

    // Handlers
    const handleMapReady = useCallback((map) => {
        mapRef.current = map;
    }, []);

    const handleBboxChange = useCallback((newBbox) => {
        setBbox(newBbox);
    }, []);

    const handleLoadConcessions = useCallback(async () => {
        if (!bbox) return;
        try {
            const data = await concessionsApi.execute(bbox);
            setConcessions(data);
            showToast(
                `Concesiones cargadas: ${data?.features?.length || 0} encontradas`,
                'success', 3000
            );
        } catch (err) {
            console.error('Failed to load concessions:', err);
            showToast(
                `Error cargando concesiones: ${err.message || 'Error desconocido'}`,
                'error'
            );
        }
    }, [bbox, concessionsApi]);

    // Geology handler
    const handleLoadGeology = useCallback(async (simplify) => {
        if (!bbox) return;
        const useSimplify = simplify !== undefined ? simplify : geoSimplify;
        try {
            const t0 = performance.now();
            const modeLabel = useSimplify ? 'simplificada' : 'alta resolución';
            showToast(`Cargando geología (${modeLabel})…`, 'info', 2000);
            const data = await geologyApi.execute(bbox, useSimplify);
            setGeologyData(data);
            setGeologyLegend(data.legend || []);
            setLayers((l) => ({ ...l, geology: true }));

            const clientMs = Math.round(performance.now() - t0);
            const serverMs = data.timing?.total_ms || '?';
            const unitCount = data.legend?.length || 0;
            showToast(
                `Geología (${modeLabel}): ${data?.total || 0} polígonos, ${unitCount} litologías (${clientMs}ms)`,
                'success', 4000
            );
        } catch (err) {
            console.error('Failed to load geology:', err);
            showToast(
                `Error cargando geología: ${err.message || 'Error desconocido'}`,
                'error'
            );
        }
    }, [bbox, geologyApi, geoSimplify]);

    // Rectangle-based slope generation
    const handleStartDrawing = useCallback(() => {
        setDrawingMode((prev) => !prev);
    }, []);

    const handleRectangleDrawn = useCallback((rectBbox) => {
        setSlopeRectBbox(rectBbox);
        setDrawingMode(false);
        showToast('Zona seleccionada correctamente', 'success', 2000);
    }, []);

    const handleGenerateSlope = useCallback(async (rectBbox, resolution, ranges) => {
        if (!rectBbox) return;
        try {
            const data = await slopeApi.execute(rectBbox, resolution);
            setSlopeData(data);
            setSlopeRanges(ranges);
            setLayers((l) => ({ ...l, slope: true }));

            const source = data?.source_label || 'desconocida';
            showToast(
                `Mapa de pendientes generado (${data.grid_size}×${data.grid_size}) — Fuente: ${source}`,
                'success', 4000
            );
        } catch (err) {
            console.error('Failed to generate slope map:', err);
            showToast(
                `Error generando pendientes: ${err.message || 'No se pudo conectar al servidor'}`,
                'error', 6000
            );
        }
    }, [slopeApi]);

    const handleExportSlope = useCallback(async (bboxStr, gridSize) => {
        if (!bboxStr) return;
        try {
            const geojson = await exportSlopeGeoJSON(bboxStr, gridSize);
            const blob = new Blob([JSON.stringify(geojson, null, 2)], {
                type: 'application/geo+json',
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `pendientes_${gridSize}x${gridSize}.geojson`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showToast(
                `Exportado: pendientes_${gridSize}x${gridSize}.geojson`,
                'success', 3000
            );
        } catch (err) {
            console.error('Export failed:', err);
            showToast(
                `Error exportando: ${err.message || 'Error desconocido'}`,
                'error'
            );
        }
    }, []);

    const handleFileLoad = useCallback(async (geojson, fileName) => {
        setUserGeoJSON(geojson);
        showToast(`Archivo cargado: ${fileName}`, 'info', 3000);

        try {
            await intersectionApi.execute(geojson);
        } catch (err) {
            console.error('Intersection failed:', err);
            showToast(
                `Error en intersección: ${err.message || 'Error desconocido'}`,
                'error'
            );
        }

        const lineFeature = (geojson.features || []).find(
            (f) => f.geometry?.type === 'LineString'
        );
        if (lineFeature) {
            try {
                const profile = await elevationApi.execute(geojson);
                setElevationData(profile);
            } catch (err) {
                console.error('Elevation profile failed:', err);
                showToast(
                    `Error en perfil de elevación: ${err.message}`,
                    'error'
                );
            }
        }
    }, [intersectionApi, elevationApi]);

    const handleToggleLayer = useCallback((layer) => {
        setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
    }, []);

    // Shapefile upload handler
    const handleShapefileUpload = useCallback(async (files) => {
        try {
            showToast('Procesando Shapefile…', 'info', 2000);
            const result = await uploadShapefile(files);
            setUserGeoJSON(result.geojson);
            setLayers((l) => ({ ...l, userData: true }));
            showToast(
                `Shapefile cargado: ${result.feature_count} ${result.geometry_type}s — "${result.name}" (${result.elapsed_ms}ms)`,
                'success', 5000
            );
        } catch (err) {
            console.error('Shapefile upload failed:', err);
            showToast(`Error: ${err.message}`, 'error');
        }
    }, []);

    // Export shapefile handler — collects all visible data
    const handleExportShapefile = useCallback(async () => {
        // Gather features from all visible layers
        const allFeatures = [];

        if (layers.geology && geologyData?.features?.length) {
            allFeatures.push(...geologyData.features);
        }
        if (layers.userData && userGeoJSON?.features?.length) {
            allFeatures.push(...userGeoJSON.features);
        }
        if (layers.concessions && concessions?.features?.length) {
            allFeatures.push(...concessions.features);
        }

        if (allFeatures.length === 0) {
            showToast('No hay datos visibles para exportar', 'error');
            return;
        }

        try {
            showToast(`Exportando ${allFeatures.length} features…`, 'info', 2000);
            const geojson = { type: 'FeatureCollection', features: allFeatures };
            const timestamp = new Date().toISOString().slice(0, 10);
            await exportShapefile(geojson, `export_${timestamp}`);
            showToast(`Shapefile exportado: ${allFeatures.length} features`, 'success', 4000);
        } catch (err) {
            console.error('Export failed:', err);
            showToast(`Error exportando: ${err.message}`, 'error');
        }
    }, [layers, geologyData, userGeoJSON, concessions]);

    return (
        <ToastProvider>
            <div className="app">
                <MapView
                    concessions={layers.concessions ? concessions : null}
                    userGeoJSON={layers.userData ? userGeoJSON : null}
                    intersectionResult={intersectionApi.data}
                    slopeData={layers.slope ? slopeData : null}
                    geologyData={layers.geology ? geologyData : null}
                    geologyLegend={layers.geology ? geologyLegend : null}
                    onMapReady={handleMapReady}
                    onBboxChange={handleBboxChange}
                    baseMap={baseMap}
                    drawingMode={drawingMode}
                    onRectangleDrawn={handleRectangleDrawn}
                    slopeRanges={slopeRanges}
                    showSlopeLegend={layers.slope}
                />

                <Sidebar
                    onFileLoad={handleFileLoad}
                    onLoadConcessions={handleLoadConcessions}
                    onLoadGeology={handleLoadGeology}
                    geologyLoading={geologyApi.loading}
                    geoSimplify={geoSimplify}
                    onGeoSimplifyChange={setGeoSimplify}

                    concessionsLoading={concessionsApi.loading}
                    slopeLoading={slopeApi.loading}
                    slopeSource={slopeData?.source}
                    slopeData={slopeData}
                    intersectionData={intersectionApi.data}
                    intersectionLoading={intersectionApi.loading}
                    layers={layers}
                    onToggleLayer={handleToggleLayer}
                    baseMap={baseMap}
                    onBaseMapChange={setBaseMap}
                    drawingMode={drawingMode}
                    onStartDrawing={handleStartDrawing}
                    onGenerateSlope={handleGenerateSlope}
                    onExportSlope={handleExportSlope}
                    slopeRectBbox={slopeRectBbox}
                    slopeRanges={slopeRanges}
                    onRangesChange={setSlopeRanges}
                    onShapefileUpload={handleShapefileUpload}
                    onExportShapefile={handleExportShapefile}
                />

                <ElevationChart data={elevationData} />
            </div>
        </ToastProvider>
    );
}
