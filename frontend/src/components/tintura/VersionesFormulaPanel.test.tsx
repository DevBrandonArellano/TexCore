import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionesFormulaPanel } from './VersionesFormulaPanel';

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
  observaciones: 'Ajuste de temperatura de tintura',
  fecha: '2026-09-24T15:00:00Z', creada_por: 3, creada_por_nombre: 'tintorero1',
};
const V1 = {
  id: 11, numero: 1, es_oficial: false, motivo: 'Ensayo de laboratorio',
  observaciones: 'Ensayo de laboratorio',
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

function renderPanel(overrides: Partial<React.ComponentProps<typeof VersionesFormulaPanel>> = {}) {
  const props: React.ComponentProps<typeof VersionesFormulaPanel> = {
    formula: FORMULA,
    onCrearVersion: vi.fn().mockResolvedValue(true),
    onMarcarOficial: vi.fn().mockResolvedValue(true),
    onDerivar: vi.fn().mockResolvedValue(true),
    ...overrides,
  };
  return { ...render(<VersionesFormulaPanel {...props} />), props };
}

describe('VersionesFormulaPanel', () => {
  beforeEach(() => { mockGet.mockReset(); });

  it('dado una formula con versiones cuando renderiza entonces lista numero, oficial, observaciones y autor', async () => {
    mockApi([V2, V1]);
    renderPanel();

    await waitFor(() => expect(screen.getByText('Ajuste de temperatura de tintura')).toBeInTheDocument());
    expect(screen.getByText('Oficial')).toBeInTheDocument();
    expect(screen.getAllByText(/tintorero1/)).toHaveLength(2);
  });

  it('dado una formula sin versiones cuando renderiza entonces explica que se crea la primera al guardar un ensayo', async () => {
    mockApi([]);
    renderPanel();

    await waitFor(() => expect(screen.getByText(/guarda un ensayo para crear la primera/)).toBeInTheDocument());
    expect(screen.queryByText('Comparar versiones')).not.toBeInTheDocument();
  });

  it('dado error de la API cuando renderiza entonces muestra un mensaje de error', async () => {
    mockGet.mockRejectedValue(new Error('500'));
    renderPanel();

    await waitFor(() => expect(screen.getByText('No se pudo cargar el historial de versiones.')).toBeInTheDocument());
  });

  it('dado dos versiones cuando compara entonces pide el diff de la penultima a la ultima y lo muestra', async () => {
    mockApi([V2, V1]);
    renderPanel();
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Comparar' }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/formula-colors/7/versiones/1/diff/2/'));
    expect(await screen.findByText(/Jabonado \(agregada\)/)).toBeInTheDocument();
  });

  it('dado click en guardar version actual cuando confirma entonces llama a onCrearVersion y recarga', async () => {
    mockApi([]);
    const onCrearVersion = vi.fn().mockResolvedValue(true);
    renderPanel({ onCrearVersion });
    await waitFor(() => expect(screen.getByText(/guarda un ensayo/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Guardar versión actual/i }));
    await userEvent.type(screen.getByLabelText('Observaciones del ensayo'), 'Primer ensayo de laboratorio');

    mockApi([V1]);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar versión' }));

    await waitFor(() => expect(onCrearVersion).toHaveBeenCalledWith(7, 'Primer ensayo de laboratorio'));
  });

  it('dado una version no oficial cuando hace click en marcar oficial entonces llama a onMarcarOficial y recarga', async () => {
    mockApi([V1]);
    const onMarcarOficial = vi.fn().mockResolvedValue(true);
    renderPanel({ onMarcarOficial });
    await waitFor(() => expect(screen.getByText('Ensayo de laboratorio')).toBeInTheDocument());

    mockApi([{ ...V1, es_oficial: true }]);
    await userEvent.click(screen.getByRole('button', { name: 'Marcar oficial' }));

    await waitFor(() => expect(onMarcarOficial).toHaveBeenCalledWith(7, 1));
  });

  it('dado una version oficial cuando renderiza entonces no ofrece marcarla oficial de nuevo', async () => {
    mockApi([V2]);
    renderPanel();
    await waitFor(() => expect(screen.getByText('Oficial')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Marcar oficial' })).not.toBeInTheDocument();
  });

  it('dado una version sin observaciones ni nombre de autor cuando renderiza entonces usa el motivo como respaldo', async () => {
    mockApi([{ ...V1, observaciones: '', creada_por_nombre: null }]);
    renderPanel();
    await waitFor(() => expect(screen.getByText('Ensayo de laboratorio')).toBeInTheDocument());
  });

  it('dado onMarcarOficial rechazado cuando marca entonces no recarga el historial', async () => {
    mockApi([V1]);
    const onMarcarOficial = vi.fn().mockResolvedValue(false);
    renderPanel({ onMarcarOficial });
    await waitFor(() => expect(screen.getByText('Ensayo de laboratorio')).toBeInTheDocument());
    mockGet.mockClear();

    await userEvent.click(screen.getByRole('button', { name: 'Marcar oficial' }));

    await waitFor(() => expect(onMarcarOficial).toHaveBeenCalledWith(7, 1));
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado onCrearVersion rechazado cuando guarda entonces no recarga el historial', async () => {
    mockApi([]);
    const onCrearVersion = vi.fn().mockResolvedValue(false);
    renderPanel({ onCrearVersion });
    await waitFor(() => expect(screen.getByText(/guarda un ensayo/)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Guardar versión actual/i }));
    await userEvent.type(screen.getByLabelText('Observaciones del ensayo'), 'Primer ensayo de laboratorio');
    mockGet.mockClear();
    await userEvent.click(screen.getByRole('button', { name: 'Guardar versión' }));

    await waitFor(() => expect(onCrearVersion).toHaveBeenCalled());
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado error en la comparacion cuando falla la API entonces muestra un mensaje de error', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === `/formula-colors/${FORMULA.id}/versiones/`) return Promise.resolve({ data: [V2, V1] });
      if (url.includes('/diff/')) return Promise.reject(new Error('500'));
      return Promise.reject(new Error('url no esperada'));
    });
    renderPanel();
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Comparar' }));

    await waitFor(() => expect(screen.getByText('No se pudo comparar las versiones.')).toBeInTheDocument());
  });

  it('dado un diff con cambios de formula fase eliminada y detalles sin nombre cuando compara entonces resuelve los respaldos', async () => {
    const diffCompleto = {
      formula_id: 7, a: 1, b: 2,
      cambios: {
        formula: { tipo_sustrato: { a: 'algodon', b: 'poliester' } },
        fases: {
          agregadas: [],
          eliminadas: [{ orden: 3, proceso_codigo: 'SECADO', proceso_nombre: null, proceso_tipo: 'acabado', ciclo: null, temperatura: null, tiempo: null, detalles: [] }],
          modificadas: [{
            orden: 1, proceso_codigo: 'TINTURA', cambios: {},
            detalles: {
              agregados: [{ producto_id: 9, producto_codigo: null, producto_descripcion: null, tipo_calculo: 'gr_l', concentracion_gr_l: '1.000', porcentaje: null, orden_adicion: 1 }],
              eliminados: [{ producto_id: 10, producto_codigo: 'Q00999', producto_descripcion: null, tipo_calculo: 'gr_l', concentracion_gr_l: '1.000', porcentaje: null, orden_adicion: 1 }],
              modificados: [{ producto_id: 11, producto_codigo: null, cambios: { concentracion_gr_l: { a: '1.000', b: '2.000' } } }],
            },
          }],
        },
      },
    };
    mockApi([V2, V1], diffCompleto);
    renderPanel();
    await waitFor(() => expect(screen.getByText('Comparar versiones')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Comparar' }));

    expect(await screen.findByText('Datos de la fórmula')).toBeInTheDocument();
    expect(screen.getByText(/Fase 3: SECADO \(eliminada\)/)).toBeInTheDocument();
    expect(screen.getByText(/Producto 9/)).toBeInTheDocument();
    expect(screen.getByText(/Q00999/)).toBeInTheDocument();
    expect(screen.getByText('Producto 11', { exact: false })).toBeInTheDocument();
  });

  it('dado click en derivar desde una version cuando confirma entonces llama a onDerivar con el numero de esa version', async () => {
    mockApi([V2, V1]);
    const onDerivar = vi.fn().mockResolvedValue(true);
    renderPanel({ onDerivar });
    await waitFor(() => expect(screen.getByText('Oficial')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: 'Derivar desde v1' }));
    await userEvent.type(screen.getByLabelText('Código'), 'DERIV-01');
    await userEvent.type(screen.getByLabelText('Nombre del color'), 'derivado');
    await userEvent.click(screen.getByRole('button', { name: 'Derivar' }));

    await waitFor(() => expect(onDerivar).toHaveBeenCalledWith(7, expect.objectContaining({
      codigo: 'DERIV-01', nombre_color: 'DERIVADO', version_origen: 1,
    })));
  });
});
