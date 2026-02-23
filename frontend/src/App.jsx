import { useState, useCallback, useRef } from 'react';
import MapView from './components/MapView';
import Sidebar from './components/Sidebar';
import ElevationChart from './components/ElevationChart';
import { useApi } from './hooks/useApi';
import {
    fetchConcessions,
    fetchSlope,
    postIntersection,
    postElevationProfile,
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
    });

    // Data states
    const [concessions, setConcessions] = useState(null);
    const [userGeoJSON, setUserGeoJSON] = useState(null);
    const [slopeData, setSlopeData] = useState(null);
    const [elevationData, setElevationData] = useState(null);
    const [baseMap, setBaseMap] = useState('carto');

    // Slope map interactive states
    const [drawingMode, setDrawingMode] = useState(false);
    const [slopeRectBbox, setSlopeRectBbox] = useState(null);
    const [slopeRanges, setSlopeRanges] = useState(DEFAULT_RANGES);

    // API hooks
    const concessionsApi = useApi(fetchConcessions);
    const slopeApi = useApi(fetchSlope);
    const intersectionApi = useApi(postIntersection);
    const elevationApi = useApi(postElevationProfile);

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
        } catch (err) {
            console.error('Failed to load concessions:', err);
        }
    }, [bbox, concessionsApi]);



    // New: rectangle-based slope generation
    const handleStartDrawing = useCallback(() => {
        setDrawingMode((prev) => !prev);
    }, []);

    const handleRectangleDrawn = useCallback((rectBbox) => {
        setSlopeRectBbox(rectBbox);
        setDrawingMode(false);
    }, []);

    const handleGenerateSlope = useCallback(async (rectBbox, resolution, ranges) => {
        if (!rectBbox) return;
        try {
            const data = await slopeApi.execute(rectBbox, resolution);
            setSlopeData(data);
            setSlopeRanges(ranges);
            setLayers((l) => ({ ...l, slope: true }));
        } catch (err) {
            console.error('Failed to generate slope map:', err);
        }
    }, [slopeApi]);

    const handleFileLoad = useCallback(async (geojson, fileName) => {
        setUserGeoJSON(geojson);

        try {
            await intersectionApi.execute(geojson);
        } catch (err) {
            console.error('Intersection failed:', err);
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
            }
        }
    }, [intersectionApi, elevationApi]);

    const handleToggleLayer = useCallback((layer) => {
        setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
    }, []);

    return (
        <div className="app">
            <MapView
                concessions={layers.concessions ? concessions : null}
                userGeoJSON={layers.userData ? userGeoJSON : null}
                intersectionResult={intersectionApi.data}
                slopeData={layers.slope ? slopeData : null}
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
                slopeRectBbox={slopeRectBbox}
                slopeRanges={slopeRanges}
                onRangesChange={setSlopeRanges}
            />

            <ElevationChart data={elevationData} />
        </div>
    );
}
