import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { usersApi, mediaApi, albumsApi, peopleApi } from '@/services/api';
import { UserStats, Media, Album, Person } from '@/types';
import {
  PhotoIcon,
  VideoCameraIcon,
  RectangleStackIcon,
  UserGroupIcon,
  CloudIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import PhotoGrid from '@/components/media/PhotoGrid';

export default function HomePage() {
  const { user } = useAuthStore();
  
  // Fetch user stats
  const { data: stats } = useQuery<UserStats>({
    queryKey: ['userStats'],
    queryFn: async () => {
      const response = await usersApi.getStats();
      return response.data;
    },
  });
  
  // Fetch recent photos
  const { data: recentMedia } = useQuery<{ items: Media[] }>({
    queryKey: ['recentMedia'],
    queryFn: async () => {
      const response = await mediaApi.list({ page_size: 12, sort_by: 'created_at', sort_order: 'desc' });
      return response.data;
    },
  });
  
  // Fetch albums
  const { data: albums } = useQuery<Album[]>({
    queryKey: ['albums'],
    queryFn: async () => {
      const response = await albumsApi.list();
      return response.data;
    },
  });
  
  // Fetch people
  const { data: people } = useQuery<Person[]>({
    queryKey: ['people'],
    queryFn: async () => {
      const response = await peopleApi.list({ named_only: true });
      return response.data;
    },
  });
  
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  return (
    <div className="space-y-8">
      {/* Welcome section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            Welcome back, {user?.full_name?.split(' ')[0] || 'there'}!
          </h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">
            Here's what's happening with your photos
          </p>
        </div>
      </div>
      
      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <PhotoIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_photos?.toLocaleString() || 0}</p>
              <p className="text-sm text-dark-500">Photos</p>
            </div>
          </div>
        </div>
        
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <VideoCameraIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_videos?.toLocaleString() || 0}</p>
              <p className="text-sm text-dark-500">Videos</p>
            </div>
          </div>
        </div>
        
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <RectangleStackIcon className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_albums || 0}</p>
              <p className="text-sm text-dark-500">Albums</p>
            </div>
          </div>
        </div>
        
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
              <UserGroupIcon className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats?.total_people || 0}</p>
              <p className="text-sm text-dark-500">People</p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Storage usage */}
      {stats && (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <CloudIcon className="w-6 h-6 text-dark-400" />
            <h2 className="text-lg font-semibold">Storage</h2>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{formatBytes(stats.storage_used_bytes)} used</span>
              <span>{formatBytes(stats.storage_quota_bytes)} total</span>
            </div>
            <div className="h-2 bg-dark-100 dark:bg-dark-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 rounded-full transition-all"
                style={{
                  width: `${Math.min(100, (stats.storage_used_bytes / stats.storage_quota_bytes) * 100)}%`,
                }}
              />
            </div>
          </div>
        </div>
      )}
      
      {/* Recent photos */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Photos</h2>
          <Link to="/photos" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
            View all
          </Link>
        </div>
        {recentMedia?.items && recentMedia.items.length > 0 ? (
          <PhotoGrid media={recentMedia.items} selectable={false} />
        ) : (
          <div className="card p-12 text-center">
            <SparklesIcon className="w-12 h-12 mx-auto text-dark-300 mb-4" />
            <h3 className="text-lg font-medium mb-2">No photos yet</h3>
            <p className="text-dark-500 mb-4">
              Start by uploading some photos or scanning your NAS folder
            </p>
            <Link to="/settings" className="btn-primary">
              Configure NAS
            </Link>
          </div>
        )}
      </div>
      
      {/* Albums preview */}
      {albums && albums.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Albums</h2>
            <Link to="/albums" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {albums.slice(0, 6).map((album) => (
              <Link
                key={album.id}
                to={`/albums/${album.id}`}
                className="card overflow-hidden group"
              >
                <div className="aspect-square bg-dark-100 dark:bg-dark-700 relative">
                  {album.cover_thumbnail ? (
                    <img
                      src={album.cover_thumbnail}
                      alt={album.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <RectangleStackIcon className="w-12 h-12 text-dark-300" />
                    </div>
                  )}
                </div>
                <div className="p-3">
                  <p className="font-medium truncate">{album.name}</p>
                  <p className="text-sm text-dark-500">{album.media_count} items</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
      
      {/* People preview */}
      {people && people.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">People</h2>
            <Link to="/people" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
              View all
            </Link>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {people.slice(0, 10).map((person) => (
              <Link
                key={person.id}
                to={`/people/${person.id}`}
                className="flex-shrink-0 text-center group"
              >
                <div className="w-20 h-20 rounded-full bg-dark-100 dark:bg-dark-700 overflow-hidden mb-2">
                  {person.cover_face_thumbnail ? (
                    <img
                      src={person.cover_face_thumbnail}
                      alt={person.name || 'Unknown'}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <UserGroupIcon className="w-8 h-8 text-dark-300" />
                    </div>
                  )}
                </div>
                <p className="text-sm font-medium truncate max-w-[80px]">
                  {person.name || 'Unknown'}
                </p>
                <p className="text-xs text-dark-500">{person.face_count} photos</p>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
