import apiClient from '../axios';
import type { MaterialSustrato } from '../types';

export type DatosNuevoMaterial = Pick<MaterialSustrato, 'nombre'>;
/** La clave y la sede no se editan: las fórmulas citan el material por su clave. Todo
 * cambio lleva su justificación, que queda en la auditoría. */
export type CambiosMaterial = Partial<Pick<MaterialSustrato, 'nombre' | 'activo'>> & {
  _justificacion_auditoria?: string;
};

const RUTA = '/materiales-sustrato/';

const lista = (data: MaterialSustrato[] | { results: MaterialSustrato[] }) =>
  (Array.isArray(data) ? data : data.results);

/** Repository del catálogo de materiales (tipos de sustrato) de la sede. */
export const materialesSustratoApi = {
  async listar({ soloActivos = false }: { soloActivos?: boolean } = {}): Promise<MaterialSustrato[]> {
    const res = await apiClient.get<MaterialSustrato[] | { results: MaterialSustrato[] }>(
      RUTA, { params: soloActivos ? { activo: 'true' } : {} },
    );
    return lista(res.data);
  },

  async crear(datos: DatosNuevoMaterial): Promise<MaterialSustrato> {
    const res = await apiClient.post<MaterialSustrato>(RUTA, datos);
    return res.data;
  },

  async actualizar(id: number, cambios: CambiosMaterial): Promise<MaterialSustrato> {
    const res = await apiClient.patch<MaterialSustrato>(`${RUTA}${id}/`, cambios);
    return res.data;
  },
};
