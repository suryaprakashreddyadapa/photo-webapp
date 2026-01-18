import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { albumsApi } from '@/services/api';
import { Album, SmartAlbum } from '@/types';
import {
  PlusIcon,
  RectangleStackIcon,
  SparklesIcon,
  EllipsisVerticalIcon,
  PencilIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { Menu } from '@headlessui/react';
import toast from 'react-hot-toast';
import clsx from 'clsx';

export default function AlbumsPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAlbumName, setNewAlbumName] = useState('');
  const [newAlbumDescription, setNewAlbumDescription] = useState('');
  const [activeTab, setActiveTab] = useState<'albums' | 'smart'>('albums');
  
  // Fetch albums
  const { data: albums, isLoading: albumsLoading } = useQuery<Album[]>({
    queryKey: ['albums'],
    queryFn: async () => {
      const response = await albumsApi.list();
      return response.data;
    },
  });
  
  // Fetch smart albums
  const { data: smartAlbums, isLoading: smartLoading } = useQuery<SmartAlbum[]>({
    queryKey: ['smartAlbums'],
    queryFn: async () => {
      const response = await albumsApi.listSmart();
      return response.data;
    },
  });
  
  // Create album mutation
  const createAlbum = useMutation({
    mutationFn: async () => {
      await albumsApi.create(newAlbumName, newAlbumDescription || undefined);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albums'] });
      setShowCreateModal(false);
      setNewAlbumName('');
      setNewAlbumDescription('');
      toast.success('Album created');
    },
    onError: () => {
      toast.error('Failed to create album');
    },
  });
  
  // Delete album mutation
  const deleteAlbum = useMutation({
    mutationFn: async (id: string) => {
      await albumsApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['albums'] });
      toast.success('Album deleted');
    },
  });
  
  const handleCreateAlbum = (e: React.FormEvent) => {
    e.preventDefault();
    if (newAlbumName.trim()) {
      createAlbum.mutate();
    }
  };
  
  const isLoading = activeTab === 'albums' ? albumsLoading : smartLoading;
  const currentAlbums = activeTab === 'albums' ? albums : smartAlbums;
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Albums</h1>
          <p className="text-dark-500 dark:text-dark-400">
            Organize your photos into collections
          </p>
        </div>
        
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-5 h-5" />
          New Album
        </button>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-4 border-b border-dark-200 dark:border-dark-700">
        <button
          onClick={() => setActiveTab('albums')}
          className={clsx(
            'pb-3 px-1 font-medium border-b-2 transition-colors',
            activeTab === 'albums'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-dark-500 hover:text-dark-700'
          )}
        >
          <RectangleStackIcon className="w-5 h-5 inline mr-2" />
          Albums
        </button>
        <button
          onClick={() => setActiveTab('smart')}
          className={clsx(
            'pb-3 px-1 font-medium border-b-2 transition-colors',
            activeTab === 'smart'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-dark-500 hover:text-dark-700'
          )}
        >
          <SparklesIcon className="w-5 h-5 inline mr-2" />
          Smart Albums
        </button>
      </div>
      
      {/* Albums grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : currentAlbums && currentAlbums.length > 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {currentAlbums.map((album) => (
            <div key={album.id} className="card overflow-hidden group relative">
              <Link to={activeTab === 'albums' ? `/albums/${album.id}` : `/albums/smart/${album.id}`}>
                <div className="aspect-square bg-dark-100 dark:bg-dark-700 relative">
                  {'cover_thumbnail' in album && album.cover_thumbnail ? (
                    <img
                      src={album.cover_thumbnail}
                      alt={album.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      {activeTab === 'smart' ? (
                        <SparklesIcon className="w-16 h-16 text-dark-300" />
                      ) : (
                        <RectangleStackIcon className="w-16 h-16 text-dark-300" />
                      )}
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <p className="font-medium truncate">{album.name}</p>
                  {'media_count' in album && (
                    <p className="text-sm text-dark-500">{album.media_count} items</p>
                  )}
                  {'query' in album && (
                    <p className="text-sm text-dark-500 truncate">{album.query}</p>
                  )}
                </div>
              </Link>
              
              {/* Menu */}
              {activeTab === 'albums' && (
                <Menu as="div" className="absolute top-2 right-2">
                  <Menu.Button className="p-2 rounded-full bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                    <EllipsisVerticalIcon className="w-5 h-5" />
                  </Menu.Button>
                  <Menu.Items className="absolute right-0 mt-1 w-48 bg-white dark:bg-dark-800 rounded-lg shadow-lg border border-dark-200 dark:border-dark-700 py-1 z-10">
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={clsx(
                            'w-full px-4 py-2 text-left flex items-center gap-2',
                            active && 'bg-dark-100 dark:bg-dark-700'
                          )}
                        >
                          <PencilIcon className="w-4 h-4" />
                          Edit
                        </button>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={() => deleteAlbum.mutate(album.id)}
                          className={clsx(
                            'w-full px-4 py-2 text-left flex items-center gap-2 text-red-600',
                            active && 'bg-dark-100 dark:bg-dark-700'
                          )}
                        >
                          <TrashIcon className="w-4 h-4" />
                          Delete
                        </button>
                      )}
                    </Menu.Item>
                  </Menu.Items>
                </Menu>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <RectangleStackIcon className="w-16 h-16 mx-auto text-dark-300 mb-4" />
          <h3 className="text-lg font-medium mb-2">No albums yet</h3>
          <p className="text-dark-500 mb-4">
            Create an album to organize your photos
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            Create Album
          </button>
        </div>
      )}
      
      {/* Create album modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create Album</h2>
            <form onSubmit={handleCreateAlbum} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  value={newAlbumName}
                  onChange={(e) => setNewAlbumName(e.target.value)}
                  className="input"
                  placeholder="Album name"
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description (optional)</label>
                <textarea
                  value={newAlbumDescription}
                  onChange={(e) => setNewAlbumDescription(e.target.value)}
                  className="input"
                  placeholder="Add a description..."
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
