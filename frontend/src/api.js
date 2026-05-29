import axios from 'axios';

const BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE });

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Token ${token}`;
  return cfg;
});

export const login = (username, password) =>
  api.post('/api/auth/login/', { username, password });

export const getSummary = () => api.get('/api/dashboard/summary/');
export const getRecords = (params) => api.get('/api/records/', { params });
export const getBatches = () => api.get('/api/batches/');
export const getAuditLog = (id) => api.get(`/api/records/${id}/audit/`);

export const approveRecord = (id) => api.post(`/api/records/${id}/approve/`);
export const rejectRecord = (id, reason) => api.post(`/api/records/${id}/reject/`, { reason });
export const flagRecord = (id, reason) => api.post(`/api/records/${id}/flag/`, { reason });
export const bulkApprove = (ids) => api.post('/api/records/bulk_approve/', { ids });

export const ingestSAP = (file, tenant) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post(`/api/ingest/sap/?tenant=${tenant}`, fd);
};
export const ingestUtility = (file, tenant) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post(`/api/ingest/utility/?tenant=${tenant}`, fd);
};
export const ingestTravel = (file, tenant) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post(`/api/ingest/travel/?tenant=${tenant}`, fd);
};

export default api;
