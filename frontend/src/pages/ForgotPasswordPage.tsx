import { useState } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '@/services/api';
import toast from 'react-hot-toast';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (error: any) {
      // Don't reveal if email exists or not
      setSent(true);
    } finally {
      setIsLoading(false);
    }
  };
  
  if (sent) {
    return (
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Check your email</h2>
        <p className="text-dark-500 mb-6">
          If an account exists with that email, we've sent password reset instructions.
        </p>
        <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          Back to login
        </Link>
      </div>
    );
  }
  
  return (
    <div>
      <h2 className="text-2xl font-bold text-center mb-2">Forgot password?</h2>
      <p className="text-center text-dark-500 mb-6">
        Enter your email and we'll send you reset instructions.
      </p>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            placeholder="you@example.com"
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary w-full"
        >
          {isLoading ? 'Sending...' : 'Send reset link'}
        </button>
      </form>
      
      <p className="text-center mt-6 text-sm text-dark-500">
        Remember your password?{' '}
        <Link to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
