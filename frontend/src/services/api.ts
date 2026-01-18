import axios, { AxiosError, AxiosInstance } from 'axios';
import { useAuthStore } from '@/store/authStore';

const API_BASE_URL = '/api';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && originalRequest) {
      const refreshToken = useAuthStore.getState().refreshToken;
      
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          useAuthStore.getState().setTokens(access_token, refresh_token);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          useAuthStore.getState().logout();
          window.location.href = '/login';
        }
      } else {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;

// Auth API
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  
  register: (email: string, password: string, full_name?: string) =>
    api.post('/auth/register', { email, password, full_name }),
  
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
  
  verifyEmail: (token: string) =>
    api.post('/auth/verify-email', { token }),
  
  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),
  
  resetPassword: (token: string, new_password: string) =>
    api.post('/auth/reset-password', { token, new_password }),
  
  me: () => api.get('/auth/me'),
  
  logout: () => api.post('/auth/logout'),
};

// Users API
export const usersApi = {
  getProfile: () => api.get('/users/me'),
  
  updateProfile: (data: { full_name?: string; settings?: Record<string, unknown> }) =>
    api.put('/users/me', data),
  
  getSettings: () => api.get('/users/me/settings'),
  
  updateSettings: (settings: Record<string, unknown>) =>
    api.put('/users/me/settings', settings),
  
  getStats: () => api.get('/users/me/stats'),
  
  changePassword: (current_password: string, new_password: string) =>
    api.put('/users/me/password', null, { params: { current_password, new_password } }),
  
  // Admin
  listUsers: (params?: { skip?: number; limit?: number; search?: string; status_filter?: string }) =>
    api.get('/users/', { params }),
  
  getPendingUsers: () => api.get('/users/pending'),
  
  getUser: (userId: string) => api.get(`/users/${userId}`),
  
  updateUser: (userId: string, data: Record<string, unknown>) =>
    api.put(`/users/${userId}`, data),
  
  approveUser: (userId: string) => api.post(`/users/${userId}/approve`),
  
  rejectUser: (userId: string) => api.post(`/users/${userId}/reject`),
  
  deleteUser: (userId: string) => api.delete(`/users/${userId}`),
};

// Media API
export const mediaApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    media_type?: string;
    sort_by?: string;
    sort_order?: string;
    favorites_only?: boolean;
    hidden?: boolean;
    year?: number;
    month?: number;
  }) => api.get('/media/', { params }),
  
  get: (mediaId: string) => api.get(`/media/${mediaId}`),
  
  update: (mediaId: string, data: { is_favorite?: boolean; is_hidden?: boolean }) =>
    api.put(`/media/${mediaId}`, data),
  
  delete: (mediaId: string, permanent?: boolean) =>
    api.delete(`/media/${mediaId}`, { params: { permanent } }),
  
  bulkAction: (media_ids: string[], action: string) =>
    api.post('/media/bulk', { media_ids, action }),
  
  getTimeline: () => api.get('/media/timeline'),
  
  getMapData: () => api.get('/media/map'),
  
  getFaces: (mediaId: string) => api.get(`/media/${mediaId}/faces`),
  
  getTrash: (params?: { page?: number; page_size?: number }) =>
    api.get('/media/trash/', { params }),
  
  restoreFromTrash: (media_ids: string[]) =>
    api.post('/media/trash/restore', media_ids),
  
  emptyTrash: () => api.delete('/media/trash/empty'),
  
  getThumbnailUrl: (mediaId: string, size: 'small' | 'medium' | 'large' = 'medium') =>
    `/api/media/${mediaId}/thumbnail/${size}`,
  
  getFileUrl: (mediaId: string) => `/api/media/${mediaId}/file`,
};

