import { useState, useCallback, useEffect, useRef } from 'react';
import './Toast.css';

let toastId = 0;

// Global toast function - will be set by ToastProvider
let globalAddToast = null;

export function showToast(message, type = 'error', duration = 5000) {
    if (globalAddToast) {
        globalAddToast(message, type, duration);
    }
}

export default function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'error', duration = 5000) => {
        const id = ++toastId;
        setToasts((prev) => [...prev, { id, message, type, duration, exiting: false }]);

        setTimeout(() => {
            setToasts((prev) =>
                prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
            );
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, 300);
        }, duration);
    }, []);

    // Register global toast
    useEffect(() => {
        globalAddToast = addToast;
        return () => { globalAddToast = null; };
    }, [addToast]);

    const dismiss = (id) => {
        setToasts((prev) =>
            prev.map((t) => (t.id === id ? { ...t, exiting: true } : t))
        );
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id));
        }, 300);
    };

    const icons = {
        error: '⚠️',
        success: '✅',
        info: 'ℹ️',
        warning: '⚡',
    };

    return (
        <>
            {children}
            <div className="toast-container">
                {toasts.map((t) => (
                    <div
                        key={t.id}
                        className={`toast toast-${t.type} ${t.exiting ? 'toast-exit' : ''}`}
                        onClick={() => dismiss(t.id)}
                    >
                        <span className="toast-icon">{icons[t.type] || icons.error}</span>
                        <span className="toast-message">{t.message}</span>
                        <button className="toast-close">✕</button>
                    </div>
                ))}
            </div>
        </>
    );
}
