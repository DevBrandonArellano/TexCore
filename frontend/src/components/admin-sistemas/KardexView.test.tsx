import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KardexView } from './KardexView';

// Sin test propio hasta ahora. Se mockea useKardex (ya testeado por su cuenta)
// para aislar las ramas propias de KardexView: columna de saldo condicional,
// estilos esEntrada/esSalida, paginación, y wiring de los 4 diálogos hijos.

const mockUseKardex = vi.fn();
vi.mock('./useKardex', () => ({
  useKardex: (...args: any[]) => mockUseKardex(...args),
}));

vi.mock('../bodeguero/EditarMovimientoDialog', () => ({
  EditarMovimientoDialog: ({ onSuccess, onClose }: any) => (
    <div>
      <button onClick={onSuccess}>confirmar-edicion</button>
      <button onClick={onClose}>cerrar-edicion</button>
    </div>
  ),
}));
vi.mock('../bodeguero/AuditoriaDialog', () => ({
  AuditoriaDialog: ({ onClose, movimientoId }: any) => (
    <div>
      <span>auditoria-{movimientoId}</span>
      <button onClick={onClose}>cerrar-auditoria</button>
    </div>
  ),
}));
vi.mock('../bodeguero/RegistrarMermaDialog', () => ({
  RegistrarMermaDialog: ({ open, onSuccess }: any) => (
    open ? <div><button onClick={onSuccess}>confirmar-merma</button></div> : null
  ),
}));
vi.mock('../bodeguero/EliminarMovimientoDialog', () => ({
  EliminarMovimientoDialog: ({ movimiento, onSuccess, onClose }: any) => (
    movimiento ? (
      <div>
        <button onClick={onSuccess}>confirmar-eliminar</button>
        <button onClick={onClose}>cerrar-eliminar</button>
      </div>
    ) : null
  ),
}));

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
vi.mock('../ui/product-select', () => ({
  ProductSelect: ({ onValueChange }: any) => (
    <button onClick={() => onValueChange('1')}>seleccionar-producto</button>
  ),
}));

function baseKardex(overrides: Partial<any> = {}) {
  return {
    selectedBodega: 'all', setSelectedBodega: vi.fn(),
    selectedProducto: 'all', setSelectedProducto: vi.fn(),
    tipoOperacion: 'all', setTipoOperacion: vi.fn(),
    fechaInicio: '', setFechaInicio: vi.fn(),
    fechaFin: '', setFechaFin: vi.fn(),
    kardexData: [], isLoading: false,
    currentPage: 1, setCurrentPage: vi.fn(), totalPages: 1, paginatedData: [],
    handleFetchKardex: vi.fn(), handleClearFilters: vi.fn(), exportToCSV: vi.fn(),
    ...overrides,
  };
}

const MOV_ENTRADA = {
  id: 1, fecha: '2026-01-01T10:00:00Z', producto: 'Hilo Azul',
  bodega_origen: 'Norte', bodega_destino: 'Central', tipo_movimiento: 'entrada',
  cantidad: 10, documento_ref: 'DOC-1', esEntrada: true, esSalida: false, saldo_acumulado: 10,
};
const MOV_SALIDA = {
  id: 2, fecha: '2026-01-02T10:00:00Z', producto: 'Hilo Rojo',
  bodega_origen: 'Central', bodega_destino: 'Norte', tipo_movimiento: 'salida',
  cantidad: 5, documento_ref: null, esEntrada: false, esSalida: true, saldo_acumulado: 5,
};

