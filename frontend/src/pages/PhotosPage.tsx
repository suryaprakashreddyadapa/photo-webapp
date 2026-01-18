import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { mediaApi } from '@/services/api';
import { useUIStore } from '@/store/uiStore';
import { Media, PaginatedResponse } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import {
  FunnelIcon,
  HeartIcon,
  TrashIcon,
  RectangleStackIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import clsx from 'clsx';

export default function PhotosPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedMedia, clearSelection, sortBy, sortOrder, setSortBy, setSortOrder } = useUIStore();
  
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    media_type: searchParams.get('type') || undefined,
    favorites_only: searchParams.get('favorites') === 'true',
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Fetch media
  const { data, isLoading, refetch } = useQuery<PaginatedResponse<Media>>({
    queryKey: ['media', page, filters, sortBy, sortOrder],
    queryFn: async () => {
      const response = await mediaApi.list({
        page,
        page_size: 50,
        sort_by: sortBy,
        sort_order: sortOrder,
        ...filters,
      });
      return response.data;
    },
  });
  
  // Toggle favorite mutation
  const toggleFavorite = useMutation({
    mutationFn: async ({ id, isFavorite }: { id: string; isFavorite: boolean }) => {
      await mediaApi.update(id, { is_favorite: isFavorite });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
    },
  });
  
  // Bulk delete mutation
  const bulkDelete = useMutation({
    mutationFn: async (ids: string[]) => {
      await mediaApi.bulkAction(ids, 'delete');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
      clearSelection();
      toast.success('Items moved to trash');
    },
  });
  
  // Bulk favorite mutation
  const bulkFavorite = useMutation({
    mutationFn: async (ids: string[]) => {
      await mediaApi.bulkAction(ids, 'favorite');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['media'] });
      clearSelection();
      toast.success('Items added to favorites');
    },
  });
  
  const handleFavoriteToggle = useCallback((id: string, isFavorite: boolean) => {
    toggleFavorite.mutate({ id, isFavorite });
  }, [toggleFavorite]);
  
  const handleBulkDelete = () => {
    if (selectedMedia.size > 0) {
      bulkDelete.mutate(Array.from(selectedMedia));
    }
  };
  
  const handleBulkFavorite = () => {
    if (selectedMedia.size > 0) {
      bulkFavorite.mutate(Array.from(selectedMedia));
    }
  };
  
  const updateFilter = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Photos</h1>
          <p className="text-dark-500 dark:text-dark-400">
            {data?.total?.toLocaleString() || 0} items
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Sort options */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="input py-2 pr-8"
          >
            <option value="taken_at">Date taken</option>
            <option value="created_at">Date added</option>
            <option value="filename">Name</option>
            <option value="file_size">Size</option>
          </select>
          
          <button
            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="btn-secondary"
          >
            {sortOrder === 'desc' ? '↓' : '↑'}
          </button>
          
          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={clsx('btn-secondary', showFilters && 'bg-primary-100 dark:bg-primary-900/30')}
          >
            <FunnelIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
      
      {/* Filters */}
      {showFilters && (
        <div className="card p-4 flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select
              value={filters.media_type || ''}
              onChange={(e) => updateFilter('media_type', e.target.value || undefined)}
              className="input py-2"
            >
              <option value="">All</option>
              <option value="photo">Photos</option>
              <option value="video">Videos</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Favorites</label>
            <label className="flex items-center gap-2 mt-2">
              <input
                type="checkbox"
                checked={filters.favorites_only}
                onChange={(e) => updateFilter('favorites_only', e.target.checked)}
                className="rounded"
              />
              <span>Favorites only</span>
            </label>
          </div>
        </div>
      )}
      
      {/* Selection toolbar */}
      {selectedMedia.size > 0 && (
        <div className="card p-4 flex items-center justify-between bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800">
          <div className="flex items-center gap-4">
            <span className="font-medium">{selectedMedia.size} selected</span>
            <button
              onClick={clearSelection}
              className="text-dark-500 hover:text-dark-700"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkFavorite}
              className="btn-secondary flex items-center gap-2"
            >
              <HeartIcon className="w-4 h-4" />
              Favorite
            </button>
            <button className="btn-secondary flex items-center gap-2">
              <RectangleStackIcon className="w-4 h-4" />
              Add to album
            </button>
            <button
              onClick={handleBulkDelete}
              className="btn-danger flex items-center gap-2"
            >
              <TrashIcon className="w-4 h-4" />
              Delete
            </button>
          </div>
        </div>
      )}
      
      {/* Photo grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : data?.items ? (
        <>
          <PhotoGrid media={data.items} onFavoriteToggle={handleFavoriteToggle} />
          
          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary"
              >
                Previous
              </button>
              <span className="px-4 py-2">
                Page {page} of {data.pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page === data.pages}
                className="btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-20 text-dark-500">
          <p>No photos found</p>
        </div>
      )}
    </div>
  );
}
