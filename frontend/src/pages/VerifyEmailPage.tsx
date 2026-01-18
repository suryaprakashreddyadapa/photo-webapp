import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { authApi } from '@/services/api';
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  
  useEffect(() => {
    const verify = async () => {
      if (!token) {
        setStatus('error');
        setMessage('Invalid verification link');
        return;
      }
      
      try {
        await authApi.verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been verified! You can now log in once an administrator approves your account.');
      } catch (error: any) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Verification failed. The link may have expired.');
      }
    };
    
    verify();
  }, [token]);
  
  return (
    <div className="text-center">
      {status === 'loading' && (
        <>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p>Verifying your email...</p>
        </>
      )}
      
      {status === 'success' && (
        <>
          <CheckCircleIcon className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Email Verified!</h2>
          <p className="text-dark-500 mb-6">{message}</p>
          <Link to="/login" className="btn-primary">
            Go to Login
          </Link>
        </>
      )}
      
      {status === 'error' && (
        <>
          <XCircleIcon className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Verification Failed</h2>
          <p className="text-dark-500 mb-6">{message}</p>
          <Link to="/login" className="btn-primary">
            Go to Login
          </Link>
        </>
      )}
    </div>
  );
}
