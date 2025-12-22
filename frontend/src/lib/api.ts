import apiClient from './axios';
import { Sede } from './types';

// API functions for Sedes
export const getSedes = async (): Promise<Sede[]> => {
  const response = await apiClient.get<Sede[]>('/sedes/');
  return response.data;
};

export const createSede = async (sede: Omit<Sede, 'id'>): Promise<Sede> => {
  const response = await apiClient.post<Sede>('/sedes/', sede);
  return response.data;
};

export const updateSede = async (sede: Sede): Promise<Sede> => {
  const response = await apiClient.put<Sede>(`/sedes/${sede.id}/`, sede);
  return response.data;
};

export const deleteSede = async (id: number): Promise<void> => {
  await apiClient.delete(`/sedes/${id}/`);
};
