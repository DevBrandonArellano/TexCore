import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReportesView } from './ReportesView';

// 55/84.2/30.8% — el archivo es casi puro cableado de botones a
// handleExport(reportType, params). Se mockea useReportesExport para
// aislar el componente y clickear los 7 botones de exportación, el mejor
// ratio funciones/esfuerzo del repo según el informe de testabilidad.

const mockHandleExport = vi.fn();
vi.mock('./useReportesExport', () => ({
  useReportesExport: () => ({ loading: {}, handleExport: mockHandleExport }),
}));

// Shim de Radix Select — usado tanto por ReportesView como por ProductSelect
// (que importa el mismo módulo '../ui/select').
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

const BODEGA = { id: 1, nombre: 'Bodega Central' } as any;
const PRODUCTOS: any[] = [];

async function seleccionarBodega() {
  await userEvent.click(screen.getByText('Bodega Central'));
}

describe('ReportesView', () => {
  beforeEach(() => {
    mockHandleExport.mockReset();
  });

  it('dado sedeId cuando renderiza entonces muestra el badge de sede', () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} sedeId="3" />);
    expect(screen.getByText(/Sede ID: 3/)).toBeInTheDocument();
  });

  it('dado sin sedeId cuando renderiza entonces no muestra el badge de sede', () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    expect(screen.queryByText(/Sede ID:/)).not.toBeInTheDocument();
  });

  it('dado bodega seleccionada cuando clickea exportar kardex entonces llama handleExport con los filtros', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    await userEvent.click(screen.getByRole('button', { name: /Exportar Kardex/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('kardex', expect.objectContaining({
      producto_id: '', fecha_inicio: '', fecha_fin: '',
    }));
  });

  it('dado bodega seleccionada cuando clickea descargar stock actual entonces llama handleExport', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    await userEvent.click(screen.getByRole('button', { name: /Descargar Stock Actual/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('stock-actual');
  });

  it('dado bodega seleccionada cuando clickea exportar aging entonces llama handleExport con dias por defecto', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    await userEvent.click(screen.getByRole('button', { name: /Exportar Aging/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('aging', { dias: '30' });
  });

  it('dado bodega seleccionada cuando clickea descargar stock en cero entonces llama handleExport', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    await userEvent.click(screen.getByRole('button', { name: /Descargar Stock en Cero/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('stock-cero');
  });

  it('dado bodega y fechas seleccionadas cuando clickea rotacion entonces llama handleExport con fechas', async () => {
    const { container } = render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    const fechas = container.querySelectorAll('input[type="date"]');
    fireEvent.change(fechas[0], { target: { value: '2026-01-01' } });
    fireEvent.change(fechas[1], { target: { value: '2026-01-31' } });
    await userEvent.click(screen.getByRole('button', { name: /^Rotación$/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('rotacion', { fecha_inicio: '2026-01-01', fecha_fin: '2026-01-31' });
  });

  it('dado bodega y fechas seleccionadas cuando clickea resumen entonces llama handleExport con fechas', async () => {
    const { container } = render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    const fechas = container.querySelectorAll('input[type="date"]');
    fireEvent.change(fechas[0], { target: { value: '2026-01-01' } });
    fireEvent.change(fechas[1], { target: { value: '2026-01-31' } });
    await userEvent.click(screen.getByRole('button', { name: /^Resumen$/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('resumen-movimientos', { fecha_inicio: '2026-01-01', fecha_fin: '2026-01-31' });
  });

  it('dado catalogo de productos cuando clickea descargar entonces llama handleExport sin requerir bodega', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    // No seleccionamos bodega: el catálogo de productos no la requiere.
    await userEvent.click(screen.getByRole('button', { name: /Descargar Catálogo/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('productos');
  });

  it('dado sin bodega seleccionada cuando intenta exportar kardex entonces el boton esta deshabilitado', () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    expect(screen.getByRole('button', { name: /Exportar Kardex/i })).toBeDisabled();
  });

  it('dado cambio de rango de antiguedad cuando selecciona critico entonces exporta aging con ese valor', async () => {
    render(<ReportesView bodegas={[BODEGA]} productos={PRODUCTOS} />);
    await seleccionarBodega();
    await userEvent.click(screen.getByText(/Crítico: más de 180 días/));
    await userEvent.click(screen.getByRole('button', { name: /Exportar Aging/i }));
    expect(mockHandleExport).toHaveBeenCalledWith('aging', { dias: '180' });
  });
});
