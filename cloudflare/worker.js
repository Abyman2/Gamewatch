/**
 * GameWatch Cloudflare D1 Edge Worker Proxy (Zero-Latency API)
 * ==========================================================
 * Deploy this Worker to your Cloudflare account to proxy D1 SQL queries
 * with sub-10ms response times directly at Cloudflare Edge!
 */

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
      });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" }
      });
    }

    try {
      const { sql, params = [] } = await request.json();
      if (!sql) {
        return new Response(JSON.stringify({ error: "Missing SQL statement" }), {
          status: 400,
          headers: { "Content-Type": "application/json" }
        });
      }

      // Execute on bound Cloudflare D1 database
      const stmt = env.DB.prepare(sql).bind(...params);
      const result = await stmt.all();

      return new Response(JSON.stringify({
        success: true,
        rows: result.results || [],
        meta: result.meta || {}
      }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*"
        }
      });
    } catch (err) {
      return new Response(JSON.stringify({
        success: false,
        error: err.message
      }), {
        status: 500,
        headers: { "Content-Type": "application/json" }
      });
    }
  }
};