// Albums API
export const albumsApi = {
  list: () => api.get('/albums/'),
  
  get: (albumId: string) => api.get(`/albums/${albumId}`),
  
  create: (name: string, description?: string) =>
    api.post('/albums/', { name, description }),
  
  update: (albumId: string, data: { name?: string; description?: string; cover_media_id?: string }) =>
    api.put(`/albums/${albumId}`, data),
  
  delete: (albumId: string) => api.delete(`/albums/${albumId}`),
  
  getMedia: (albumId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/albums/${albumId}/media`, { params }),
  
  addMedia: (albumId: string, media_ids: string[]) =>
    api.post(`/albums/${albumId}/media`, { media_ids }),
  
  removeMedia: (albumId: string, media_ids: string[]) =>
    api.delete(`/albums/${albumId}/media`, { params: { media_ids } }),
  
  share: (albumId: string) => api.post(`/albums/${albumId}/share`),
  
  unshare: (albumId: string) => api.delete(`/albums/${albumId}/share`),
  
  // Smart albums
  listSmart: () => api.get('/albums/smart/'),
  
  getSmart: (albumId: string) => api.get(`/albums/smart/${albumId}`),
  
  createSmart: (name: string, query: string, description?: string, filters?: Record<string, unknown>) =>
    api.post('/albums/smart/', { name, query, description, filters }),
  
  deleteSmart: (albumId: string) => api.delete(`/albums/smart/${albumId}`),
  
  getSmartMedia: (albumId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/albums/smart/${albumId}/media`, { params }),
};

// People API
export const peopleApi = {
  list: (params?: { named_only?: boolean; min_faces?: number }) =>
    api.get('/people/', { params }),
  
  get: (personId: string) => api.get(`/people/${personId}`),
  
  update: (personId: string, name: string) =>
    api.put(`/people/${personId}`, { name }),
  
  delete: (personId: string) => api.delete(`/people/${personId}`),
  
  getMedia: (personId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/people/${personId}/media`, { params }),
  
  merge: (source_person_ids: string[], target_person_id: string) =>
    api.post('/people/merge', { source_person_ids, target_person_id }),
  
  getUnassignedFaces: (limit?: number) =>
    api.get('/people/faces/unassigned', { params: { limit } }),
  
  assignFace: (faceId: string, person_id: string) =>
    api.put(`/people/faces/${faceId}/assign`, { person_id }),
  
  unassignFace: (faceId: string) =>
    api.put(`/people/faces/${faceId}/unassign`),
  
  createPersonFromFace: (faceId: string, name?: string) =>
    api.post(`/people/faces/${faceId}/create-person`, null, { params: { name } }),
};

// Search API
export const searchApi = {
  search: (query: string, filters?: Record<string, unknown>, page?: number, page_size?: number) =>
    api.post('/search/', { query, filters, page, page_size }),
  
  getSuggestions: (q: string) =>
    api.get('/search/suggestions', { params: { q } }),
  
  getTags: () => api.get('/search/tags'),
  
  searchByTag: (tag_name: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/search/by-tag/${tag_name}`, { params }),
  
  searchByDate: (date: string) =>
    api.get(`/search/by-date/${date}`),
  
  searchByLocation: (lat: number, lng: number, radius_km?: number) =>
    api.get('/search/by-location', { params: { lat, lng, radius_km } }),
  
  ask: (query: string, context?: Record<string, unknown>) =>
    api.post('/search/ask', { query, context }),
  
  findSimilar: (mediaId: string, limit?: number) =>
    api.get(`/search/similar/${mediaId}`, { params: { limit } }),
};

// Jobs API
export const jobsApi = {
  list: (params?: { status_filter?: string; skip?: number; limit?: number }) =>
    api.get('/jobs/', { params }),
  
  get: (jobId: string) => api.get(`/jobs/${jobId}`),
  
  triggerScan: () => api.post('/jobs/scan'),
  
  triggerFaceProcessing: () => api.post('/jobs/process-faces'),
  
  triggerClipProcessing: () => api.post('/jobs/process-clip'),
  
  triggerYoloProcessing: () => api.post('/jobs/process-yolo'),
  
  cancel: (jobId: string) => api.post(`/jobs/${jobId}/cancel`),
};

// Admin API
export const adminApi = {
  getStats: () => api.get('/admin/stats'),
  
  getSettings: () => api.get('/admin/settings'),
  
  listJobs: (params?: { status_filter?: string; job_type?: string; skip?: number; limit?: number }) =>
    api.get('/admin/jobs', { params }),
  
  getJob: (jobId: string) => api.get(`/admin/jobs/${jobId}`),
  
  cancelJob: (jobId: string) => api.post(`/admin/jobs/${jobId}/cancel`),
  
  triggerReindex: (user_id?: string) =>
    api.post('/admin/reindex', null, { params: { user_id } }),
  
  triggerAiProcessing: (process_type: string, user_id?: string) =>
    api.post('/admin/process-ai', null, { params: { process_type, user_id } }),
  
  getAuditLogs: (params?: { user_id?: string; action?: string; skip?: number; limit?: number }) =>
    api.get('/admin/audit-logs', { params }),
  
  healthCheck: () => api.get('/admin/health'),
};
