import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type GridSize = 'small' | 'medium' | 'large';
type SortBy = 'taken_at' | 'created_at' | 'filename' | 'file_size';
type SortOrder = 'asc' | 'desc';

interface UIState {
  // Theme
  darkMode: boolean;
  toggleDarkMode: () => void;
  setDarkMode: (dark: boolean) => void;
  
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  
  // Grid
  gridSize: GridSize;
  setGridSize: (size: GridSize) => void;
  
  // Sorting
  sortBy: SortBy;
  sortOrder: SortOrder;
  setSortBy: (sortBy: SortBy) => void;
  setSortOrder: (order: SortOrder) => void;
  
  // Selection
  selectedMedia: Set<string>;
  selectMedia: (id: string) => void;
  deselectMedia: (id: string) => void;
  toggleMediaSelection: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  isSelected: (id: string) => boolean;
  
  // Modals
  lightboxOpen: boolean;
  lightboxMediaId: string | null;
  openLightbox: (mediaId: string) => void;
  closeLightbox: () => void;
  
  // Upload
  uploadModalOpen: boolean;
  setUploadModalOpen: (open: boolean) => void;
  
  // Search
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Theme
      darkMode: false,
      toggleDarkMode: () => {
        const newDarkMode = !get().darkMode;
        set({ darkMode: newDarkMode });
        if (newDarkMode) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      setDarkMode: (dark) => {
        set({ darkMode: dark });
        if (dark) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
      
      // Sidebar
      sidebarCollapsed: false,
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      
      // Grid
      gridSize: 'medium',
      setGridSize: (size) => set({ gridSize: size }),
      
      // Sorting
      sortBy: 'taken_at',
      sortOrder: 'desc',
      setSortBy: (sortBy) => set({ sortBy }),
      setSortOrder: (order) => set({ sortOrder: order }),
      
      // Selection
      selectedMedia: new Set<string>(),
      selectMedia: (id) => set((state) => {
        const newSelection = new Set(state.selectedMedia);
        newSelection.add(id);
        return { selectedMedia: newSelection };
      }),
      deselectMedia: (id) => set((state) => {
        const newSelection = new Set(state.selectedMedia);
        newSelection.delete(id);
        return { selectedMedia: newSelection };
      }),
      toggleMediaSelection: (id) => set((state) => {
        const newSelection = new Set(state.selectedMedia);
        if (newSelection.has(id)) {
          newSelection.delete(id);
        } else {
          newSelection.add(id);
        }
        return { selectedMedia: newSelection };
      }),
      selectAll: (ids) => set({ selectedMedia: new Set(ids) }),
      clearSelection: () => set({ selectedMedia: new Set() }),
      isSelected: (id) => get().selectedMedia.has(id),
      
      // Modals
      lightboxOpen: false,
      lightboxMediaId: null,
      openLightbox: (mediaId) => set({ lightboxOpen: true, lightboxMediaId: mediaId }),
      closeLightbox: () => set({ lightboxOpen: false, lightboxMediaId: null }),
      
      // Upload
      uploadModalOpen: false,
      setUploadModalOpen: (open) => set({ uploadModalOpen: open }),
      
      // Search
      searchQuery: '',
      setSearchQuery: (query) => set({ searchQuery: query }),
    }),
    {
      name: 'photovault-ui',
      partialize: (state) => ({
        darkMode: state.darkMode,
        sidebarCollapsed: state.sidebarCollapsed,
        gridSize: state.gridSize,
        sortBy: state.sortBy,
        sortOrder: state.sortOrder,
      }),
    }
  )
);

// Initialize dark mode on app load
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('photovault-ui');
  if (stored) {
    const { state } = JSON.parse(stored);
    if (state?.darkMode) {
      document.documentElement.classList.add('dark');
    }
  }
}
