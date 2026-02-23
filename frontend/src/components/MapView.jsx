import { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SlopeLegend } from './SlopeMapPanel';
import './MapView.css';

const INITIAL_CENTER = [-70.65, -27.35];
const INITIAL_ZOOM = 8;

const MAP_STYLE = {
    version: 8,
    name: 'Positron',
    sources: {
        'carto-tiles': {
            type: 'raster',
            tiles: [
                'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                'https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
                'https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png',
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
            maxzoom: 19,
        },
        'topo-tiles': {
            type: 'raster',
            tiles: [
                'https://a.tile.opentopomap.org/{z}/{x}/{y}.png',
                'https://b.tile.opentopomap.org/{z}/{x}/{y}.png',
                'https://c.tile.opentopomap.org/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
            maxzoom: 17,
        },
    },
    layers: [
        {
            id: 'base-tiles', type: 'raster', source: 'carto-tiles',
            minzoom: 0, maxzoom: 22,
        },
        {
            id: 'topo-tiles', type: 'raster', source: 'topo-tiles',
            minzoom: 0, maxzoom: 22,
            layout: { visibility: 'none' },
        },
    ],
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
};

export default function MapView({
    concessions, userGeoJSON, intersectionResult, slopeData,
    onMapReady, onBboxChange, baseMap = 'carto',
    drawingMode, onRectangleDrawn, slopeRanges, showSlopeLegend,
}) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const [loaded, setLoaded] = useState(false);

    // Rectangle drawing state
    const drawStartRef = useRef(null);

    useEffect(() => {
        if (mapRef.current) return;

        const map = new maplibregl.Map({
            container: containerRef.current,
            style: MAP_STYLE,
            center: INITIAL_CENTER,
            zoom: INITIAL_ZOOM,
            attributionControl: false,
        });

        map.addControl(new maplibregl.NavigationControl(), 'top-right');
        map.addControl(new maplibregl.ScaleControl({ maxWidth: 200 }), 'bottom-right');
        map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

        map.on('load', () => {
            setLoaded(true);
            const b = map.getBounds();
            onBboxChange?.(`${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`);
            onMapReady?.(map);
        });

        map.on('moveend', () => {
            const b = map.getBounds();
            onBboxChange?.(`${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`);
        });

        mapRef.current = map;
        return () => { map.remove(); mapRef.current = null; };
    }, []);

    // Toggle base map layers
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded) return;
        map.setLayoutProperty('base-tiles', 'visibility', baseMap === 'carto' ? 'visible' : 'none');
        map.setLayoutProperty('topo-tiles', 'visibility', baseMap === 'topo' ? 'visible' : 'none');
    }, [baseMap, loaded]);

    // Concessions layer
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded || !concessions) return;

        if (map.getSource('concessions')) {
            map.getSource('concessions').setData(concessions);
        } else {
            map.addSource('concessions', { type: 'geojson', data: concessions });
            map.addLayer({
                id: 'concessions-fill', type: 'fill', source: 'concessions',
                paint: { 'fill-color': '#00d2ff', 'fill-opacity': 0.15 },
            });
            map.addLayer({
                id: 'concessions-line', type: 'line', source: 'concessions',
                paint: { 'line-color': '#00d2ff', 'line-width': 1.5, 'line-opacity': 0.7 },
            });

            map.on('click', 'concessions-fill', (e) => {
                const props = e.features[0]?.properties || {};
                const html = Object.entries(props).slice(0, 6)
                    .map(([k, v]) => `<strong>${k}:</strong> ${v}`).join('<br/>');
                new maplibregl.Popup({ className: 'dark-popup' })
                    .setLngLat(e.lngLat)
                    .setHTML(`<div class="popup-content">${html}</div>`)
                    .addTo(map);
            });
            map.on('mouseenter', 'concessions-fill', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', 'concessions-fill', () => { map.getCanvas().style.cursor = ''; });
        }
    }, [concessions, loaded]);

    // User GeoJSON layer
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded || !userGeoJSON) return;

        if (map.getSource('user-data')) {
            map.getSource('user-data').setData(userGeoJSON);
        } else {
            map.addSource('user-data', { type: 'geojson', data: userGeoJSON });
            map.addLayer({
                id: 'user-fill', type: 'fill', source: 'user-data',
                paint: { 'fill-color': '#7c3aed', 'fill-opacity': 0.25 },
            });
            map.addLayer({
                id: 'user-line', type: 'line', source: 'user-data',
                paint: { 'line-color': '#7c3aed', 'line-width': 2 },
            });
        }

        try {
            const bounds = new maplibregl.LngLatBounds();
            const addCoords = (c) => { typeof c[0] === 'number' ? bounds.extend(c) : c.forEach(addCoords); };
            (userGeoJSON.features || []).forEach((f) => addCoords(f.geometry.coordinates));
            if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, maxZoom: 14 });
        } catch (_) { }
    }, [userGeoJSON, loaded]);

    // Intersection result layer
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded || !intersectionResult) return;

        if (map.getSource('intersection')) {
            map.getSource('intersection').setData(intersectionResult);
        } else {
            map.addSource('intersection', { type: 'geojson', data: intersectionResult });
            map.addLayer({
                id: 'intersection-fill', type: 'fill', source: 'intersection',
                paint: { 'fill-color': '#f59e0b', 'fill-opacity': 0.35 },
            });
            map.addLayer({
                id: 'intersection-line', type: 'line', source: 'intersection',
                paint: { 'line-color': '#f59e0b', 'line-width': 2 },
            });
        }
    }, [intersectionResult, loaded]);

    // ── Slope polygon layer (GIS-style colored cells) ──────────────
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded) return;

        if (!slopeData) {
            // Clear slope layers if data removed
            if (map.getLayer('slope-cells')) map.removeLayer('slope-cells');
            if (map.getLayer('slope-cells-outline')) map.removeLayer('slope-cells-outline');
            if (map.getSource('slope-cells')) map.removeSource('slope-cells');
            return;
        }

        const { slopes_percent, slopes, bbox: bboxStr, grid_size } = slopeData;
        const slopeGrid = slopes_percent || slopes;
        if (!slopeGrid || !bboxStr) return;

        const [minx, miny, maxx, maxy] = bboxStr.split(',').map(Number);
        const n = grid_size || slopeGrid.length;
        const dx = (maxx - minx) / n;
        const dy = (maxy - miny) / n;

        const ranges = slopeRanges || [];
        const features = [];

        for (let r = 0; r < slopeGrid.length; r++) {
            for (let c = 0; c < slopeGrid[r].length; c++) {
                const val = slopeGrid[r][c];
                // Find matching range color
                let fillColor = '#888888';
                for (const rng of ranges) {
                    if (val >= rng.min && val < rng.max) {
                        fillColor = rng.color;
                        break;
                    }
                }
                // Last range catches everything above
                if (val >= ranges[ranges.length - 1]?.min) {
                    fillColor = ranges[ranges.length - 1]?.color || fillColor;
                }

                const x0 = minx + c * dx;
                const y0 = miny + r * dy;
                features.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Polygon',
                        coordinates: [[
                            [x0, y0],
                            [x0 + dx, y0],
                            [x0 + dx, y0 + dy],
                            [x0, y0 + dy],
                            [x0, y0],
                        ]],
                    },
                    properties: {
                        slope: Math.round(val * 10) / 10,
                        color: fillColor,
                    },
                });
            }
        }

        const fc = { type: 'FeatureCollection', features };

        if (map.getSource('slope-cells')) {
            map.getSource('slope-cells').setData(fc);
            // Update paint if needed
            map.setPaintProperty('slope-cells', 'fill-color', ['get', 'color']);
        } else {
            map.addSource('slope-cells', { type: 'geojson', data: fc });
            map.addLayer({
                id: 'slope-cells',
                type: 'fill',
                source: 'slope-cells',
                paint: {
                    'fill-color': ['get', 'color'],
                    'fill-opacity': 0.7,
                },
            });
            map.addLayer({
                id: 'slope-cells-outline',
                type: 'line',
                source: 'slope-cells',
                paint: {
                    'line-color': 'rgba(0,0,0,0.1)',
                    'line-width': 0.3,
                },
            });

            // Click popup with slope value
            map.on('click', 'slope-cells', (e) => {
                const props = e.features[0]?.properties || {};
                new maplibregl.Popup({ className: 'dark-popup' })
                    .setLngLat(e.lngLat)
                    .setHTML(`<div class="popup-content"><strong>Pendiente:</strong> ${props.slope}%</div>`)
                    .addTo(map);
            });
            map.on('mouseenter', 'slope-cells', () => { map.getCanvas().style.cursor = 'pointer'; });
            map.on('mouseleave', 'slope-cells', () => { map.getCanvas().style.cursor = ''; });
        }
    }, [slopeData, slopeRanges, loaded]);

    // ── Rectangle drawing logic ────────────────────────────────────
    useEffect(() => {
        const map = mapRef.current;
        if (!map || !loaded) return;

        const canvas = map.getCanvas();

        if (drawingMode) {
            map.dragPan.disable();
            canvas.style.cursor = 'crosshair';
        } else {
            map.dragPan.enable();
            canvas.style.cursor = '';
            return;
        }

        const mousedown = (e) => {
            e.preventDefault();
            const lngLat = map.unproject([e.offsetX, e.offsetY]);
            drawStartRef.current = lngLat;
        };

        const mousemove = (e) => {
            if (!drawStartRef.current) return;
            const start = drawStartRef.current;
            const current = map.unproject([e.offsetX, e.offsetY]);

            const rect = {
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [[
                        [start.lng, start.lat],
                        [current.lng, start.lat],
                        [current.lng, current.lat],
                        [start.lng, current.lat],
                        [start.lng, start.lat],
                    ]],
                },
            };

            const fc = { type: 'FeatureCollection', features: [rect] };
            if (map.getSource('draw-rect')) {
                map.getSource('draw-rect').setData(fc);
            } else {
                map.addSource('draw-rect', { type: 'geojson', data: fc });
                map.addLayer({
                    id: 'draw-rect-fill', type: 'fill', source: 'draw-rect',
                    paint: { 'fill-color': '#00d2ff', 'fill-opacity': 0.15 },
                });
                map.addLayer({
                    id: 'draw-rect-line', type: 'line', source: 'draw-rect',
                    paint: {
                        'line-color': '#00d2ff', 'line-width': 2,
                        'line-dasharray': [4, 2],
                    },
                });
            }
        };

        const mouseup = (e) => {
            if (!drawStartRef.current) return;
            const start = drawStartRef.current;
            const end = map.unproject([e.offsetX, e.offsetY]);
            drawStartRef.current = null;

            const minx = Math.min(start.lng, end.lng);
            const miny = Math.min(start.lat, end.lat);
            const maxx = Math.max(start.lng, end.lng);
            const maxy = Math.max(start.lat, end.lat);

            // Only accept if it's a meaningful rectangle
            if (Math.abs(maxx - minx) > 0.001 && Math.abs(maxy - miny) > 0.001) {
                const bboxStr = `${minx},${miny},${maxx},${maxy}`;
                onRectangleDrawn?.(bboxStr);
            }
        };

        canvas.addEventListener('mousedown', mousedown);
        canvas.addEventListener('mousemove', mousemove);
        canvas.addEventListener('mouseup', mouseup);

        return () => {
            canvas.removeEventListener('mousedown', mousedown);
            canvas.removeEventListener('mousemove', mousemove);
            canvas.removeEventListener('mouseup', mouseup);
            if (map.dragPan) map.dragPan.enable();
            canvas.style.cursor = '';
        };
    }, [drawingMode, loaded, onRectangleDrawn]);

    return (
        <div className={`map-container ${drawingMode ? 'drawing-mode' : ''}`} ref={containerRef}>
            {!loaded && (
                <div className="map-loading">
                    <div className="map-loading-spinner" />
                    <span>Cargando mapa…</span>
                </div>
            )}
            <SlopeLegend ranges={slopeRanges} visible={showSlopeLegend && slopeData} />
        </div>
    );
}
