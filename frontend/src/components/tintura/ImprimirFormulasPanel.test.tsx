/**
 * Técnicas ISTQB aplicadas (CTFL v4.0):
 * - Partición de equivalencia (EP): catálogo con/sin fórmulas; color con uno o varios
 *   materiales; fórmula con/sin versión estándar; versión oficial y no oficial.
 * - Caja negra (CN): cascada color → material → fórmula; impresión de una versión concreta.
 * - Caja blanca (CB): rama de error al cargar el historial de versiones.
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ImprimirFormulasPanel } from './ImprimirFormulasPanel';

const mockListar = vi.fn();
const mockVersiones = vi.fn();
const mockImprimir = vi.fn();
vi.mock('../../lib/api/formulasApi', () => ({
  formulasApi: {
    listar: (...a: unknown[]) => mockListar(...a),
    versiones: (...a: unknown[]) => mockVersiones(...a),
    imprimirDosificacion: (...a: unknown[]) => mockImprimir(...a),
  },
}));

vi.mock('./DerivadasFormula', () => ({
  DerivadasFormula: ({ formulaId }: { formulaId: number }) => (
    <div data-testid="matices">Matices de la fórmula {formulaId}</div>
  ),
}));

const formula = (over: Record<string, unknown>) => ({
  id: 1, codigo: 'AZ-ALG', nombre_color: 'Azul Marino', tipo_sustrato: 'algodon',
  tipo_sustrato_display: 'Algodón', version: 1, version_oficial: 1, estado: 'aprobada',
  es_laboratorio: false, ...over,
});

const CATALOGO = [
  formula({ id: 1, codigo: 'AZ-ALG', nombre_color: 'Azul Marino', tipo_sustrato: 'algodon', tipo_sustrato_display: 'Algodón', version_oficial: 1 }),
  formula({ id: 2, codigo: 'AZ-POL', nombre_color: 'Azul Marino', tipo_sustrato: 'poliester', tipo_sustrato_display: 'Poliéster', version_oficial: null }),
  formula({ id: 3, codigo: 'RJ-ALG', nombre_color: 'Rojo Intenso', tipo_sustrato: 'algodon', tipo_sustrato_display: 'Algodón', version_oficial: 2 }),
];

const VERSIONES_AZ_ALG = [
  { id: 11, numero: 2, es_oficial: false, motivo: 'Ensayo más rojizo', observaciones: 'sale muy rojizo', fecha: '2026-11-10T10:00:00Z', creada_por: null, creada_por_nombre: 'tintorero1' },
  { id: 10, numero: 1, es_oficial: true, motivo: 'Receta aprobada en laboratorio', observaciones: '', fecha: '2026-11-01T10:00:00Z', creada_por: null, creada_por_nombre: 'tintorero1' },
];

async function elegirColorYMaterial(user: ReturnType<typeof userEvent.setup>, color: string, material: string) {
  await user.selectOptions(screen.getByLabelText('Color'), color);
  await user.selectOptions(screen.getByLabelText('Tipo de material'), material);
}

describe('ImprimirFormulasPanel', () => {
  beforeAll(() => {
    // jsdom no implementa estos métodos que usa el diálogo para abrir el PDF.
    vi.stubGlobal('open', vi.fn());
    URL.createObjectURL = vi.fn(() => 'blob:pdf');
  });

  beforeEach(() => {
    mockListar.mockReset();
    mockVersiones.mockReset();
    mockImprimir.mockReset();
    mockListar.mockResolvedValue(CATALOGO);
    mockVersiones.mockResolvedValue(VERSIONES_AZ_ALG);
    mockImprimir.mockResolvedValue(new Blob(['%PDF']));
  });

  it('dado el catálogo de la sede cuando carga entonces ofrece cada color una sola vez', async () => {
    render(<ImprimirFormulasPanel />);
    const colores = await screen.findByLabelText('Color');
    const opciones = within(colores).getAllByRole('option').map((o) => o.textContent);
    expect(opciones).toEqual(['Seleccione un color', 'Azul Marino', 'Rojo Intenso']);
  });

  it('dado un color cuando se elige entonces ofrece solo los materiales de ese color', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await user.selectOptions(await screen.findByLabelText('Color'), 'Azul Marino');

    const materiales = within(screen.getByLabelText('Tipo de material')).getAllByRole('option').map((o) => o.textContent);
    expect(materiales).toEqual(['Seleccione un material', 'Algodón', 'Poliéster']);
  });

  it('dado color y material cuando se eligen entonces ofrece la fórmula de ese par', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'poliester');

    expect(within(screen.getByLabelText('Fórmula')).getByRole('option', { name: /AZ-POL/ })).toBeInTheDocument();
    expect(within(screen.getByLabelText('Fórmula')).queryByRole('option', { name: /AZ-ALG/ })).not.toBeInTheDocument();
  });

  it('dado una fórmula con versión oficial cuando se selecciona entonces muestra la estándar y las demás versiones', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'algodon');

    expect(await screen.findByText('Versión estándar')).toBeInTheDocument();
    expect(screen.getByText('v1 (oficial)')).toBeInTheDocument();
    expect(mockVersiones).toHaveBeenCalledWith(1);
    const otras = await screen.findByRole('list', { name: 'Otras versiones' });
    expect(within(otras).getByText('v2')).toBeInTheDocument();
    expect(within(otras).getByText('Ensayo más rojizo')).toBeInTheDocument();
    expect(within(otras).queryByText('v1')).not.toBeInTheDocument();
  });

  it('dado una fórmula sin versión oficial cuando se selecciona entonces ofrece imprimir la receta en edición como borrador', async () => {
    const user = userEvent.setup();
    mockVersiones.mockResolvedValueOnce([]);
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'poliester');

    expect(await screen.findByText('Sin versión estándar')).toBeInTheDocument();
    expect(screen.getByText(/se imprime la receta en edición como BORRADOR/)).toBeInTheDocument();
  });

  it('dado una versión cuando se pulsa imprimir entonces abre el diálogo y envía ese número de versión', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'algodon');
    const otras = await screen.findByRole('list', { name: 'Otras versiones' });

    await user.click(within(otras).getByRole('button', { name: 'Imprimir versión 2' }));
    await user.type(screen.getByLabelText('Peso de la tela (kg)'), '100');
    await user.type(screen.getByLabelText('Litros de baño'), '800');
    await user.click(screen.getByRole('button', { name: 'Imprimir hoja' }));

    await waitFor(() => expect(mockImprimir).toHaveBeenCalledWith(1, 100, 800, 2));
  });

  it('dado la versión estándar cuando se pulsa imprimir entonces envía el número de la oficial', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'algodon');
    await screen.findByRole('list', { name: 'Otras versiones' });

    await user.click(screen.getByRole('button', { name: 'Imprimir versión estándar' }));
    await user.type(screen.getByLabelText('Peso de la tela (kg)'), '50');
    await user.type(screen.getByLabelText('Litros de baño'), '400');
    await user.click(screen.getByRole('button', { name: 'Imprimir hoja' }));

    await waitFor(() => expect(mockImprimir).toHaveBeenCalledWith(1, 50, 400, 1));
  });

  it('dado una fórmula cuando se elige entonces muestra sus matices (derivadas)', async () => {
    const user = userEvent.setup();
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'algodon');

    expect(await screen.findByTestId('matices')).toHaveTextContent('Matices de la fórmula 1');
  });

  it('dado el catálogo vacío cuando carga entonces indica que no hay fórmulas para imprimir', async () => {
    mockListar.mockResolvedValueOnce([]);
    render(<ImprimirFormulasPanel />);
    expect(await screen.findByText('No hay fórmulas para imprimir.')).toBeInTheDocument();
  });

  it('dado un error al cargar el historial de versiones cuando se elige la fórmula entonces lo indica', async () => {
    const user = userEvent.setup();
    mockVersiones.mockRejectedValueOnce(new Error('500'));
    render(<ImprimirFormulasPanel />);
    await screen.findByLabelText('Color');
    await elegirColorYMaterial(user, 'Azul Marino', 'algodon');

    expect(await screen.findByText('No se pudo cargar el historial de versiones.')).toBeInTheDocument();
  });
});
