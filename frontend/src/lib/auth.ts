import { createContext, useContext } from 'react';
import { User } from './types';

export interface Profile {
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

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
