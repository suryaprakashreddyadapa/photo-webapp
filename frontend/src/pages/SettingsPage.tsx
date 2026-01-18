import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import { usersApi, jobsApi } from '@/services/api';
import { UserSettings, Job } from '@/types';
import {
  Cog6ToothIcon,
  ServerIcon,
  CpuChipIcon,
  ArrowPathIcon,
  KeyIcon,
  UserCircleIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import clsx from 'clsx';

type SettingsTab = 'profile' | 'nas' | 'ai' | 'indexing' | 'security';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { user, updateUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  
  // Fetch settings
  const { data: settings, isLoading } = useQuery<UserSettings>({
    queryKey: ['userSettings'],
    queryFn: async () => {
      const response = await usersApi.getSettings();
      return response.data;
    },
  });
  
  // Fetch jobs
  const { data: jobs } = useQuery<Job[]>({
    queryKey: ['jobs'],
    queryFn: async () => {
      const response = await jobsApi.list({ limit: 5 });
      return response.data;
    },
    refetchInterval: 5000,
  });
  
  // Update settings mutation
  const updateSettings = useMutation({
    mutationFn: async (newSettings: Partial<UserSettings>) => {
      await usersApi.updateSettings(newSettings);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userSettings'] });
      toast.success('Settings saved');
    },
    onError: () => {
      toast.error('Failed to save settings');
    },
  });
  
  // Profile update mutation
  const updateProfile = useMutation({
    mutationFn: async (data: { full_name?: string }) => {
      await usersApi.updateProfile(data);
    },
    onSuccess: (_, data) => {
      updateUser(data);
      toast.success('Profile updated');
    },
  });
  
  // Trigger scan mutation
  const triggerScan = useMutation({
    mutationFn: async () => {
      await jobsApi.triggerScan();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Scan started');
    },
  });
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const changePassword = useMutation({
    mutationFn: async () => {
      await usersApi.changePassword(currentPassword, newPassword);
    },
    onSuccess: () => {
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast.success('Password changed');
    },
    onError: () => {
      toast.error('Failed to change password');
    },
  });
  
  const handlePasswordChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    changePassword.mutate();
  };
  
  const tabs = [
    { id: 'profile', name: 'Profile', icon: UserCircleIcon },
    { id: 'nas', name: 'NAS Storage', icon: ServerIcon },
    { id: 'ai', name: 'AI Features', icon: CpuChipIcon },
    { id: 'indexing', name: 'Indexing', icon: ArrowPathIcon },
    { id: 'security', name: 'Security', icon: KeyIcon },
  ];
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Cog6ToothIcon className="w-7 h-7" />
        Settings
      </h1>
      
      <div className="flex gap-6">
        {/* Tabs */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as SettingsTab)}
                className={clsx(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left',
                  activeTab === tab.id
                    ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                    : 'hover:bg-dark-100 dark:hover:bg-dark-800'
                )}
              >
                <tab.icon className="w-5 h-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>
        
        {/* Content */}
        <div className="flex-1">
          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="card p-6 space-y-6">
              <h2 className="text-lg font-semibold">Profile Settings</h2>
              
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="input bg-dark-50 dark:bg-dark-700"
                />
                <p className="text-xs text-dark-500 mt-1">Email cannot be changed</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Full Name</label>
                <input
                  type="text"
                  defaultValue={user?.full_name || ''}
                  onBlur={(e) => {
                    if (e.target.value !== user?.full_name) {
                      updateProfile.mutate({ full_name: e.target.value });
                    }
                  }}
                  className="input"
                />
              </div>
            </div>
          )}
          
          {/* NAS Tab */}
          {activeTab === 'nas' && (
            <div className="card p-6 space-y-6">
              <h2 className="text-lg font-semibold">NAS Storage</h2>
              
              <div>
                <label className="block text-sm font-medium mb-1">NAS Paths</label>
                <p className="text-sm text-dark-500 mb-2">
                  Folders on your NAS that will be scanned for photos
                </p>
                {settings?.nas_paths?.map((path, index) => (
                  <div key={index} className="flex items-center gap-2 mb-2">
                    <input
                      type="text"
                      value={path}
                      className="input flex-1"
                      readOnly
                    />
                  </div>
                )) || (
                  <p className="text-dark-400 italic">No paths configured</p>
                )}
                <p className="text-xs text-dark-500 mt-2">
                  Contact your administrator to configure NAS paths
                </p>
              </div>
              
              <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
                <h3 className="font-medium mb-2">Manual Scan</h3>
                <p className="text-sm text-dark-500 mb-4">
                  Trigger a manual scan of your NAS folders
                </p>
                <button
                  onClick={() => triggerScan.mutate()}
                  disabled={triggerScan.isPending}
                  className="btn-primary flex items-center gap-2"
                >
                  <ArrowPathIcon className={clsx('w-5 h-5', triggerScan.isPending && 'animate-spin')} />
                  {triggerScan.isPending ? 'Scanning...' : 'Start Scan'}
                </button>
              </div>
            </div>
          )}
          
          {/* AI Tab */}
          {activeTab === 'ai' && (
            <div className="card p-6 space-y-6">
              <h2 className="text-lg font-semibold">AI Features</h2>
              
              <div className="space-y-4">
                <label className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Face Recognition</p>
                    <p className="text-sm text-dark-500">Detect and group faces in your photos</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings?.face_recognition_enabled ?? true}
                    onChange={(e) => updateSettings.mutate({ face_recognition_enabled: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                </label>
                
                <label className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">CLIP Tagging</p>
                    <p className="text-sm text-dark-500">Auto-tag photos using AI semantic understanding</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings?.clip_enabled ?? true}
                    onChange={(e) => updateSettings.mutate({ clip_enabled: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                </label>
                
                <label className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Object Detection (YOLO)</p>
                    <p className="text-sm text-dark-500">Detect objects in your photos</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings?.yolo_enabled ?? true}
                    onChange={(e) => updateSettings.mutate({ yolo_enabled: e.target.checked })}
                    className="w-5 h-5 rounded"
                  />
                </label>
              </div>
              
              <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
                <h3 className="font-medium mb-4">Re-process AI</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => jobsApi.triggerFaceProcessing()}
                    className="btn-secondary"
                  >
                    Process Faces
                  </button>
                  <button
                    onClick={() => jobsApi.triggerClipProcessing()}
                    className="btn-secondary"
                  >
                    Process CLIP
                  </button>
                  <button
                    onClick={() => jobsApi.triggerYoloProcessing()}
                    className="btn-secondary"
                  >
                    Process YOLO
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Indexing Tab */}
          {activeTab === 'indexing' && (
            <div className="card p-6 space-y-6">
              <h2 className="text-lg font-semibold">Indexing Settings</h2>
              
              <label className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Auto-index</p>
                  <p className="text-sm text-dark-500">Automatically scan for new photos</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings?.auto_index ?? true}
                  onChange={(e) => updateSettings.mutate({ auto_index: e.target.checked })}
                  className="w-5 h-5 rounded"
                />
              </label>
              
              <div>
                <label className="block text-sm font-medium mb-1">Scan Interval (hours)</label>
                <input
                  type="number"
                  value={settings?.index_interval_hours ?? 24}
                  onChange={(e) => updateSettings.mutate({ index_interval_hours: parseInt(e.target.value) })}
                  min={1}
                  max={168}
                  className="input w-32"
                />
              </div>
              
              {/* Recent jobs */}
              {jobs && jobs.length > 0 && (
                <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
                  <h3 className="font-medium mb-4">Recent Jobs</h3>
                  <div className="space-y-2">
                    {jobs.map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center justify-between p-3 bg-dark-50 dark:bg-dark-700 rounded-lg"
                      >
                        <div>
                          <p className="font-medium">{job.job_type}</p>
                          <p className="text-sm text-dark-500">
                            {job.processed_items} / {job.total_items} items
                          </p>
                        </div>
                        <span
                          className={clsx(
                            'px-2 py-1 rounded-full text-xs font-medium',
                            job.status === 'completed' && 'bg-green-100 text-green-700',
                            job.status === 'running' && 'bg-blue-100 text-blue-700',
                            job.status === 'failed' && 'bg-red-100 text-red-700',
                            job.status === 'pending' && 'bg-yellow-100 text-yellow-700'
                          )}
                        >
                          {job.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Security Tab */}
          {activeTab === 'security' && (
            <div className="card p-6 space-y-6">
              <h2 className="text-lg font-semibold">Security</h2>
              
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <h3 className="font-medium">Change Password</h3>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Current Password</label>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="input"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">New Password</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="input"
                    required
                    minLength={8}
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Confirm New Password</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input"
                    required
                  />
                </div>
                
                <button
                  type="submit"
                  disabled={changePassword.isPending}
                  className="btn-primary"
                >
                  {changePassword.isPending ? 'Changing...' : 'Change Password'}
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
