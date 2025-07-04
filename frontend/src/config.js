const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // WebSocket URL derived from API URL
  get wsUrl() {
    const url = new URL(this.apiUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws/sensors`;
  },
  
  // Add other configuration values here
  chartRefreshRate: import.meta.env.VITE_CHART_REFRESH_RATE || 1000,
  chartTimespan: import.meta.env.VITE_CHART_TIMESPAN || 5,
};

export default config;