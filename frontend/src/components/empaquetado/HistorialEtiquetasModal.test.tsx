import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HistorialEtiquetasModal } from './HistorialEtiquetasModal';

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

// ReimprimirModal usa el Select de radix — se mockea igual que en
// EmpaquetadoDashboard.test.tsx para poder elegir un motivo con un click
// simple en jsdom, sin lidiar con el portal/dropdown real de radix.
const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return (
      <button type="button" onClick={() => onValueChange(value)}>
        {children}
      </button>
    );
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: (...args: any[]) => toastSuccessMock(...args),
  },
}));

// printLabel (usado por ReimprimirModal) cae a portapapeles cuando no hay
// impresora Zebra ni se puede generar el PDF en jsdom — se stubea igual que
// en EmpaquetadoDashboard.test.tsx para que la reimpresión resuelva limpio.
const writeTextMock = vi.fn().mockResolvedValue(undefined);
Object.assign(navigator, { clipboard: { writeText: writeTextMock } });

const EVENTO_ORIGINAL = {
  id: 1, tipo_evento: 'ORIGINAL', secuencia: 1, version: 1, motivo: null,
  detalle_motivo: '', usuario: 'operario1', timestamp: '2026-07-01T08:10:00Z',
  formato: 'ZPL', anulada: true, anula_a: null,
};

const EVENTO_REETIQUETADO = {
  id: 2, tipo_evento: 'REETIQUETADO', secuencia: 2, version: 2, motivo: 'RECLASIFICACION',
  detalle_motivo: 'Cambio de calidad', usuario: 'jefe_area1', timestamp: '2026-07-02T09:00:00Z',
  formato: 'ZPL', anulada: false, anula_a: 1,
};

describe('HistorialEtiquetasModal', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  it('dado open en false cuando renderiza entonces no consulta el historial', () => {
    render(<HistorialEtiquetasModal open={false} onOpenChange={vi.fn()} loteId={1} codigoLote="L-001" />);
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado open en true cuando monta entonces consulta el historial del lote correcto', async () => {
    mockGet.mockResolvedValue({ data: [EVENTO_ORIGINAL, EVENTO_REETIQUETADO] });
    render(<HistorialEtiquetasModal open={true} onOpenChange={vi.fn()} loteId={7} codigoLote="L-007" />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/7/etiquetas/'));
    expect(await screen.findByText('Original')).toBeInTheDocument();
    expect(screen.getByText('Reetiquetado')).toBeInTheDocument();
    expect(screen.getByText('RECLASIFICACION')).toBeInTheDocument();
    expect(screen.getByText('jefe_area1')).toBeInTheDocument();
    expect(screen.getByText('Anulada')).toBeInTheDocument();
    expect(screen.getByText('Vigente')).toBeInTheDocument();
  });

  it('dado sin eventos cuando carga entonces muestra el mensaje de vacio', async () => {
    mockGet.mockResolvedValue({ data: [] });
    render(<HistorialEtiquetasModal open={true} onOpenChange={vi.fn()} loteId={1} codigoLote="L-001" />);

    await waitFor(() => expect(screen.getByText('Sin eventos de etiqueta registrados.')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /reimprimir etiqueta vigente/i })).toBeDisabled();
  });

  it('dado error al cargar cuando falla la peticion entonces muestra un toast de error', async () => {
    mockGet.mockRejectedValue(new Error('network error'));
    render(<HistorialEtiquetasModal open={true} onOpenChange={vi.fn()} loteId={1} codigoLote="L-001" />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar el historial de etiquetas.'));
  });

  it('dado un evento vigente cuando hay uno entonces habilita reimprimir etiqueta vigente', async () => {
    mockGet.mockResolvedValue({ data: [EVENTO_ORIGINAL, EVENTO_REETIQUETADO] });
    render(<HistorialEtiquetasModal open={true} onOpenChange={vi.fn()} loteId={7} codigoLote="L-007" />);

    await waitFor(() => expect(screen.getByText('Reetiquetado')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /reimprimir etiqueta vigente/i })).toBeEnabled();
  });

  it('dado clic en reimprimir etiqueta vigente cuando confirma motivo entonces llama al endpoint y recarga el historial', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url.includes('/etiquetas/')) return Promise.resolve({ data: [EVENTO_REETIQUETADO] });
      return Promise.resolve({ data: [] });
    });
    mockPost.mockResolvedValue({ data: { zpl: 'ZPL-DATA', evento: { tipo_evento: 'REIMPRESION', version: 2, secuencia: 3 } } });
    render(<HistorialEtiquetasModal open={true} onOpenChange={vi.fn()} loteId={7} codigoLote="L-007" />);
    await waitFor(() => expect(screen.getByText('Reetiquetado')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /reimprimir etiqueta vigente/i }));
    await userEvent.click(await screen.findByRole('button', { name: 'Etiqueta Dañada' }));
    await userEvent.click(screen.getByRole('button', { name: /^Reimprimir$/i }));

    await waitFor(() => expect(mockPost).toHaveBeenCalledWith(
      '/lotes-produccion/7/reimprimir/',
      expect.objectContaining({ motivo: 'DANIADA' }),
    ));
    // onReimpreso recarga el historial: la llamada a /etiquetas/ debe repetirse
    await waitFor(() => expect(
      mockGet.mock.calls.filter((c) => c[0] === '/lotes-produccion/7/etiquetas/').length,
    ).toBeGreaterThanOrEqual(2));
  });
});
