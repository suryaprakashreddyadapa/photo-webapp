import { useCallback } from 'react';
import { useUIStore } from '@/store/uiStore';
import { Media } from '@/types';
import { mediaApi } from '@/services/api';
import { HeartIcon, PlayIcon, CheckIcon } from '@heroicons/react/24/solid';
import { HeartIcon as HeartOutline } from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface PhotoGridProps {
  media: Media[];
  onFavoriteToggle?: (id: string, isFavorite: boolean) => void;
  selectable?: boolean;
}

export default function PhotoGrid({ media, onFavoriteToggle, selectable = true }: PhotoGridProps) {
  const { gridSize, openLightbox, selectedMedia, toggleMediaSelection, isSelected } = useUIStore();
  
  const handleClick = useCallback((item: Media, e: React.MouseEvent) => {
    if (e.ctrlKey || e.metaKey) {
      // Multi-select with Ctrl/Cmd
      toggleMediaSelection(item.id);
    } else if (selectable && selectedMedia.size > 0) {
      // If in selection mode, toggle selection
      toggleMediaSelection(item.id);
    } else {
      // Open lightbox
      openLightbox(item.id);
    }
  }, [openLightbox, toggleMediaSelection, selectable, selectedMedia.size]);
  
  const handleFavorite = useCallback((e: React.MouseEvent, item: Media) => {
    e.stopPropagation();
    onFavoriteToggle?.(item.id, !item.is_favorite);
  }, [onFavoriteToggle]);
  
  const gridClass = clsx(
    'photo-grid',
    gridSize === 'small' && 'photo-grid-small',
    gridSize === 'large' && 'photo-grid-large'
  );
  
  if (media.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-dark-500">
        <p className="text-lg">No photos found</p>
        <p className="text-sm mt-1">Upload some photos to get started</p>
      </div>
    );
  }
  
  return (
    <div className={gridClass}>
      {media.map((item) => (
        <div
          key={item.id}
          className={clsx(
            'relative group cursor-pointer overflow-hidden rounded-lg bg-dark-100 dark:bg-dark-800 aspect-square',
            isSelected(item.id) && 'ring-2 ring-primary-500 ring-offset-2 dark:ring-offset-dark-900'
          )}
          onClick={(e) => handleClick(item, e)}
        >
          {/* Thumbnail */}
          <img
            src={mediaApi.getThumbnailUrl(item.id, gridSize === 'large' ? 'large' : 'medium')}
            alt={item.filename}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
          
          {/* Video indicator */}
          {item.media_type === 'video' && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-black/50 flex items-center justify-center">
                <PlayIcon className="w-6 h-6 text-white ml-1" />
              </div>
            </div>
          )}
          
          {/* Selection checkbox */}
          {selectable && (
            <div
              className={clsx(
                'absolute top-2 left-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all',
                isSelected(item.id)
                  ? 'bg-primary-500 border-primary-500'
                  : 'border-white bg-black/20 opacity-0 group-hover:opacity-100'
              )}
              onClick={(e) => {
                e.stopPropagation();
                toggleMediaSelection(item.id);
              }}
            >
              {isSelected(item.id) && <CheckIcon className="w-4 h-4 text-white" />}
            </div>
          )}
          
          {/* Favorite button */}
          <button
            className={clsx(
              'absolute top-2 right-2 p-1.5 rounded-full transition-all',
              item.is_favorite
                ? 'bg-red-500 text-white'
                : 'bg-black/20 text-white opacity-0 group-hover:opacity-100 hover:bg-black/40'
            )}
            onClick={(e) => handleFavorite(e, item)}
          >
            {item.is_favorite ? (
              <HeartIcon className="w-4 h-4" />
            ) : (
              <HeartOutline className="w-4 h-4" />
            )}
          </button>
          
          {/* Hover overlay with info */}
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
            <p className="text-white text-sm truncate">{item.filename}</p>
            {item.taken_at && (
              <p className="text-white/70 text-xs">
                {new Date(item.taken_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
