import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User } from './types';
import apiClient from './axios';

interface Profile {
  user: User;
  role: string | null;
}

interface AuthContextType {
  profile: Profile | null;
  login: (username: string, password:string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean; // Add a loading state for session checking
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Start as true to check session on load

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/token/logout/');
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setProfile(null);
    }
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      // The backend now returns user data on login, and sets the HttpOnly cookie.
      const response = await apiClient.post<Profile>('/token/', { username, password });
      setProfile(response.data);
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };
  
  // This effect runs once on app load to check if a valid session cookie exists.
  useEffect(() => {
    const checkUserSession = async () => {
      try {
        // The browser will automatically send the HttpOnly cookie.
        // If the session is valid, this will return the user's profile.
        const response = await apiClient.get<Profile>('/profile/');
        setProfile(response.data);
      } catch (error) {
        // If the request fails (e.g., 401 Unauthorized), it means no valid session.
        // The profile state will remain null.
        setProfile(null);
        console.log('No active session found.');
      } finally {
        setIsLoading(false);
      }
    };

    checkUserSession();
  }, []);

  const isAuthenticated = !!profile;

  const value = {
    profile,
    login,
    logout,
    isAuthenticated,
    isLoading,
  };

  // While checking the session, you might want to show a loading spinner
  // instead of rendering the children (which might redirect to /login).
  return (
    <AuthContext.Provider value={value}>
      {isLoading ? null : children} 
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
