import apiClient from '../axios';
import type { DosificacionFormulaResultado, FormulaColor, VersionFormula, VersionFormulaResumen } from '../types';

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

  /** Catálogo de fórmulas de la sede (sin laboratorio), para elegir color, material y fórmula. */
  async listar(): Promise<FormulaColor[]> {
    const res = await apiClient.get<FormulaColor[]>('/formula-colors/');
    return res.data;
  },

  /** Historial de versiones de una fórmula, de la más nueva a la más antigua. */
  async versiones(formulaId: number): Promise<VersionFormulaResumen[]> {
    const res = await apiClient.get<VersionFormulaResumen[]>(`/formula-colors/${formulaId}/versiones/`);
    return res.data;
  },

  /**
   * Hoja de dosificación en PDF. Sin `numeroVersion` imprime la oficial (o la receta
   * viva como borrador); con él, la versión pedida, marcada como borrador si no es la oficial.
   */
  async imprimirDosificacion(formulaId: number, peso: number, litros: number, numeroVersion?: number): Promise<Blob> {
    const cuerpo = numeroVersion === undefined
      ? { peso, litros }
      : { peso, litros, numero_version: numeroVersion };
    const res = await apiClient.post<Blob>(
      `/formula-colors/${formulaId}/imprimir-dosificacion/`, cuerpo, { responseType: 'blob' },
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
