import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionesFormulaSheet } from './VersionesFormulaSheet';

const mockGet = vi.fn();
vi.mock('../../lib/axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

// Select de Radix simplificado: cada opción es un botón (mismo patrón que FormulaQuimica.test)
const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const FORMULA = { id: 7, codigo: 'PES-T0191', nombre_color: 'AZUL' };

const V2 = {
  id: 12, numero: 2, es_oficial: true, motivo: 'Ajuste de temperatura de tintura',
  fecha: '2026-09-24T15:00:00Z', creada_por: 3, creada_por_nombre: 'tintorero1',
};
const V1 = {
  id: 11, numero: 1, es_oficial: false, motivo: 'Aprobada tras prueba de laboratorio',
  fecha: '2026-09-20T10:00:00Z', creada_por: 3, creada_por_nombre: 'tintorero1',
};

const DIFF = {
  formula_id: 7, a: 1, b: 2,
  cambios: {
    formula: {},
    fases: {
      agregadas: [{ orden: 2, proceso_codigo: 'JABONADO', proceso_nombre: 'Jabonado', proceso_tipo: 'lavado',
        ciclo: null, temperatura: 60, tiempo: 10, detalles: [] }],
      eliminadas: [],
      modificadas: [{
        orden: 1, proceso_codigo: 'TINTURA', cambios: { temperatura: { a: 90, b: 95 } },
        detalles: {
          agregados: [], eliminados: [],
          modificados: [{ producto_id: 5, producto_codigo: 'Q00610', cambios: { concentracion_gr_l: { a: '0.700', b: '0.800' } } }],
        },
      }],
    },
  },
};

function mockApi(versiones: any[], diff: any = DIFF) {
  mockGet.mockImplementation((url: string) => {
    if (url === `/formula-colors/${FORMULA.id}/versiones/`) return Promise.resolve({ data: versiones });
    if (url.includes('/diff/')) return Promise.resolve({ data: diff });
    return Promise.reject(new Error('url no esperada'));
  });
}

describe('VersionesFormulaSheet', () => {
  beforeEach(() => { mockGet.mockReset(); });

  it('dado sin formula cuando renderiza entonces no abre el panel ni consulta la API', () => {
    render(<VersionesFormulaSheet formula={null} onOpenChange={vi.fn()} />);
    expect(screen.queryByText('Historial de versiones')).not.toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado una formula con versiones cuando abre entonces lista numero, oficial, motivo y autor', async () => {
    mockApi([V2, V1]);
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('Ajuste de temperatura de tintura')).toBeInTheDocument());
    expect(screen.getByText('PES-T0191 — AZUL')).toBeInTheDocument();
    expect(screen.getByText('Oficial')).toBeInTheDocument();
    expect(screen.getAllByText(/tintorero1/)).toHaveLength(2);
  });

  it('dado una formula sin versiones cuando abre entonces explica que la primera se crea al aprobar', async () => {
    mockApi([]);
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);

    await waitFor(() => expect(screen.getByText(/se crea la primera al aprobarla/)).toBeInTheDocument());
    expect(screen.queryByText('Comparar versiones')).not.toBeInTheDocument();
  });

  it('dado error de la API cuando abre entonces muestra un mensaje de error', async () => {
    mockGet.mockRejectedValue(new Error('500'));
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('No se pudo cargar el historial de versiones.')).toBeInTheDocument());
  });

  it('dado dos versiones cuando compara entonces pide el diff de la penultima a la ultima y lo muestra', async () => {
    mockApi([V2, V1]);
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Comparar' }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/formula-colors/7/versiones/1/diff/2/'));
    expect(await screen.findByText(/Jabonado \(agregada\)/)).toBeInTheDocument();
    expect(screen.getByText('Fase 1 (TINTURA)')).toBeInTheDocument();
    expect(screen.getByText('90')).toBeInTheDocument();
    expect(screen.getByText('95')).toBeInTheDocument();
    expect(screen.getByText('Q00610')).toBeInTheDocument();
    expect(screen.getByText('0.800')).toBeInTheDocument();
  });

  it('dado la misma version en ambos lados cuando elige entonces no permite comparar', async () => {
    mockApi([V2, V1]);
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    // Desde = v2 (hay dos grupos de opciones v1/v2: el primero es «Desde»)
    await userEvent.click(screen.getAllByRole('button', { name: 'v2' })[0]);

    expect(screen.getByRole('button', { name: 'Comparar' })).toBeDisabled();
  });

  it('dado un diff sin cambios cuando compara entonces indica que las versiones son identicas', async () => {
    mockApi([V2, V1], { formula_id: 7, a: 1, b: 2, cambios: { formula: {}, fases: { agregadas: [], eliminadas: [], modificadas: [] } } });
    render(<VersionesFormulaSheet formula={FORMULA} onOpenChange={vi.fn()} />);
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Comparar' }));

    expect(await screen.findByText('Las versiones v1 y v2 son idénticas.')).toBeInTheDocument();
  });
});
