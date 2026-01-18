import { useQuery } from '@tanstack/react-query';
import { mediaApi } from '@/services/api';
import { TimelineEntry, Media } from '@/types';
import PhotoGrid from '@/components/media/PhotoGrid';
import { CalendarDaysIcon } from '@heroicons/react/24/outline';
import { format, parseISO } from 'date-fns';

export default function TimelinePage() {
  // Fetch timeline data
  const { data: timeline, isLoading } = useQuery<TimelineEntry[]>({
    queryKey: ['timeline'],
    queryFn: async () => {
      const response = await mediaApi.getTimeline();
      return response.data;
    },
  });
  
  // Group timeline by year and month
  const groupedTimeline = timeline?.reduce((acc, entry) => {
    const date = parseISO(entry.date);
    const year = date.getFullYear();
    const month = format(date, 'MMMM');
    
    if (!acc[year]) {
      acc[year] = {};
    }
    if (!acc[year][month]) {
      acc[year][month] = [];
    }
    acc[year][month].push(entry);
    
    return acc;
  }, {} as Record<number, Record<string, TimelineEntry[]>>);
  
  const years = groupedTimeline ? Object.keys(groupedTimeline).sort((a, b) => Number(b) - Number(a)) : [];
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <CalendarDaysIcon className="w-7 h-7" />
          Timeline
        </h1>
        <p className="text-dark-500 dark:text-dark-400">
          Browse your photos by date
        </p>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : years.length > 0 ? (
        <div className="space-y-12">
          {years.map((year) => (
            <div key={year}>
              <h2 className="text-xl font-bold mb-6 sticky top-0 bg-white dark:bg-dark-900 py-2 z-10">
                {year}
              </h2>
              
              <div className="space-y-8">
                {Object.entries(groupedTimeline![Number(year)])
                  .sort((a, b) => {
                    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                                   'July', 'August', 'September', 'October', 'November', 'December'];
                    return months.indexOf(b[0]) - months.indexOf(a[0]);
                  })
                  .map(([month, entries]) => {
                    const totalPhotos = entries.reduce((sum, e) => sum + e.count, 0);
                    
                    return (
                      <div key={`${year}-${month}`}>
                        <div className="flex items-center gap-4 mb-4">
                          <h3 className="text-lg font-semibold">{month}</h3>
                          <span className="text-dark-500">
                            {totalPhotos} photo{totalPhotos !== 1 ? 's' : ''}
                          </span>
                        </div>
                        
                        {/* Calendar view */}
                        <div className="grid grid-cols-7 gap-1 mb-4">
                          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                            <div key={day} className="text-center text-xs text-dark-500 py-1">
                              {day}
                            </div>
                          ))}
                          
                          {entries.map((entry) => {
                            const date = parseISO(entry.date);
                            const dayOfWeek = date.getDay();
                            const dayOfMonth = date.getDate();
                            
                            // Add empty cells for alignment (simplified)
                            return (
                              <div
                                key={entry.date}
                                className="aspect-square rounded-lg bg-primary-100 dark:bg-primary-900/30 flex flex-col items-center justify-center cursor-pointer hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
                                title={`${entry.count} photos`}
                              >
                                <span className="text-sm font-medium">{dayOfMonth}</span>
                                <span className="text-xs text-dark-500">{entry.count}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <CalendarDaysIcon className="w-16 h-16 mx-auto text-dark-300 mb-4" />
          <h3 className="text-lg font-medium mb-2">No timeline data</h3>
          <p className="text-dark-500">
            Upload photos to see them organized by date
          </p>
        </div>
      )}
    </div>
  );
}
