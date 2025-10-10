// Debug helper to check API configuration
export function debugApiConfig() {
  console.log('=== API Configuration Debug ===');
  console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
  console.log('Mode:', import.meta.env.MODE);
  console.log('Dev:', import.meta.env.DEV);
  console.log('Prod:', import.meta.env.PROD);
  console.log('All env vars:', import.meta.env);
  
  const testEndpoint = 'analyze-document';
  const base = import.meta.env.VITE_API_BASE_URL?.trim();
  const cleanEndpoint = testEndpoint.startsWith('/') ? testEndpoint.slice(1) : testEndpoint;
  
  if (base) {
    const url = `${base.replace(/\/$/, '')}/${cleanEndpoint}`;
    console.log('✅ Would call:', url);
  } else {
    const url = `/${cleanEndpoint}`;
    console.log('❌ VITE_API_BASE_URL not set! Would call:', url, '(This will fail!)');
  }
  console.log('===============================');
}
