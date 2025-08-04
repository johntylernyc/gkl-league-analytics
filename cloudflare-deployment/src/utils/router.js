/**
 * Simple router for Cloudflare Workers
 */

export class Router {
  constructor() {
    this.routes = {
      GET: [],
      POST: [],
      PUT: [],
      DELETE: [],
      PATCH: []
    };
  }

  /**
   * Register a GET route
   */
  get(path, handler) {
    this.routes.GET.push({ path, handler, regex: this.pathToRegex(path) });
  }

  /**
   * Register a POST route
   */
  post(path, handler) {
    this.routes.POST.push({ path, handler, regex: this.pathToRegex(path) });
  }

  /**
   * Register a PUT route
   */
  put(path, handler) {
    this.routes.PUT.push({ path, handler, regex: this.pathToRegex(path) });
  }

  /**
   * Register a DELETE route
   */
  delete(path, handler) {
    this.routes.DELETE.push({ path, handler, regex: this.pathToRegex(path) });
  }

  /**
   * Register a PATCH route
   */
  patch(path, handler) {
    this.routes.PATCH.push({ path, handler, regex: this.pathToRegex(path) });
  }

  /**
   * Convert path pattern to regex
   */
  pathToRegex(path) {
    // Convert :param to named capture groups
    const pattern = path
      .replace(/\//g, '\\/')
      .replace(/:([^\/]+)/g, '(?<$1>[^\/]+)');
    return new RegExp(`^${pattern}$`);
  }

  /**
   * Handle incoming request
   */
  async handle(request) {
    const url = new URL(request.url);
    const method = request.method;
    const pathname = url.pathname;

    // Get routes for this method
    const methodRoutes = this.routes[method] || [];

    // Find matching route
    for (const route of methodRoutes) {
      const match = pathname.match(route.regex);
      if (match) {
        // Add params to request
        request.params = match.groups || {};
        request.query = Object.fromEntries(url.searchParams);
        
        // Call handler
        return await route.handler(request);
      }
    }

    // No route found
    return new Response('Not Found', { status: 404 });
  }
}