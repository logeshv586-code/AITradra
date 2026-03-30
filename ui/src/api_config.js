// Centralized API and WebSocket configuration for AXIOM V4
// Defaults to the same host/port as the frontend, but allows override via VITE_API_URL env var during build

const getBaseUrl = () => {
    // If VITE_API_URL is set (e.g. in .env.local or build time), use it
    if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL;
    }
    // Otherwise fallback to the current window location (perfect for unified port mode)
    return window.location.origin;
};

const getWsUrl = () => {
    const baseUrl = getBaseUrl();
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    if (baseUrl.startsWith('http')) {
        return baseUrl.replace(/^http/, 'ws');
    }
    
    // Fallback for relative URLs
    return `${wsProto}//${window.location.host}`;
};

export const API_BASE = getBaseUrl();
export const WS_BASE = getWsUrl();
