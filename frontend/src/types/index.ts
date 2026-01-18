// User types
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_approved: boolean;
  role: 'admin' | 'user';
  nas_path: string | null;
  storage_quota_gb: number;
  storage_used_bytes: number;
  settings: UserSettings;
  created_at: string;
  last_login: string | null;
}

export interface UserSettings {
  nas_paths: string[];
  face_recognition_enabled: boolean;
  clip_enabled: boolean;
  yolo_enabled: boolean;
  auto_index: boolean;
  index_interval_hours: number;
  thumbnail_quality: number;
  video_thumbnail_count: number;
  dark_mode: boolean;
  grid_size: 'small' | 'medium' | 'large';
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

// Auth types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Media types
export interface Media {
  id: string;
  filename: string;
  original_path: string;
  relative_path: string | null;
  file_size: number | null;
  mime_type: string | null;
  media_type: 'photo' | 'video';
  width: number | null;
  height: number | null;
  duration: number | null;
  thumbnail_small: string | null;
  thumbnail_medium: string | null;
  thumbnail_large: string | null;
  taken_at: string | null;
  camera_make: string | null;
  camera_model: string | null;
  latitude: number | null;
  longitude: number | null;
  location_name: string | null;
  is_favorite: boolean;
  is_hidden: boolean;
  created_at: string;
  tags: string[];
  faces_count: number;
}

export interface MediaFilters {
  media_type?: 'photo' | 'video';
  favorites_only?: boolean;
  hidden?: boolean;
  year?: number;
  month?: number;
}

// Album types
export interface Album {
  id: string;
  name: string;
  description: string | null;
  cover_media_id: string | null;
  cover_thumbnail: string | null;
  media_count: number;
  is_shared: boolean;
  share_token: string | null;
  created_at: string;
  updated_at: string;
}

export interface SmartAlbum {
  id: string;
  name: string;
  description: string | null;
  query: string;
  filters: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// People types
export interface Person {
  id: string;
  name: string | null;
  is_named: boolean;
  face_count: number;
  cover_face_thumbnail: string | null;
  created_at: string;
}

export interface Face {
  id: string;
  media_id: string;
  person_id: string | null;
  person_name: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number | null;
  thumbnail: string | null;
}

// Search types
export interface SearchQuery {
  query: string;
  filters?: Record<string, unknown>;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  results: Media[];
  suggestions: string[];
}

export interface AskResponse {
  query: string;
  response: string;
  action: string | null;
  action_result: Record<string, unknown> | null;
  media: Media[] | null;
}

// Job types
export interface Job {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  total_items: number;
  processed_items: number;
  failed_items: number;
  progress: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

// Stats types
export interface UserStats {
  total_photos: number;
  total_videos: number;
  total_albums: number;
  total_people: number;
  storage_used_bytes: number;
  storage_quota_bytes: number;
  photos_by_year: Record<number, number>;
  photos_by_month: Record<string, number>;
}

export interface SystemStats {
  total_users: number;
  active_users: number;
  pending_users: number;
  total_media: number;
  total_storage_bytes: number;
  jobs_pending: number;
  jobs_running: number;
}

// Pagination
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: T[];
}

// Timeline
export interface TimelineEntry {
  date: string;
  count: number;
}

// Map
export interface MapMarker {
  id: string;
  latitude: number;
  longitude: number;
  thumbnail: string | null;
  taken_at: string | null;
}
