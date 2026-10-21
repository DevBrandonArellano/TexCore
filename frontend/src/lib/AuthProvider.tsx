import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from './axios';
import { AuthContext, type Profile } from './auth';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Empieza en true para verificar la sesión al cargar
  const navigate = useNavigate();

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/token/logout/');
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setProfile(null);
      navigate('/', { replace: true });
    }
  }, [navigate]);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await apiClient.post<Profile>('/token/', { username, password });
      setProfile(response.data);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };
  
  // Al cargar la app verifica si hay una cookie de sesión válida
  useEffect(() => {
    const checkUserSession = async () => {
      try {
        const response = await apiClient.get<Profile>('/profile/');
        setProfile(response.data);
      } catch {
        setProfile(null);
        console.log('No active session found.');
      } finally {
        setIsLoading(false);
      }
    };

    checkUserSession();

    // Cuando el interceptor de axios detecta refresh_token_invalid, emite este
    // evento para que AuthProvider limpie el perfil sin recargar la SPA.
    const handleSessionExpired = () => setProfile(null);
    window.addEventListener('auth:session-expired', handleSessionExpired);
    return () => window.removeEventListener('auth:session-expired', handleSessionExpired);
  }, []);

  const isAuthenticated = !!profile;

  const value = {
    profile,
    login,
    logout,
    isAuthenticated,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {isLoading ? null : children} 
    </AuthContext.Provider>
  );
}
