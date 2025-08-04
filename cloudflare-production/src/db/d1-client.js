/**
 * D1 Database client for Cloudflare Workers
 */

export class D1Client {
  constructor(db) {
    this.db = db;
  }

  /**
   * Execute a SELECT query and return all results
   */
  async all(query, params = []) {
    try {
      const stmt = this.db.prepare(query);
      const result = await stmt.bind(...params).all();
      return result.results || [];
    } catch (error) {
      console.error('Database query error:', error);
      throw new Error(`Database query failed: ${error.message}`);
    }
  }

  /**
   * Execute a SELECT query and return first result
   */
  async first(query, params = []) {
    try {
      const stmt = this.db.prepare(query);
      const result = await stmt.bind(...params).first();
      return result;
    } catch (error) {
      console.error('Database query error:', error);
      throw new Error(`Database query failed: ${error.message}`);
    }
  }

  /**
   * Execute an INSERT, UPDATE, or DELETE query
   */
  async run(query, params = []) {
    try {
      const stmt = this.db.prepare(query);
      const result = await stmt.bind(...params).run();
      return result;
    } catch (error) {
      console.error('Database execution error:', error);
      throw new Error(`Database execution failed: ${error.message}`);
    }
  }

  /**
   * Execute multiple queries in a transaction
   */
  async batch(queries) {
    try {
      const statements = queries.map(({ query, params = [] }) => 
        this.db.prepare(query).bind(...params)
      );
      const results = await this.db.batch(statements);
      return results;
    } catch (error) {
      console.error('Database batch error:', error);
      throw new Error(`Database batch operation failed: ${error.message}`);
    }
  }

  /**
   * Get paginated results
   */
  async paginate(query, page = 1, limit = 20, params = []) {
    const offset = (page - 1) * limit;
    const paginatedQuery = `${query} LIMIT ? OFFSET ?`;
    const allParams = [...params, limit, offset];
    
    const results = await this.all(paginatedQuery, allParams);
    
    // Get total count - simplified to avoid regex issues
    let countQuery = query;
    // Remove GROUP BY clause for counting
    const groupByIndex = countQuery.toUpperCase().indexOf('GROUP BY');
    if (groupByIndex !== -1) {
      countQuery = countQuery.substring(0, groupByIndex);
    }
    // Remove ORDER BY clause
    const orderByIndex = countQuery.toUpperCase().indexOf('ORDER BY');
    if (orderByIndex !== -1) {
      countQuery = countQuery.substring(0, orderByIndex);
    }
    
    // Wrap in a count query
    countQuery = `SELECT COUNT(*) as count FROM (${countQuery}) as subquery`;
    
    const countResult = await this.first(countQuery, params);
    const total = countResult?.count || 0;
    
    return {
      data: results,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    };
  }
}