import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';
import { Loader } from 'lucide-react';

/**
 * Component to handle OAuth callback redirects
 * This component processes the OAuth callback from providers like Google
 */
export const AuthCallback = () => {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Process the OAuth callback
    const handleAuthCallback = async () => {
      try {
        // Get the auth code from the URL
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const queryParams = new URLSearchParams(window.location.search);
        
        // If there's an error in the URL, display it
        const errorParam = hashParams.get('error') || queryParams.get('error');
        if (errorParam) {
          setError(errorParam);
          return;
        }

        // Exchange the auth code for a session
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
          throw error;
        }

        if (data?.session) {
          // Successfully authenticated, redirect to home
          navigate('/');
        } else {
          // No session found, redirect to login
          navigate('/login');
        }
      } catch (err) {
        console.error('Error during auth callback:', err);
        setError('Authentication failed. Please try again.');
      }
    };

    handleAuthCallback();
  }, [navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      {error ? (
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-500 mb-2">Authentication Error</h2>
          <p className="text-gray-600 dark:text-gray-400">{error}</p>
          <button 
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            onClick={() => navigate('/login')}
          >
            Return to Login
          </button>
        </div>
      ) : (
        <div className="text-center">
          <Loader className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">Completing authentication...</p>
        </div>
      )}
    </div>
  );
};

export default AuthCallback;
