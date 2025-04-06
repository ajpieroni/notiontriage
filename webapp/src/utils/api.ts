export function getApiUrl(path: string) {
  if (typeof window === 'undefined') {
    // Server-side
    return process.env.VERCEL_URL
      ? `https://${process.env.VERCEL_URL}${path}`
      : `http://localhost:${process.env.PORT || 3000}${path}`;
  }
  
  // Client-side
  return path;
} 