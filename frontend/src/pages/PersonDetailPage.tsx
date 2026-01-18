import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { peopleApi } from '@/services/api';
import { Person, Media } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import { ArrowLeftIcon, PencilIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';

export default function PersonDetailPage() {
  const { personId } = useParams<{ personId: string }>();
  
  const { data: person, isLoading: personLoading } = useQuery<Person>({
    queryKey: ['person', personId],
    queryFn: async () => {
      const response = await peopleApi.get(personId!);
      return response.data;
    },
    enabled: !!personId,
  });
  
  const { data: mediaData, isLoading: mediaLoading } = useQuery<{ items: Media[] }>({
    queryKey: ['personMedia', personId],
    queryFn: async () => {
      const response = await peopleApi.getMedia(personId!, { page_size: 100 });
      return response.data;
    },
    enabled: !!personId,
  });
  
  const isLoading = personLoading || mediaLoading;
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  if (!person) {
    return (
      <div className="text-center py-20">
        <p>Person not found</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/people" className="p-2 hover:bg-dark-100 dark:hover:bg-dark-800 rounded-lg">
          <ArrowLeftIcon className="w-5 h-5" />
        </Link>
        
        <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-700 overflow-hidden">
          {person.cover_face_thumbnail ? (
            <img
              src={person.cover_face_thumbnail}
              alt={person.name || 'Unknown'}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <UserGroupIcon className="w-8 h-8 text-dark-300" />
            </div>
          )}
        </div>
        
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{person.name || 'Unknown'}</h1>
          <p className="text-dark-500">{person.face_count} photos</p>
        </div>
        
        <button className="btn-secondary flex items-center gap-2">
          <PencilIcon className="w-4 h-4" />
          Edit Name
        </button>
      </div>
      
      {mediaData?.items && mediaData.items.length > 0 ? (
        <PhotoGrid media={mediaData.items} />
      ) : (
        <div className="text-center py-20 text-dark-500">
          <p>No photos found</p>
        </div>
      )}
    </div>
  );
}
