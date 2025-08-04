/**
 * Error handling for Cloudflare Workers
 */

import { corsHeaders } from './cors.js';

export function handleError(error, env) {
  console.error('Error occurred:', error);

  // Log to database if available
  if (env?.DB) {
    try {
      env.DB.prepare(
        `INSERT INTO error_log (timestamp, error_message, stack_trace) 
         VALUES (?, ?, ?)`
      ).bind(
        new Date().toISOString(),
        error.message,
        error.stack
      ).run();
    } catch (logError) {
      console.error('Failed to log error to database:', logError);
    }
  }

  // Determine status code
  let status = 500;
  let message = 'Internal Server Error';

  if (error.message.includes('not found')) {
    status = 404;
    message = 'Resource not found';
  } else if (error.message.includes('unauthorized')) {
    status = 401;
    message = 'Unauthorized';
  } else if (error.message.includes('forbidden')) {
    status = 403;
    message = 'Forbidden';
  } else if (error.message.includes('bad request')) {
    status = 400;
    message = 'Bad request';
  }

  // Return error response
  return new Response(JSON.stringify({
    error: message,
    message: env?.ENVIRONMENT === 'development' ? error.message : undefined,
    timestamp: new Date().toISOString()
  }), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders
    }
  });
}