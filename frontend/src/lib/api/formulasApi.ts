import apiClient from '../axios';
import type { DosificacionFormulaResultado, FormulaColor, VersionFormula } from '../types';

/**
 * Repository de fórmulas de color: cálculos y consultas de una fórmula guardada.
 * Los componentes no arman URLs.
 */
export const formulasApi = {
  async calcularDosificacion(formulaId: number, peso: number, litros: number): Promise<DosificacionFormulaResultado> {
    const res = await apiClient.post<DosificacionFormulaResultado>(
      `/formula-colors/${formulaId}/calcular-dosificacion/`, { peso, litros },
    );
    return res.data;
  },

  async derivadas(formulaId: number): Promise<FormulaColor[]> {
    const res = await apiClient.get<FormulaColor[]>(`/formula-colors/${formulaId}/derivadas/`);
    return res.data;
  },

  async version(formulaId: number, numero: number): Promise<VersionFormula> {
    const res = await apiClient.get<VersionFormula>(`/formula-colors/${formulaId}/versiones/${numero}/`);
    return res.data;
  },
};
