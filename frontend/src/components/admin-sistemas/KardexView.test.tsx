import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KardexView } from './KardexView';
import { parcial } from '../../testing/parcial';

// Sin test propio hasta ahora. Se mockea useKardex (ya testeado por su cuenta)
// para aislar las ramas propias de KardexView: columna de saldo condicional,
// estilos esEntrada/esSalida, paginación, y wiring de los 4 diálogos hijos.

const mockUseKardex = vi.fn();
vi.mock('./useKardex', () => ({
  useKardex: (...args: unknown[]) => mockUseKardex(...args),
}));

vi.mock('../bodeguero/EditarMovimientoDialog', () => ({
  EditarMovimientoDialog: ({ onSuccess, onClose }: import('react').ComponentProps<typeof import('../bodeguero/EditarMovimientoDialog').EditarMovimientoDialog>) => (
    <div>
      <button onClick={onSuccess}>confirmar-edicion</button>
      <button onClick={onClose}>cerrar-edicion</button>
    </div>
  ),
}));
vi.mock('../bodeguero/AuditoriaDialog', () => ({
  AuditoriaDialog: ({ onClose, movimientoId }: import('react').ComponentProps<typeof import('../bodeguero/AuditoriaDialog').AuditoriaDialog>) => (
    <div>
      <span>auditoria-{movimientoId}</span>
      <button onClick={onClose}>cerrar-auditoria</button>
    </div>
  ),
}));
vi.mock('../bodeguero/RegistrarMermaDialog', () => ({
  RegistrarMermaDialog: ({ open, onSuccess }: import('react').ComponentProps<typeof import('../bodeguero/RegistrarMermaDialog').RegistrarMermaDialog>) => (
    open ? <div><button onClick={onSuccess}>confirmar-merma</button></div> : null
  ),
}));
vi.mock('../bodeguero/EliminarMovimientoDialog', () => ({
  EliminarMovimientoDialog: ({ movimiento, onSuccess, onClose }: import('react').ComponentProps<typeof import('../bodeguero/EliminarMovimientoDialog').EliminarMovimientoDialog>) => (
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
  Select: ({ children, onValueChange }: import('react').ComponentProps<typeof import('../ui/select').Select>) => (
    <SelectCtx.Provider value={onValueChange ?? (() => {})}><div>{children}</div></SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectTrigger>) => <div>{children}</div>,
  SelectValue: ({ placeholder }: import('react').ComponentProps<typeof import('../ui/select').SelectValue>) => <span>{placeholder}</span>,
  SelectContent: ({ children }: import('react').ComponentProps<typeof import('../ui/select').SelectContent>) => <div>{children}</div>,
  SelectItem: ({ children, value }: import('react').ComponentProps<typeof import('../ui/select').SelectItem>) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));
vi.mock('../ui/product-select', () => ({
  ProductSelect: ({ onValueChange }: import('react').ComponentProps<typeof import('../ui/product-select').ProductSelect>) => (
    <button onClick={() => onValueChange('1')}>seleccionar-producto</button>
  ),
}));

function baseKardex(overrides: Record<string, unknown> = {}) {
  return {
    selectedBodega: 'all', setSelectedBodega: vi.fn(),
    selectedProducto: 'all', setSelectedProducto: vi.fn(),
    tipoOperacion: 'all', setTipoOperacion: vi.fn(),
    fechaInicio: '', setFechaInicio: vi.fn(),
    fechaFin: '', setFechaFin: vi.fn(),
    kardexData: [], isLoading: false, mostrarSaldo: false,
    currentPage: 1, setCurrentPage: vi.fn(), totalPages: 1, totalCount: 0, paginatedData: [],
    handleFetchKardex: vi.fn(), recargarPagina: vi.fn(), handleClearFilters: vi.fn(),
    exportarExcel: vi.fn(), exportando: false,
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

  it('dado consulta de kardex con saldo cuando renderiza entonces muestra la columna de saldo con el valor formateado', () => {
    mockUseKardex.mockReturnValue(baseKardex({
      mostrarSaldo: true,
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByText('Saldo')).toBeInTheDocument();
    expect(screen.getByText('10.00')).toBeInTheDocument();
  });

  it('dado fila sin saldo_acumulado cuando muestra la columna de saldo entonces muestra guion', () => {
    const movSinSaldo = { ...MOV_ENTRADA, saldo_acumulado: undefined };
    mockUseKardex.mockReturnValue(baseKardex({
      mostrarSaldo: true,
      kardexData: [movSinSaldo], paginatedData: [movSinSaldo],
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
  });

  it('dado filtros de producto y bodega elegidos sin consultar cuando renderiza entonces no muestra la columna de saldo', () => {
    // La columna depende de la consulta hecha, no de lo que se eligió después sin consultar.
    mockUseKardex.mockReturnValue(baseKardex({
      selectedProducto: '1', selectedBodega: '2', mostrarSaldo: false,
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], totalCount: 1,
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.queryByText('Saldo')).not.toBeInTheDocument();
  });

  it('dado click en Limpiar y Consultar y Exportar cuando se activan entonces llaman a sus handlers', async () => {
    const handleClearFilters = vi.fn();
    const handleFetchKardex = vi.fn();
    const exportarExcel = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ handleClearFilters, handleFetchKardex, exportarExcel }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    await userEvent.click(screen.getByRole('button', { name: 'Limpiar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Consultar' }));
    await userEvent.click(screen.getByRole('button', { name: /Exportar Excel/i }));

    expect(handleClearFilters).toHaveBeenCalled();
    expect(handleFetchKardex).toHaveBeenCalled();
    expect(exportarExcel).toHaveBeenCalled();
  });

  it('dado exportacion en curso cuando renderiza entonces deshabilita el boton de exportar', () => {
    mockUseKardex.mockReturnValue(baseKardex({ exportando: true }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByRole('button', { name: /Generando/i })).toBeDisabled();
  });

  it('dado resultados cuando renderiza entonces muestra el total de movimientos de la consulta', () => {
    mockUseKardex.mockReturnValue(baseKardex({
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], totalCount: 1234, totalPages: 62,
    }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);
    expect(screen.getByText(/1234 movimientos/)).toBeInTheDocument();
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

  it('dado click en editar cuando se confirma entonces recarga la pagina actual y llama onDataRefresh', async () => {
    const recargarPagina = vi.fn();
    const onDataRefresh = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], totalCount: 1, recargarPagina }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} onDataRefresh={onDataRefresh} />);

    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [, editBtn] = within(fila).getAllByRole('button');
    await userEvent.click(editBtn);
    await userEvent.click(screen.getByText('confirmar-edicion'));

    expect(recargarPagina).toHaveBeenCalled();
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

  it('dado click en eliminar cuando se confirma entonces recarga la pagina actual', async () => {
    const recargarPagina = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA], totalCount: 1, recargarPagina }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    const fila = screen.getByText('Hilo Azul').closest('tr') as HTMLElement;
    const [, , delBtn] = within(fila).getAllByRole('button');
    await userEvent.click(delBtn);
    await userEvent.click(screen.getByText('confirmar-eliminar'));
    expect(recargarPagina).toHaveBeenCalled();
  });

  it('dado click en registrar merma cuando se abre y se confirma entonces recarga la pagina actual', async () => {
    const recargarPagina = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({ recargarPagina }));
    render(<KardexView productos={[]} bodegas={[]} proveedores={[]} />);

    await userEvent.click(screen.getByRole('button', { name: /Registrar Merma/i }));
    await userEvent.click(screen.getByText('confirmar-merma'));
    expect(recargarPagina).toHaveBeenCalled();
  });

  it('dado mas de una pagina cuando cambia de pagina con los botones entonces llama setCurrentPage', async () => {
    const setCurrentPage = vi.fn();
    mockUseKardex.mockReturnValue(baseKardex({
      kardexData: [MOV_ENTRADA], paginatedData: [MOV_ENTRADA],
      currentPage: 2, totalPages: 3, totalCount: 60, setCurrentPage,
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
      currentPage: 1, totalPages: 3, totalCount: 60, setCurrentPage,
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
      currentPage: 1, totalPages: 3, totalCount: 60, setCurrentPage,
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
    const { container } = render(<KardexView productos={[]} bodegas={[parcial({ id: 1, nombre: 'B1' })]} proveedores={[]} />);

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
