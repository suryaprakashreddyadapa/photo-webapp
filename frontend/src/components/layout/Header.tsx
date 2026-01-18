import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import {
  MagnifyingGlassIcon,
  SunIcon,
  MoonIcon,
  Squares2X2Icon,
  ArrowUpTrayIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export default function Header() {
  const navigate = useNavigate();
  const { darkMode, toggleDarkMode, gridSize, setGridSize, searchQuery, setSearchQuery } = useUIStore();
  const [localSearch, setLocalSearch] = useState(searchQuery);
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(localSearch);
    if (localSearch.trim()) {
      navigate(`/ask?q=${encodeURIComponent(localSearch)}`);
    }
  };
  
  const gridSizes = ['small', 'medium', 'large'] as const;
  
  return (
    <header className="h-16 bg-white dark:bg-dark-800 border-b border-dark-100 dark:border-dark-700 flex items-center justify-between px-6">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
          <input
            type="text"
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            placeholder="Search photos, people, places..."
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-dark-50 dark:bg-dark-700 border border-transparent focus:border-primary-500 focus:bg-white dark:focus:bg-dark-800 transition-all"
          />
        </div>
      </form>
      
      {/* Actions */}
      <div className="flex items-center gap-2 ml-4">
        {/* Grid size */}
        <div className="flex items-center bg-dark-100 dark:bg-dark-700 rounded-lg p-1">
          {gridSizes.map((size) => (
            <button
              key={size}
              onClick={() => setGridSize(size)}
              className={clsx(
                'p-1.5 rounded transition-colors',
                gridSize === size
                  ? 'bg-white dark:bg-dark-600 shadow-sm'
                  : 'hover:bg-dark-200 dark:hover:bg-dark-600'
              )}
              title={`${size.charAt(0).toUpperCase() + size.slice(1)} grid`}
            >
              <Squares2X2Icon
                className={clsx(
                  'w-4 h-4',
                  size === 'small' && 'scale-75',
                  size === 'large' && 'scale-110'
                )}
              />
            </button>
          ))}
        </div>
        
        {/* Upload button */}
        <button
          onClick={() => navigate('/photos?upload=true')}
          className="btn-primary flex items-center gap-2"
        >
          <ArrowUpTrayIcon className="w-4 h-4" />
          <span className="hidden sm:inline">Upload</span>
        </button>
        
        {/* Theme toggle */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700 transition-colors"
          title={darkMode ? 'Light mode' : 'Dark mode'}
        >
          {darkMode ? (
            <SunIcon className="w-5 h-5 text-yellow-500" />
          ) : (
            <MoonIcon className="w-5 h-5" />
          )}
        </button>
      </div>
    </header>
  );
}
