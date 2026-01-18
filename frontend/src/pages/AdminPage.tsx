import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi, usersApi } from '@/services/api';
import { User, SystemStats, Job } from '@/types';
import {
  ShieldCheckIcon,
  UsersIcon,
  ServerStackIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import clsx from 'clsx';

type AdminTab = 'overview' | 'users' | 'jobs';

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  
  // Fetch system stats
  const { data: stats } = useQuery<SystemStats>({
    queryKey: ['adminStats'],
    queryFn: async () => {
      const response = await adminApi.getStats();
      return response.data;
    },
  });
  
  // Fetch users
  const { data: users, isLoading: usersLoading } = useQuery<User[]>({
    queryKey: ['adminUsers'],
    queryFn: async () => {
      const response = await usersApi.listUsers({ limit: 100 });
      return response.data;
    },
    enabled: activeTab === 'users',
  });
  
  // Fetch pending users
  const { data: pendingUsers } = useQuery<User[]>({
    queryKey: ['pendingUsers'],
    queryFn: async () => {
      const response = await usersApi.getPendingUsers();
      return response.data;
    },
  });
  
  // Fetch jobs
  const { data: jobs, isLoading: jobsLoading } = useQuery<Job[]>({
    queryKey: ['adminJobs'],
    queryFn: async () => {
      const response = await adminApi.listJobs({ limit: 50 });
      return response.data;
    },
    enabled: activeTab === 'jobs',
    refetchInterval: 5000,
  });
  
  // Approve user mutation
  const approveUser = useMutation({
    mutationFn: async (userId: string) => {
      await usersApi.approveUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      queryClient.invalidateQueries({ queryKey: ['pendingUsers'] });
      queryClient.invalidateQueries({ queryKey: ['adminStats'] });
      toast.success('User approved');
    },
  });
  
  // Reject user mutation
  const rejectUser = useMutation({
    mutationFn: async (userId: string) => {
      await usersApi.rejectUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      queryClient.invalidateQueries({ queryKey: ['pendingUsers'] });
      toast.success('User rejected');
    },
  });
  
  // Delete user mutation
  const deleteUser = useMutation({
    mutationFn: async (userId: string) => {
      await usersApi.deleteUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
      toast.success('User deleted');
    },
  });
  
  // Trigger reindex mutation
  const triggerReindex = useMutation({
    mutationFn: async () => {
      await adminApi.triggerReindex();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminJobs'] });
      toast.success('Reindex started');
    },
  });
  
  // Cancel job mutation
  const cancelJob = useMutation({
    mutationFn: async (jobId: string) => {
      await adminApi.cancelJob(jobId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminJobs'] });
      toast.success('Job cancelled');
    },
  });
  
  const tabs = [
    { id: 'overview', name: 'Overview', icon: ServerStackIcon },
    { id: 'users', name: 'Users', icon: UsersIcon },
    { id: 'jobs', name: 'Jobs', icon: ClockIcon },
  ];
  
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <ShieldCheckIcon className="w-7 h-7" />
        Admin Dashboard
      </h1>
      
      {/* Pending approvals alert */}
      {pendingUsers && pendingUsers.length > 0 && (
        <div className="card p-4 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <UsersIcon className="w-6 h-6 text-yellow-600" />
              <div>
                <p className="font-medium text-yellow-800 dark:text-yellow-200">
                  {pendingUsers.length} user(s) pending approval
                </p>
                <p className="text-sm text-yellow-600 dark:text-yellow-400">
                  Review and approve new user registrations
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveTab('users')}
              className="btn-secondary"
            >
              Review
            </button>
          </div>
        </div>
      )}
      
      {/* Tabs */}
      <div className="flex gap-4 border-b border-dark-200 dark:border-dark-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as AdminTab)}
            className={clsx(
              'pb-3 px-1 font-medium border-b-2 transition-colors flex items-center gap-2',
              activeTab === tab.id
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-dark-500 hover:text-dark-700'
            )}
          >
            <tab.icon className="w-5 h-5" />
            {tab.name}
          </button>
        ))}
      </div>
      
      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card p-4">
              <p className="text-sm text-dark-500">Total Users</p>
              <p className="text-2xl font-bold">{stats?.total_users || 0}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-dark-500">Active Users</p>
              <p className="text-2xl font-bold">{stats?.active_users || 0}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-dark-500">Total Media</p>
              <p className="text-2xl font-bold">{stats?.total_media?.toLocaleString() || 0}</p>
            </div>
            <div className="card p-4">
              <p className="text-sm text-dark-500">Total Storage</p>
              <p className="text-2xl font-bold">{formatBytes(stats?.total_storage_bytes || 0)}</p>
            </div>
          </div>
          
          {/* Quick actions */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
            <div className="flex gap-4">
              <button
                onClick={() => triggerReindex.mutate()}
                disabled={triggerReindex.isPending}
                className="btn-primary flex items-center gap-2"
              >
                <ArrowPathIcon className={clsx('w-5 h-5', triggerReindex.isPending && 'animate-spin')} />
                Reindex All Users
              </button>
            </div>
          </div>
          
          {/* Running jobs */}
          {stats && (stats.jobs_running > 0 || stats.jobs_pending > 0) && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold mb-4">Active Jobs</h2>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                  <span>{stats.jobs_running} running</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                  <span>{stats.jobs_pending} pending</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-dark-50 dark:bg-dark-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">User</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Role</th>
                <th className="px-4 py-3 text-left text-sm font-medium">NAS Path</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Created</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100 dark:divide-dark-700">
              {usersLoading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                  </td>
                </tr>
              ) : users?.map((user) => (
                <tr key={user.id} className="hover:bg-dark-50 dark:hover:bg-dark-800">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium">{user.full_name || 'No name'}</p>
                      <p className="text-sm text-dark-500">{user.email}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {!user.is_approved ? (
                      <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs">
                        Pending
                      </span>
                    ) : user.is_active ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-1 rounded-full text-xs',
                      user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-dark-100 text-dark-700'
                    )}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-dark-500">
                    {user.nas_path || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-dark-500">
                    {format(new Date(user.created_at), 'PP')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {!user.is_approved && (
                        <>
                          <button
                            onClick={() => approveUser.mutate(user.id)}
                            className="p-1.5 text-green-600 hover:bg-green-50 rounded"
                            title="Approve"
                          >
                            <CheckCircleIcon className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => rejectUser.mutate(user.id)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                            title="Reject"
                          >
                            <XCircleIcon className="w-5 h-5" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => {
                          if (confirm('Delete this user?')) {
                            deleteUser.mutate(user.id);
                          }
                        }}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Delete"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Jobs Tab */}
      {activeTab === 'jobs' && (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-dark-50 dark:bg-dark-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Job Type</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Progress</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Started</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100 dark:divide-dark-700">
              {jobsLoading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
                  </td>
                </tr>
              ) : jobs?.map((job) => (
                <tr key={job.id} className="hover:bg-dark-50 dark:hover:bg-dark-800">
                  <td className="px-4 py-3 font-medium">{job.job_type}</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      job.status === 'completed' && 'bg-green-100 text-green-700',
                      job.status === 'running' && 'bg-blue-100 text-blue-700',
                      job.status === 'failed' && 'bg-red-100 text-red-700',
                      job.status === 'pending' && 'bg-yellow-100 text-yellow-700',
                      job.status === 'cancelled' && 'bg-dark-100 text-dark-700'
                    )}>
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-dark-200 dark:bg-dark-600 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 rounded-full transition-all"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                      <span className="text-sm text-dark-500">
                        {job.processed_items}/{job.total_items}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-dark-500">
                    {job.started_at ? format(new Date(job.started_at), 'Pp') : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {(job.status === 'running' || job.status === 'pending') && (
                      <button
                        onClick={() => cancelJob.mutate(job.id)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded"
                        title="Cancel"
                      >
                        <XCircleIcon className="w-5 h-5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
