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
