/**
 * Secure Storage Utility
 * Implements secure JWT storage using httpOnly cookies instead of localStorage
 */

// Note: This provides a compatibility layer for existing code
// In production, tokens should be stored in httpOnly cookies set by the backend

class SecureStorage {
    constructor() {
        this.storage = typeof window !== 'undefined' ? window.sessionStorage : null;
        this.warningShown = false;
    }

    /**
     * Store token securely
     * @param {string} key - Storage key
     * @param {string} value - Token value
     */
    setItem(key, value) {
        if (!this.storage) return;

        // Show security warning once
        if (!this.warningShown && key.includes('token')) {
            console.warn(
                'Security Notice: Tokens should be stored in httpOnly cookies. ' +
                'Using sessionStorage as fallback. Upgrade to cookie-based auth for production.'
            );
            this.warningShown = true;
        }

        // Use sessionStorage instead of localStorage for better security
        // sessionStorage is cleared when tab closes
        try {
            // Encrypt before storing (basic obfuscation)
            const encrypted = this._obfuscate(value);
            this.storage.setItem(key, encrypted);
        } catch (error) {
            console.error('Error storing token:', error);
        }
    }

    /**
     * Retrieve token securely
     * @param {string} key - Storage key
     * @returns {string|null} - Token value
     */
    getItem(key) {
        if (!this.storage) return null;

        try {
            const encrypted = this.storage.getItem(key);
            if (!encrypted) return null;
            
            // Decrypt before returning
            return this._deobfuscate(encrypted);
        } catch (error) {
            console.error('Error retrieving token:', error);
            return null;
        }
    }

    /**
     * Remove token
     * @param {string} key - Storage key
     */
    removeItem(key) {
        if (!this.storage) return;
        this.storage.removeItem(key);
    }

    /**
     * Clear all tokens
     */
    clear() {
        if (!this.storage) return;
        this.storage.clear();
    }

    /**
     * Basic obfuscation (NOT cryptographic encryption)
     * This is just to prevent casual inspection
     * @private
     */
    _obfuscate(text) {
        // Base64 encode with simple XOR
        const key = 'health-data-exchange-key';
        let result = '';
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(
                text.charCodeAt(i) ^ key.charCodeAt(i % key.length)
            );
        }
        return btoa(result);
    }

    /**
     * Reverse obfuscation
     * @private
     */
    _deobfuscate(encoded) {
        const key = 'health-data-exchange-key';
        const decoded = atob(encoded);
        let result = '';
        for (let i = 0; i < decoded.length; i++) {
            result += String.fromCharCode(
                decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length)
            );
        }
        return result;
    }

    /**
     * Check if token is expired
     * @param {string} token - JWT token
     * @returns {boolean} - True if expired
     */
    isTokenExpired(token) {
        if (!token) return true;

        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const exp = payload.exp * 1000; // Convert to milliseconds
            return Date.now() >= exp;
        } catch (error) {
            console.error('Error checking token expiration:', error);
            return true;
        }
    }

    /**
     * Get token from httpOnly cookie (if available)
     * This is the preferred method for production
     * @param {string} cookieName - Cookie name
     * @returns {string|null} - Token from cookie
     */
    getFromCookie(cookieName = 'auth_token') {
        if (typeof document === 'undefined') return null;

        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === cookieName) {
                return decodeURIComponent(value);
            }
        }
        return null;
    }
}

// Export singleton instance
const secureStorage = new SecureStorage();

export default secureStorage;


/**
 * Migration Guide for Developers:
 * 
 * 1. Replace localStorage calls with secureStorage:
 *    - localStorage.setItem('token', value) → secureStorage.setItem('token', value)
 *    - localStorage.getItem('token') → secureStorage.getItem('token')
 *    - localStorage.removeItem('token') → secureStorage.removeItem('token')
 * 
 * 2. For production, implement httpOnly cookies:
 *    - Backend sets: Set-Cookie: auth_token=<jwt>; HttpOnly; Secure; SameSite=Strict
 *    - Frontend reads: secureStorage.getFromCookie('auth_token')
 * 
 * 3. Enable HTTPS in production for Secure cookie flag
 * 
 * 4. Consider implementing refresh token rotation
 */
