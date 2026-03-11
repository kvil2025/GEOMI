const API_BASE = '';  // Proxied by Vite in dev

async function request(url, options = {}) {
    const res = await fetch(`${API_BASE}${url}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function fetchConcessions(bbox) {
    return request(`/wfs/polygons?bbox=${encodeURIComponent(bbox)}`);
}

export async function fetchSlope(bbox, resolution = 10) {
    return request(`/dem/slope?bbox=${encodeURIComponent(bbox)}&resolution=${resolution}`);
}

export async function exportSlopeGeoJSON(bbox, resolution = 10) {
    return request(`/dem/slope/export?bbox=${encodeURIComponent(bbox)}&resolution=${resolution}`);
}

export async function postIntersection(geojson) {
    return request('/intersection/intersect', {
        method: 'POST',
        body: JSON.stringify(geojson),
    });
}

export async function postElevationProfile(lineGeojson, interval = 100) {
    return request(`/profile/profile?interval=${interval}`, {
        method: 'POST',
        body: JSON.stringify(lineGeojson),
    });
}

export async function fetchGeology(bbox, simplify = true) {
    return request(`/geology/features?bbox=${encodeURIComponent(bbox)}&simplify=${simplify}`);
}

export async function uploadShapefile(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }
    const res = await fetch(`${API_BASE}/shapefile/upload`, {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function exportShapefile(geojson, filename = 'export') {
    const res = await fetch(`${API_BASE}/shapefile/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ geojson, filename }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return { success: true };
}
