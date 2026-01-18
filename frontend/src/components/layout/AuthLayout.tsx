import { Outlet, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { PhotoIcon } from '@heroicons/react/24/outline';

export default function AuthLayout() {
  const { isAuthenticated, isLoading } = useAuthStore();
  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 dark:from-dark-900 dark:to-dark-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl shadow-lg mb-4">
            <PhotoIcon className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-dark-900 dark:text-white">PhotoVault</h1>
          <p className="text-dark-500 dark:text-dark-400 mt-1">Your photos, your privacy</p>
        </div>
        
        {/* Auth form */}
        <div className="card p-8">
          <Outlet />
        </div>
        
        {/* Footer */}
        <p className="text-center text-sm text-dark-500 dark:text-dark-400 mt-6">
          Self-hosted photo management with AI
        </p>
      </div>
    </div>
  );
}