describe('KardexView', () => {
  beforeEach(() => {
    mockUseKardex.mockReset();
  });

  it('dado sin datos cuando renderiza entonces muestra el mensaje de sin movimientos', () => {
    mockUseKardex.mockReturnValue(baseKardex());
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByText('No se encontraron movimientos con los filtros seleccionados.')).toBeInTheDocument();
  });

  it('dado isLoading en true y sin datos cuando renderiza entonces muestra el mensaje de carga', () => {
    mockUseKardex.mockReturnValue(baseKardex({ isLoading: true }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByText('Cargando movimientos...')).toBeInTheDocument();
  });

  it('dado movimientos de entrada y salida sin filtro de producto/bodega cuando renderiza entonces no muestra columna de saldo', () => {
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA, MOV_SALIDA] }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.queryByText('Saldo')).not.toBeInTheDocument();
    expect(screen.getByText('+10')).toBeInTheDocument();
    expect(screen.getByText('-5')).toBeInTheDocument();
    expect(screen.getByText('-')).toBeInTheDocument(); // documento_ref null
  });

  it('dado producto y bodega seleccionados cuando renderiza entonces muestra la columna de saldo con el valor formateado', () => {
    mockUseKardex.mockReturnValue(baseKardex({
      selectedProducto: '1', selectedBodega: '2',
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByText('Saldo')).toBeInTheDocument();
    expect(screen.getByText('10.00')).toBeInTheDocument();
  });

  it('dado fila sin saldo_acumulado cuando muestra la columna de saldo entonces muestra guion', () => {
    const movSinSaldo = { ...MOV_ENTRADA, saldo_acumulado: undefined };
    mockUseKardex.mockReturnValue(baseKardex({
      selectedProducto: '1', selectedBodega: '2',
      kardexData: [movSinSaldo], paginatedData: [movSinSaldo],
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
  });

  it('dado click en Limpiar y Consultar y Exportar cuando se activan entonces llaman a sus handlers', async () => {
    const handleClearFilters = vi.fn();
    const handleFetchKardex = vi.fn();
    const exportToCSV = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ handleClearFilters, handleFetchKardex, exportToCSV }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    await userEvent.click(screen.getByRole('button', { name: 'Limpiar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Consultar' }));
    await userEvent.click(screen.getByRole('button', { name: /Exportar CSV/i }));

    expect(handleClearFilters).toHaveBeenCalled();
    expect(handleFetchKardex).toHaveBeenCalled();
    expect(exportToCSV).toHaveBeenCalled();
  });

  it('dado click en el boton de auditoria cuando se activa entonces abre el dialogo de auditoria con el id correcto', async () => {
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA] }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    // Orden fijo en la celda "Acciones": auditoria, editar, eliminar.
    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [auditBtn] = within(fila).getAllByRole('button');
    await userEvent.click(auditBtn);
    expect(screen.getByText('auditoria-1')).toBeInTheDocument();

    await userEvent.click(screen.getByText('cerrar-auditoria'));
    expect(screen.queryByText('auditoria-1')).not.toBeInTheDocument();
  });

  it('dado click en editar cuando se confirma entonces refresca el kardex y llama onDataRefresh', async () => {
    const handleFetchKardex = vi.fn();
    const onDataRefresh = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], handleFetchKardex }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} onDataRefresh={onDataRefresh} />);

    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [, editBtn] = within(fila).getAllByRole('button');
    await userEvent.click(editBtn);
    await userEvent.click(screen.getByText('confirmar-edicion'));

    expect(handleFetchKardex).toHaveBeenCalled();
    expect(onDataRefresh).toHaveBeenCalled();
  });

  it('dado sin onDataRefresh cuando se confirma una edicion entonces no falla', async () => {
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA] }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [, editBtn] = within(fila).getAllByRole('button');
    await userEvent.click(editBtn);
    await userEvent.click(screen.getByText('confirmar-edicion'));
    expect(screen.queryByText('confirmar-edicion')).not.toBeInTheDocument();
  });

  it('dado click en eliminar cuando se confirma entonces refresca el kardex', async () => {
    const handleFetchKardex = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], handleFetchKardex }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [, , delBtn] = within(fila).getAllByRole('button');
    await userEvent.click(delBtn);
    await userEvent.click(screen.getByText('confirmar-eliminar'));
    expect(handleFetchKardex).toHaveBeenCalled();
  });

  it('dado click en registrar merma cuando se abre y se confirma entonces refresca el kardex', async () => {
    const handleFetchKardex = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ handleFetchKardex }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    await userEvent.click(screen.getByRole('button', { name: /Registrar Merma/i }));
    await userEvent.click(screen.getByText('confirmar-merma'));
    expect(handleFetchKardex).toHaveBeenCalled();
  });

  it('dado mas de una pagina cuando cambia de pagina con los botones entonces llama setCurrentPage', async () => {
    const setCurrentPage = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
      currentPage: 2, totalPages: 3, setCurrentPage,
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    await userEvent.click(screen.getByRole('button', { name: /Anterior/i }));
    expect(setCurrentPage).toHaveBeenCalledWith(1);
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    expect(setCurrentPage).toHaveBeenCalledWith(3);
  });

  it('dado el input Ir a pagina cuando escribe una pagina valida y presiona Enter entonces llama setCurrentPage', async () => {
    const setCurrentPage = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
      currentPage: 1, totalPages: 3, setCurrentPage,
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');
    expect(setCurrentPage).toHaveBeenCalledWith(2);
  });

  it('dado el input Ir a pagina cuando escribe un numero fuera de rango entonces no llama setCurrentPage', async () => {
    const setCurrentPage = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
      currentPage: 1, totalPages: 3, setCurrentPage,
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();
    expect(setCurrentPage).not.toHaveBeenCalled();
  });

  it('dado cambio en los filtros de select y fecha cuando se activan entonces llaman a sus setters', async () => {
    const setSelectedBodega = vi.fn();
    const setSelectedProducto = vi.fn();
    const setTipoOperacion = vi.fn();
    const setFechaInicio = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ setSelectedBodega, setSelectedProducto, setTipoOperacion, setFechaInicio }));
    const { container } = render(<KardexView productos={[]} bodegas={[{ id: 1, nombre: 'B1' } as any]} proveedores={[]} />);

    await userEvent.click(screen.getByText('Todas las Bodegas'));
    expect(setSelectedBodega).toHaveBeenCalledWith('all');
    await userEvent.click(screen.getByText('seleccionar-producto'));
    expect(setSelectedProducto).toHaveBeenCalledWith('1');
    await userEvent.click(screen.getByText('Entradas (Ingresos)'));
    expect(setTipoOperacion).toHaveBeenCalledWith('entrada');

    const fechaDesde = container.querySelectorAll('input[type="date"]')[0];
    await userEvent.type(fechaDesde, '2026-01-01');
    expect(setFechaInicio).toHaveBeenCalled();
  });
});
