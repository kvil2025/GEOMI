import { useState, useEffect, useCallback } from 'react';
import './LoginScreen.css';

export default function LoginScreen({ onLogin }) {
    const [authConfig, setAuthConfig] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    // Fetch auth config from backend
    useEffect(() => {
        fetch('/auth/config')
            .then(res => res.json())
            .then(config => {
                setAuthConfig(config);
                if (!config.authRequired) {
                    // No auth required, auto-login
                    onLogin({ email: 'local', name: 'Usuario Local', authorized: true });
                }
                setLoading(false);
            })
            .catch(() => {
                // Backend not available, allow access (local dev)
                onLogin({ email: 'local', name: 'Usuario Local', authorized: true });
                setLoading(false);
            });
    }, [onLogin]);

    // Load Google Identity Services script
    useEffect(() => {
        if (!authConfig?.googleClientId) return;

        const script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onload = () => {
            window.google.accounts.id.initialize({
                client_id: authConfig.googleClientId,
                callback: handleCredentialResponse,
                auto_select: true,
            });
            window.google.accounts.id.renderButton(
                document.getElementById('google-signin-btn'),
                {
                    theme: 'filled_black',
                    size: 'large',
                    shape: 'pill',
                    text: 'signin_with',
                    locale: 'es',
                    width: 300,
                }
            );
        };
        document.head.appendChild(script);

        return () => {
            document.head.removeChild(script);
        };
    }, [authConfig]);

    const handleCredentialResponse = useCallback(async (response) => {
        setLoading(true);
        setError(null);

        try {
            const res = await fetch('/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ credential: response.credential }),
            });

            const data = await res.json();

            if (data.authorized) {
                onLogin(data);
            } else {
                setError(data.message || 'Acceso denegado');
            }
        } catch (err) {
            setError('Error al verificar credenciales');
        }

        setLoading(false);
    }, [onLogin]);

    if (loading) {
        return (
            <div className="login-screen">
                <div className="login-card">
                    <div className="login-spinner" />
                    <p className="login-loading-text">Conectando...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="login-screen">
            <div className="login-card">
                {/* Logo */}
                <div className="login-logo">
                    <svg width="56" height="56" viewBox="0 0 40 40" fill="none">
                        <circle cx="20" cy="20" r="18" stroke="url(#loginGrad)" strokeWidth="2.5" fill="none"/>
                        <path d="M20 6 C12 12, 10 18, 14 24 C18 30, 26 30, 30 24 C34 18, 28 12, 20 6Z"
                              fill="url(#loginGrad)" opacity="0.15"/>
                        <path d="M12 22 Q16 18 20 20 Q24 22 28 18" stroke="url(#loginGrad)"
                              strokeWidth="1.5" fill="none"/>
                        <path d="M14 26 Q18 23 22 25 Q26 27 30 24" stroke="url(#loginGrad)"
                              strokeWidth="1.2" fill="none" opacity="0.6"/>
                        <defs>
                            <linearGradient id="loginGrad" x1="0" y1="0" x2="40" y2="40">
                                <stop offset="0%" stopColor="#0ea5e9"/>
                                <stop offset="100%" stopColor="#8b5cf6"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>

                {/* Title */}
                <h1 className="login-title">GeologgIA Map</h1>
                <p className="login-subtitle">Inteligencia Geológica</p>

                {/* Divider */}
                <div className="login-divider" />

                {/* Description */}
                <p className="login-description">
                    Acceso restringido a usuarios autorizados.
                    <br />Inicia sesión con tu cuenta de Google.
                </p>

                {/* Google Sign-In Button */}
                <div id="google-signin-btn" className="login-google-btn" />

                {/* Error */}
                {error && (
                    <div className="login-error">
                        <span>⚠️</span>
                        <p>{error}</p>
                    </div>
                )}

                {/* Footer */}
                <div className="login-footer">
                    <p>GEOLOGGÍA LTDA · Atacama, Chile</p>
                </div>
            </div>
        </div>
    );
}
