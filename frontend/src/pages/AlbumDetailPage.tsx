import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { albumsApi } from '@/services/api';
import { Album, Media } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import { ArrowLeftIcon, PencilIcon, ShareIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';

export default function AlbumDetailPage() {
  const { albumId } = useParams<{ albumId: string }>();
  
  const { data: album, isLoading: albumLoading } = useQuery<Album>({
    queryKey: ['album', albumId],
    queryFn: async () => {
      const response = await albumsApi.get(albumId!);
      return response.data;
    },
    enabled: !!albumId,
  });
  
  const { data: mediaData, isLoading: mediaLoading } = useQuery<{ items: Media[] }>({
    queryKey: ['albumMedia', albumId],
    queryFn: async () => {
      const response = await albumsApi.getMedia(albumId!, { page_size: 100 });
      return response.data;
    },
    enabled: !!albumId,
  });
  
  const isLoading = albumLoading || mediaLoading;
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  if (!album) {
    return (
      <div className="text-center py-20">
        <p>Album not found</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/albums" className="p-2 hover:bg-dark-100 dark:hover:bg-dark-800 rounded-lg">
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{album.name}</h1>
          {album.description && (
            <p className="text-dark-500 dark:text-dark-400">{album.description}</p>
          )}
          <p className="text-sm text-dark-500">{album.media_count} items</p>
        </div>
        <button className="btn-secondary flex items-center gap-2">
          <PencilIcon className="w-4 h-4" />
          Edit
        </button>
        <button className="btn-secondary flex items-center gap-2">
          <ShareIcon className="w-4 h-4" />
          Share
        </button>
      </div>
      
      {mediaData?.items && mediaData.items.length > 0 ? (
        <PhotoGrid media={mediaData.items} />
      ) : (
        <div className="text-center py-20 text-dark-500">
          <p>This album is empty</p>
        </div>
      )}
    </div>
  );
}
