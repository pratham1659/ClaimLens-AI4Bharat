const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Proxy for all API routes to port 8000 (where backend is running)
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      logLevel: 'debug',
      onProxyReq: function(proxyReq) {
        // Add credentials support
        proxyReq.setHeader('Access-Control-Allow-Credentials', 'true');
      },
    })
  );

  // Proxy for auth routes (if they're not under /api)
  app.use(
    '/auth',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      logLevel: 'debug',
      onProxyReq: function(proxyReq) {
        // Add credentials support
        proxyReq.setHeader('Access-Control-Allow-Credentials', 'true');
      },
    })
  );

  // Proxy for admin-controls routes
  app.use(
    '/admin-controls',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      logLevel: 'debug',
      onProxyReq: function(proxyReq) {
        // Add credentials support
        proxyReq.setHeader('Access-Control-Allow-Credentials', 'true');
      },
    })
  );
};