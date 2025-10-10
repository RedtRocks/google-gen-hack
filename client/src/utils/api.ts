// API utilities for handling different environments

/**
 * Get the API base URL based on environment
 * In production (Vercel), API routes are automatically available under /api/
 * In development, they're served by the FastAPI dev server at root
 */
export const getApiUrl = (endpoint: string): string => {
  const base = import.meta.env.VITE_API_BASE_URL?.trim();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  
  if (base) {
    // Ensure single slash between base and endpoint
    return `${base.replace(/\/$/, '')}/${cleanEndpoint}`;
  }
  // Fallback to relative path for local dev
  return `/${cleanEndpoint}`;
};
