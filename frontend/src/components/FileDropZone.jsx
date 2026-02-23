import { useState, useCallback } from 'react';
import './FileDropZone.css';

export default function FileDropZone({ onFileLoad }) {
    const [dragging, setDragging] = useState(false);
    const [fileName, setFileName] = useState(null);

    const handleDrag = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDragIn = useCallback((e) => {
        handleDrag(e);
        setDragging(true);
    }, []);

    const handleDragOut = useCallback((e) => {
        handleDrag(e);
        setDragging(false);
    }, []);

    const processFile = useCallback((file) => {
        if (!file) return;
        setFileName(file.name);
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const geojson = JSON.parse(e.target.result);
                onFileLoad?.(geojson, file.name);
            } catch {
                alert('Error: El archivo no es un GeoJSON válido.');
            }
        };
        reader.readAsText(file);
    }, [onFileLoad]);

    const handleDrop = useCallback((e) => {
        handleDrag(e);
        setDragging(false);
        const file = e.dataTransfer?.files?.[0];
        processFile(file);
    }, [processFile]);

    const handleClick = useCallback(() => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.geojson,.json,.kml';
        input.onchange = (e) => processFile(e.target.files[0]);
        input.click();
    }, [processFile]);

    return (
        <div
            className={`dropzone ${dragging ? 'dropzone--active' : ''}`}
            onDragEnter={handleDragIn}
            onDragOver={handleDrag}
            onDragLeave={handleDragOut}
            onDrop={handleDrop}
            onClick={handleClick}
        >
            <div className="dropzone-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
            </div>
            {fileName ? (
                <span className="dropzone-file">{fileName}</span>
            ) : (
                <>
                    <span className="dropzone-label">Arrastra un GeoJSON / KML aquí</span>
                    <span className="dropzone-sublabel">o haz clic para seleccionar</span>
                </>
            )}
        </div>
    );
}
