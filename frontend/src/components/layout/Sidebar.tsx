import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import {
  HomeIcon,
  PhotoIcon,
  RectangleStackIcon,
  UserGroupIcon,
  ChatBubbleLeftRightIcon,
  CalendarDaysIcon,
  MapIcon,
  Cog6ToothIcon,
  TrashIcon,
  ShieldCheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

const navItems = [
  { name: 'Home', path: '/', icon: HomeIcon },
  { name: 'Photos', path: '/photos', icon: PhotoIcon },
  { name: 'Albums', path: '/albums', icon: RectangleStackIcon },
  { name: 'People', path: '/people', icon: UserGroupIcon },
  { name: 'Ask', path: '/ask', icon: ChatBubbleLeftRightIcon },
  { name: 'Timeline', path: '/timeline', icon: CalendarDaysIcon },
  { name: 'Map', path: '/map', icon: MapIcon },
];

const bottomItems = [
  { name: 'Trash', path: '/trash', icon: TrashIcon },
  { name: 'Settings', path: '/settings', icon: Cog6ToothIcon },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-full bg-white dark:bg-dark-800 border-r border-dark-100 dark:border-dark-700 transition-all duration-300 z-40 flex flex-col',
        sidebarCollapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-dark-100 dark:border-dark-700">
        {!sidebarCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
              <PhotoIcon className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-lg">PhotoVault</span>
          </div>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-700 transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRightIcon className="w-5 h-5" />
          ) : (
            <ChevronLeftIcon className="w-5 h-5" />
          )}
        </button>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-3">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'sidebar-item',
                    isActive && 'sidebar-item-active',
                    sidebarCollapsed && 'justify-center px-0'
                  )
                }
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </NavLink>
            </li>
          ))}
          
          {/* Admin link */}
          {user?.role === 'admin' && (
            <li>
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  clsx(
                    'sidebar-item',
                    isActive && 'sidebar-item-active',
                    sidebarCollapsed && 'justify-center px-0'
                  )
                }
                title={sidebarCollapsed ? 'Admin' : undefined}
              >
                <ShieldCheckIcon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>Admin</span>}
              </NavLink>
            </li>
          )}
        </ul>
      </nav>
      
      {/* Bottom items */}
      <div className="border-t border-dark-100 dark:border-dark-700 py-4">
        <ul className="space-y-1 px-3">
          {bottomItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  clsx(
                    'sidebar-item',
                    isActive && 'sidebar-item-active',
                    sidebarCollapsed && 'justify-center px-0'
                  )
                }
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </NavLink>
            </li>
          ))}
          
          {/* Logout */}
          <li>
            <button
              onClick={handleLogout}
              className={clsx(
                'sidebar-item w-full text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20',
                sidebarCollapsed && 'justify-center px-0'
              )}
              title={sidebarCollapsed ? 'Logout' : undefined}
            >
              <ArrowRightOnRectangleIcon className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span>Logout</span>}
            </button>
          </li>
        </ul>
      </div>
      
      {/* User info */}
      {!sidebarCollapsed && user && (
        <div className="p-4 border-t border-dark-100 dark:border-dark-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
              <span className="text-primary-600 dark:text-primary-400 font-medium">
                {user.full_name?.[0] || user.email[0].toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user.full_name || 'User'}
              </p>
              <p className="text-xs text-dark-500 truncate">{user.email}</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
