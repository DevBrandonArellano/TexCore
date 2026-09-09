import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ManageFormulas } from './ManageFormulas';
import type { FormulaColor } from '../../lib/types';

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

const FORMULA_1: FormulaColor = {
  id: 1,
  codigo: 'ROJ-001',
  nombre_color: 'Rojo Carmesí',
  description: 'Color base rojo',
  tipo_sustrato: 'algodon',
  version: 1,
  estado: 'en_pruebas',
  observaciones: 'Nota de laboratorio',
  detalles: [{ id: 1, producto: 5, cantidad: '10.00' }],
};

const FORMULA_2: FormulaColor = {
  id: 2,
  codigo: 'AZL-002',
  nombre_color: 'Azul Marino',
  description: 'Color base azul',
  tipo_sustrato: 'poliester',
  version: 1,
  estado: 'aprobada',
  observaciones: '',
  detalles: [],
};

function renderComponent(props: Partial<React.ComponentProps<typeof ManageFormulas>> = {}) {
  const defaultProps: React.ComponentProps<typeof ManageFormulas> = {
    formulas: [],
    onFormulaCreate: vi.fn().mockResolvedValue(true),
    onFormulaUpdate: vi.fn().mockResolvedValue(true),
    onFormulaDelete: vi.fn(),
    loading: false,
  };
  return render(
    <MemoryRouter>
      <ManageFormulas {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

function getRow(codigo: string) {
  return screen.getByText(codigo).closest('tr') as HTMLTableRowElement;
}

describe('ManageFormulas', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado sin formulas cuando carga entonces la tabla no muestra filas de datos', async () => {
    renderComponent({ formulas: [] });
    expect(screen.queryByText('ROJ-001')).not.toBeInTheDocument();
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
  });

  it('dado formulas existentes cuando carga entonces las lista con codigo nombre y descripcion', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    expect(screen.getByText('ROJ-001')).toBeInTheDocument();
    expect(screen.getByText('Rojo Carmesí')).toBeInTheDocument();
    expect(screen.getByText('Color base rojo')).toBeInTheDocument();
    expect(screen.getByText('AZL-002')).toBeInTheDocument();
  });

  it('dado loading en true cuando renderiza entonces muestra skeletons en vez de datos', async () => {
    const { container } = renderComponent({ formulas: [FORMULA_1], loading: true });
    expect(screen.queryByText('ROJ-001')).not.toBeInTheDocument();
    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it('dado busqueda por codigo cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    await userEvent.type(
      screen.getByPlaceholderText('Buscar por código o nombre de color...'),
      'ROJ',
    );
    await waitFor(() => expect(screen.queryByText('AZL-002')).not.toBeInTheDocument());
    expect(screen.getByText('ROJ-001')).toBeInTheDocument();
  });

  it('dado busqueda por nombre de color cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    await userEvent.type(
      screen.getByPlaceholderText('Buscar por código o nombre de color...'),
      'marino',
    );
    await waitFor(() => expect(screen.queryByText('ROJ-001')).not.toBeInTheDocument());
    expect(screen.getByText('AZL-002')).toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando carga entonces pagina y el boton siguiente avanza de pagina', async () => {
    const manyFormulas: FormulaColor[] = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1,
      id: i + 1,
      codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('COD-001')).toBeInTheDocument();
    expect(screen.queryByText('COD-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('COD-021')).toBeInTheDocument();
    expect(screen.queryByText('COD-001')).not.toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const manyFormulas: FormulaColor[] = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado mas de 20 formulas cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const manyFormulas: FormulaColor[] = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado nueva formula cuando deja campos vacios y crea entonces muestra errores y no llama a onFormulaCreate', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });

    await userEvent.click(screen.getByRole('button', { name: /Nueva Fórmula/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    expect(screen.getByText('El código es requerido')).toBeInTheDocument();
    expect(screen.getByText('El nombre del color es requerido')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onFormulaCreate).not.toHaveBeenCalled();
  });

  it('dado datos validos cuando crea una formula entonces llama a onFormulaCreate con el payload correcto', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });

    await userEvent.click(screen.getByRole('button', { name: /Nueva Fórmula/i }));
    await userEvent.type(screen.getByLabelText(/Código/), 'AZL-003');
    await userEvent.type(screen.getByLabelText(/Nombre del Color/), 'Azul Cielo');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(onFormulaCreate).toHaveBeenCalledWith(expect.objectContaining({
      codigo: 'AZL-003',
      nombre_color: 'Azul Cielo',
      description: '',
      tipo_sustrato: 'algodon',
      estado: 'en_pruebas',
      observaciones: '',
      detalles: [],
    })));
  });

  it('dado creacion exitosa cuando se completa entonces cierra el dialogo', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });

    await userEvent.click(screen.getByRole('button', { name: /Nueva Fórmula/i }));
    await userEvent.type(screen.getByLabelText(/Código/), 'AZL-003');
    await userEvent.type(screen.getByLabelText(/Nombre del Color/), 'Azul Cielo');
    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Nueva Fórmula' })).not.toBeInTheDocument());
  });

  it('dado editar una formula existente cuando abre el dialogo entonces precarga sus datos', async () => {
    renderComponent({ formulas: [FORMULA_1] });

    const row = getRow('ROJ-001');
    const [editButton] = within(row).getAllByRole('button');
    await userEvent.click(editButton);

    expect(screen.getByRole('heading', { name: 'Editar Fórmula' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Código/)).toHaveValue('ROJ-001');
    expect(screen.getByLabelText(/Nombre del Color/)).toHaveValue('Rojo Carmesí');
    expect(screen.getByLabelText('Descripción')).toHaveValue('Color base rojo');
    expect(screen.getByLabelText(/Justificación de auditoría/)).toHaveValue('');
  });

  it('dado editar sin justificacion cuando intenta actualizar entonces muestra error y no llama a onFormulaUpdate', async () => {
    const onFormulaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ formulas: [FORMULA_1], onFormulaUpdate });

    const row = getRow('ROJ-001');
    const [editButton] = within(row).getAllByRole('button');
    await userEvent.click(editButton);
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Fórmula' }));

    expect(screen.getByText('La justificación es obligatoria para actualizar la fórmula')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Por favor completa todos los campos requeridos');
    expect(onFormulaUpdate).not.toHaveBeenCalled();
  });

  it('dado editar con justificacion cuando actualiza entonces llama a onFormulaUpdate con el id y preserva detalles', async () => {
    const onFormulaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ formulas: [FORMULA_1], onFormulaUpdate });

    const row = getRow('ROJ-001');
    const [editButton] = within(row).getAllByRole('button');
    await userEvent.click(editButton);
    await userEvent.type(
      screen.getByLabelText(/Justificación de auditoría/),
      'Ajuste de fórmula por prueba de laboratorio',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Fórmula' }));

    await waitFor(() => expect(onFormulaUpdate).toHaveBeenCalledWith(1, expect.objectContaining({
      codigo: 'ROJ-001',
      nombre_color: 'Rojo Carmesí',
      description: 'Color base rojo',
      _justificacion_auditoria: 'Ajuste de fórmula por prueba de laboratorio',
      tipo_sustrato: 'algodon',
      estado: 'en_pruebas',
      observaciones: 'Nota de laboratorio',
      detalles: FORMULA_1.detalles,
    })));
  });

  it('dado click en eliminar cuando se hace click entonces llama a onFormulaDelete con el id de la formula', async () => {
    const onFormulaDelete = vi.fn();
    renderComponent({ formulas: [FORMULA_1], onFormulaDelete });

    const row = getRow('ROJ-001');
    const [, deleteButton] = within(row).getAllByRole('button');
    await userEvent.click(deleteButton);

    expect(onFormulaDelete).toHaveBeenCalledWith(1);
  });
});
