import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSedes, createSede, updateSede, deleteSede } from '../lib/api';
import { Sede } from '../lib/types';
import { toast } from 'sonner';

const SEDES_QUERY_KEY = 'sedes';

export const useSedes = () => {
  return useQuery<Sede[], Error>({
    queryKey: [SEDES_QUERY_KEY],
    queryFn: getSedes,
  });
};

export const useCreateSede = () => {
  const queryClient = useQueryClient();
  return useMutation<Sede, Error, Omit<Sede, 'id'>>({
    mutationFn: createSede,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEDES_QUERY_KEY] });
      toast.success('Sede creada exitosamente');
    },
    onError: (error) => {
      toast.error('Error al crear la sede', { description: error.message });
    },
  });
};

export const useUpdateSede = () => {
  const queryClient = useQueryClient();
  return useMutation<Sede, Error, Sede>({
    mutationFn: updateSede,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEDES_QUERY_KEY] });
      toast.success('Sede actualizada exitosamente');
    },
    onError: (error) => {
      toast.error('Error al actualizar la sede', { description: error.message });
    },
  });
};

export const useDeleteSede = () => {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: deleteSede,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEDES_QUERY_KEY] });
      toast.success('Sede eliminada exitosamente');
    },
    onError: (error) => {
      toast.error('Error al eliminar la sede', { description: error.message });
    },
  });
};
