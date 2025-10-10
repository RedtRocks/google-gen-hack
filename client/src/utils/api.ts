// API utilities for handling different environments

/**
 * Get the API base URL based on environment
 * In production (Vercel), API routes are prefixed with /api
 * In development, they're at the root
 */
export const getApiUrl = (endpoint: string): string => {
  // Check if we're in production (Vercel)
  const isProduction = import.meta.env.PROD;
  
  // Remove leading slash if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  
  // In production, prefix with /api/
  return isProduction ? `/api/${cleanEndpoint}` : `/${cleanEndpoint}`;
};
