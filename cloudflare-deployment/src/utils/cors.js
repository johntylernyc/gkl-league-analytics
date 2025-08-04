/**
 * CORS configuration for Cloudflare Workers
 */

export const corsHeaders = {
  'Access-Control-Allow-Origin': '*', // Configure with your domain in production
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Max-Age': '86400',
};

export function handleCORS() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders
  });
}