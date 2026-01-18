import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import { useUIStore } from '@/store/uiStore';
import Lightbox from '@/components/media/Lightbox';

export default function MainLayout() {
  const { sidebarCollapsed, lightboxOpen } = useUIStore();
  
  return (
    <div className="min-h-screen bg-white dark:bg-dark-900">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content */}
      <div
        className={`transition-all duration-300 ${
          sidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        {/* Header */}
        <Header />
        
        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
      
      {/* Lightbox */}
      {lightboxOpen && <Lightbox />}
    </div>
  );
}
