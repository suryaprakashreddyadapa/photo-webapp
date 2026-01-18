import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { mediaApi } from '@/services/api';
import { Media, PaginatedResponse } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import { TrashIcon, ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

export default function TrashPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  
  // Fetch trashed media
  const { data, isLoading } = useQuery<PaginatedResponse<Media>>({
    queryKey: ['trash', page],
    queryFn: async () => {
      const response = await mediaApi.list({
        page,
        page_size: 50,
        trashed: true,
      });
      return response.data;
    },
  });
  
  // Restore mutation
  const restoreAll = useMutation({
    mutationFn: async () => {
      if (data?.items) {
        const ids = data.items.map((m) => m.id);
        await mediaApi.bulkAction(ids, 'restore');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash'] });
      toast.success('Items restored');
    },
  });
  
  // Empty trash mutation
  const emptyTrash = useMutation({
    mutationFn: async () => {
      await mediaApi.emptyTrash();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trash'] });
      toast.success('Trash emptied');
    },
  });
  
  const handleEmptyTrash = () => {
    if (confirm('Permanently delete all items in trash? This cannot be undone.')) {
      emptyTrash.mutate();
    }
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrashIcon className="w-7 h-7" />
            Trash
          </h1>
          <p className="text-dark-500 dark:text-dark-400">
            Items in trash will be permanently deleted after 30 days
          </p>
        </div>
        
        {data?.items && data.items.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => restoreAll.mutate()}
              disabled={restoreAll.isPending}
              className="btn-secondary flex items-center gap-2"
            >
              <ArrowPathIcon className="w-4 h-4" />
              Restore All
            </button>
            <button
              onClick={handleEmptyTrash}
              disabled={emptyTrash.isPending}
              className="btn-danger flex items-center gap-2"
            >
              <TrashIcon className="w-4 h-4" />
              Empty Trash
            </button>
          </div>
        )}
      </div>
      
      {/* Warning banner */}
      {data?.items && data.items.length > 0 && (
        <div className="card p-4 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 flex items-center gap-3">
          <ExclamationTriangleIcon className="w-6 h-6 text-yellow-600" />
          <p className="text-yellow-800 dark:text-yellow-200">
            {data.total} item(s) in trash. Items will be permanently deleted after 30 days.
          </p>
        </div>
      )}
      
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : data?.items && data.items.length > 0 ? (
        <>
          <PhotoGrid media={data.items} />
          
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
        <div className="text-center py-20">
          <TrashIcon className="w-16 h-16 mx-auto text-dark-300 mb-4" />
          <h3 className="text-lg font-medium mb-2">Trash is empty</h3>
          <p className="text-dark-500">
            Deleted items will appear here
          </p>
        </div>
      )}
    </div>
  );
}
