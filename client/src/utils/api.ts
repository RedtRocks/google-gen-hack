// API utilities for handling different environments

/**
 * Get the API base URL based on environment
 * In production (Vercel), API routes go directly to endpoints
 * In development, they're at the root with the dev server
 */
export const getApiUrl = (endpoint: string): string => {
  // Check if we're in production (Vercel)
  const isProduction = import.meta.env.PROD;
  
  // Remove leading slash if present
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  
  // Same path for both prod and dev - Vercel routes API endpoints to serverless function
  return `/${cleanEndpoint}`;
};
