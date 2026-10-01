import apiClient from '../axios';
import type { DesempenoOperario, ReporteEficienciaArea, VendedorResumen } from '../../types/indicadores';

/** Repository de indicadores: eficiencia del área, desempeño del operario y vendedores. */
export const indicadoresApi = {
  async reporteEficienciaArea(areaId: number): Promise<ReporteEficienciaArea> {
    const res = await apiClient.get<ReporteEficienciaArea>(`/areas/${areaId}/reporte-eficiencia/`);
    return res.data;
  },

  async desempenoOperario(usuarioId: number): Promise<DesempenoOperario> {
    const res = await apiClient.get<DesempenoOperario>(`/users/${usuarioId}/desempeno/`);
    return res.data;
  },

  async vendedores(): Promise<VendedorResumen[]> {
    const res = await apiClient.get<VendedorResumen[]>('/users/vendedores/');
    return res.data;
  },
};
