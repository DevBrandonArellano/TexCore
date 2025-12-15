import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User } from './types';
import apiClient from './axios';
import { jwtDecode } from 'jwt-decode';

interface Profile {
  user: User;
  role: string | null;
}

interface AuthContextType {
  profile: Profile | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);

  const logout = useCallback(() => {
    setProfile(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    apiClient.defaults.headers.Authorization = null;
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const response = await apiClient.get<Profile>('/profile/');
      setProfile(response.data);
      return true;
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      logout();
      return false;
    }
  }, [logout]);

  useEffect(() => {
    const loadUserFromStorage = async () => {
      const accessToken = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');

      if (accessToken) {
        try {
          const decodedToken: any = jwtDecode(accessToken);
          if (decodedToken.exp * 1000 < Date.now()) { // Token expired
            if (refreshToken) {
              try {
                const refreshResponse = await apiClient.post('/token/refresh/', { refresh: refreshToken });
                const newAccessToken = refreshResponse.data.access;
                localStorage.setItem('access_token', newAccessToken);
                apiClient.defaults.headers.Authorization = `Bearer ${newAccessToken}`;
                await fetchProfile();
              } catch (refreshError) {
                console.error('Error refreshing token:', refreshError);
                logout();
              }
            } else {
              logout();
            }
          } else { // Token is valid
            apiClient.defaults.headers.Authorization = `Bearer ${accessToken}`;
            await fetchProfile();
          }
        } catch (error) {
          console.error('Error decoding or validating token:', error);
          logout();
        }
      }
    };

    loadUserFromStorage();
  }, [logout, fetchProfile]);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await apiClient.post('/token/', { username, password });
      const { access, refresh } = response.data;

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      apiClient.defaults.headers.Authorization = `Bearer ${access}`;
      
      const profileFetched = await fetchProfile();
      
      return profileFetched;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const isAuthenticated = !!profile;

  const value = {
    profile,
    login,
    logout,
    isAuthenticated,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};


