/**
 * ISTQB — Nivel: Componente
 * Técnica : partición de equivalencia (sin configurar / configurada), valor límite
 *           (justificación de 10 caracteres) y transición de estados al guardar.
 * Cubre   : ConfiguracionEmpaqueView — TEX-43, equivalencias de empaque de una sede.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const obtenerMock = vi.fn();
const guardarMock = vi.fn();
vi.mock('../../lib/api/configuracionEmpaqueApi', () => ({
  configuracionEmpaqueApi: {
    obtener: (...args: unknown[]) => obtenerMock(...args),
    guardar: (...args: unknown[]) => guardarMock(...args),
  },
}));

const toastSuccessMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}));

import { ConfiguracionEmpaqueView } from './ConfiguracionEmpaqueView';

const SIN_CONFIGURAR = {
  sede_id: 3, sede_nombre: 'Sede Norte', configurada: false,
  fundas_por_bano: null, conos_por_funda: null, conos_por_bano: null,
};
const CONFIGURADA = {
  sede_id: 3, sede_nombre: 'Sede Norte', configurada: true,
  fundas_por_bano: 15, conos_por_funda: 15, conos_por_bano: 225,
};
const JUSTIFICACION = 'Nuevo proveedor de conos';

describe('ConfiguracionEmpaqueView', () => {
  beforeEach(() => {
    obtenerMock.mockReset();
    guardarMock.mockReset();
    toastSuccessMock.mockReset();
    toastErrorMock.mockReset();
  });

  it('dado una sede sin configurar cuando carga entonces avisa que debe registrarse', async () => {
    obtenerMock.mockResolvedValue(SIN_CONFIGURAR);
    render(<ConfiguracionEmpaqueView />);
    expect(await screen.findByText(/no tiene configuradas las equivalencias de empaque/i)).toBeInTheDocument();
    expect(obtenerMock).toHaveBeenCalledWith(undefined);
  });

  it('dado una sede configurada cuando carga entonces muestra la equivalencia completa', async () => {
    obtenerMock.mockResolvedValue(CONFIGURADA);
    render(<ConfiguracionEmpaqueView />);
    expect(await screen.findByText('1 baño = 15 fundas = 225 conos')).toBeInTheDocument();
    expect(screen.getByLabelText('Fundas por baño')).toHaveValue(15);
  });

  it('dado sede elegida por el admin de sistemas cuando carga entonces consulta esa sede', async () => {
    obtenerMock.mockResolvedValue(CONFIGURADA);
    render(<ConfiguracionEmpaqueView sedeId="7" />);
    await waitFor(() => expect(obtenerMock).toHaveBeenCalledWith('7'));
  });

  it('dado cambios cuando escribe entonces recalcula los conos por baño', async () => {
    obtenerMock.mockResolvedValue(CONFIGURADA);
    render(<ConfiguracionEmpaqueView />);
    const fundas = await screen.findByLabelText('Fundas por baño');
    await userEvent.clear(fundas);
    await userEvent.type(fundas, '10');
    expect(screen.getByText('1 baño = 10 fundas = 150 conos')).toBeInTheDocument();
  });

  it('dado justificacion corta cuando guarda entonces no llama a la API', async () => {
    obtenerMock.mockResolvedValue(CONFIGURADA);
    render(<ConfiguracionEmpaqueView />);
    await userEvent.type(await screen.findByLabelText('Justificación'), 'corta');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar equivalencias' }));
    expect(guardarMock).not.toHaveBeenCalled();
    expect(screen.getByText('La justificación debe tener al menos 10 caracteres.')).toBeInTheDocument();
  });

  it('dado datos validos cuando guarda entonces envia la configuracion y confirma', async () => {
    obtenerMock.mockResolvedValue(SIN_CONFIGURAR);
    guardarMock.mockResolvedValue({ ...CONFIGURADA, fundas_por_bano: 12, conos_por_funda: 18, conos_por_bano: 216 });
    render(<ConfiguracionEmpaqueView sedeId="3" />);
    await userEvent.type(await screen.findByLabelText('Fundas por baño'), '12');
    await userEvent.type(screen.getByLabelText('Conos por funda'), '18');
    await userEvent.type(screen.getByLabelText('Justificación'), JUSTIFICACION);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar equivalencias' }));

    await waitFor(() => expect(guardarMock).toHaveBeenCalledWith(
      { fundas_por_bano: 12, conos_por_funda: 18, justificacion: JUSTIFICACION }, '3'));
    expect(toastSuccessMock).toHaveBeenCalledWith('Equivalencias de empaque guardadas.');
    expect(await screen.findByText('1 baño = 12 fundas = 216 conos')).toBeInTheDocument();
    expect(screen.getByLabelText('Justificación')).toHaveValue('');
  });

  it('dado error del servidor cuando guarda entonces lo muestra', async () => {
    obtenerMock.mockResolvedValue(CONFIGURADA);
    guardarMock.mockRejectedValue(new Error('caido'));
    render(<ConfiguracionEmpaqueView />);
    await userEvent.type(await screen.findByLabelText('Justificación'), JUSTIFICACION);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar equivalencias' }));
    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });
});
