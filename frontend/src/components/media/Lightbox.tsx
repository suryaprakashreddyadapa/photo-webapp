import { useEffect, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useUIStore } from '@/store/uiStore';
import { mediaApi } from '@/services/api';
import { Media } from '@/types';
import {
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  HeartIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  InformationCircleIcon,
  MapPinIcon,
  CalendarIcon,
  CameraIcon,
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartSolid } from '@heroicons/react/24/solid';
import clsx from 'clsx';
import { format } from 'date-fns';

export default function Lightbox() {
  const { lightboxMediaId, closeLightbox } = useUIStore();
  const [showInfo, setShowInfo] = useState(false);
  
  // Fetch media details
  const { data: media, isLoading } = useQuery<Media>({
    queryKey: ['media', lightboxMediaId],
    queryFn: async () => {
      const response = await mediaApi.get(lightboxMediaId!);
      return response.data;
    },
    enabled: !!lightboxMediaId,
  });
  
  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeLightbox();
      } else if (e.key === 'i') {
        setShowInfo((prev) => !prev);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [closeLightbox]);
  
  const handleDownload = useCallback(() => {
    if (media) {
      window.open(mediaApi.getFileUrl(media.id), '_blank');
    }
  }, [media]);
  
  if (!lightboxMediaId) return null;
  
  return (
    <div className="fixed inset-0 z-50 bg-black flex">
      {/* Close button */}
      <button
        onClick={closeLightbox}
        className="absolute top-4 left-4 z-10 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
      >
        <XMarkIcon className="w-6 h-6" />
      </button>
      
      {/* Action buttons */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className={clsx(
            'p-2 rounded-full transition-colors',
            showInfo ? 'bg-white text-black' : 'bg-black/50 text-white hover:bg-black/70'
          )}
          title="Info (i)"
        >
          <InformationCircleIcon className="w-6 h-6" />
        </button>
        <button
          onClick={handleDownload}
          className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
          title="Download"
        >
          <ArrowDownTrayIcon className="w-6 h-6" />
        </button>
        <button
          className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
          title="Favorite"
        >
          {media?.is_favorite ? (
            <HeartSolid className="w-6 h-6 text-red-500" />
          ) : (
            <HeartIcon className="w-6 h-6" />
          )}
        </button>
        <button
          className="p-2 rounded-full bg-black/50 text-white hover:bg-red-600 transition-colors"
          title="Delete"
        >
          <TrashIcon className="w-6 h-6" />
        </button>
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex items-center justify-center p-4">
        {isLoading ? (
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
        ) : media ? (
          media.media_type === 'video' ? (
            <video
              src={mediaApi.getFileUrl(media.id)}
              controls
              autoPlay
              className="max-h-full max-w-full"
            />
          ) : (
            <img
              src={mediaApi.getFileUrl(media.id)}
              alt={media.filename}
              className="max-h-full max-w-full object-contain"
            />
          )
        ) : null}
      </div>
      
      {/* Info panel */}
      {showInfo && media && (
        <div className="w-80 bg-dark-900 border-l border-dark-700 p-6 overflow-y-auto">
          <h3 className="text-lg font-semibold text-white mb-4">Details</h3>
          
          {/* Filename */}
          <div className="mb-4">
            <p className="text-dark-400 text-sm">Filename</p>
            <p className="text-white truncate">{media.filename}</p>
          </div>
          
          {/* Date */}
          {media.taken_at && (
            <div className="mb-4 flex items-start gap-3">
              <CalendarIcon className="w-5 h-5 text-dark-400 mt-0.5" />
              <div>
                <p className="text-dark-400 text-sm">Date taken</p>
                <p className="text-white">
                  {format(new Date(media.taken_at), 'PPP')}
                </p>
                <p className="text-dark-400 text-sm">
                  {format(new Date(media.taken_at), 'p')}
                </p>
              </div>
            </div>
          )}
          
          {/* Location */}
          {(media.location_name || (media.latitude && media.longitude)) && (
            <div className="mb-4 flex items-start gap-3">
              <MapPinIcon className="w-5 h-5 text-dark-400 mt-0.5" />
              <div>
                <p className="text-dark-400 text-sm">Location</p>
                <p className="text-white">
                  {media.location_name || `${media.latitude?.toFixed(4)}, ${media.longitude?.toFixed(4)}`}
                </p>
              </div>
            </div>
          )}
          
          {/* Camera info */}
          {(media.camera_make || media.camera_model) && (
            <div className="mb-4 flex items-start gap-3">
              <CameraIcon className="w-5 h-5 text-dark-400 mt-0.5" />
              <div>
                <p className="text-dark-400 text-sm">Camera</p>
                <p className="text-white">
                  {[media.camera_make, media.camera_model].filter(Boolean).join(' ')}
                </p>
              </div>
            </div>
          )}
          
          {/* Dimensions */}
          {media.width && media.height && (
            <div className="mb-4">
              <p className="text-dark-400 text-sm">Dimensions</p>
              <p className="text-white">{media.width} × {media.height}</p>
            </div>
          )}
          
          {/* File size */}
          {media.file_size && (
            <div className="mb-4">
              <p className="text-dark-400 text-sm">File size</p>
              <p className="text-white">
                {(media.file_size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          )}
          
          {/* Tags */}
          {media.tags && media.tags.length > 0 && (
            <div className="mb-4">
              <p className="text-dark-400 text-sm mb-2">Tags</p>
              <div className="flex flex-wrap gap-2">
                {media.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-dark-700 rounded-full text-sm text-white"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Faces */}
          {media.faces_count > 0 && (
            <div className="mb-4">
              <p className="text-dark-400 text-sm">People</p>
              <p className="text-white">{media.faces_count} face(s) detected</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
