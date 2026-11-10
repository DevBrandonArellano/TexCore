/**
 * ISTQB — Nivel: Componente (hook)
 * Técnica : partición de equivalencia (sin resumen, bodegas con y sin stock)
 * Cubre   : useStockEjecutivo.stockPorBodega — el gráfico se arma con el resumen del
 *           servidor (/inventory/stock/resumen/), no sumando filas por lote.
 */
import { describe, it, expect } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useStockEjecutivo } from './useStockEjecutivo';

describe('useStockEjecutivo', () => {
  it('dado sin resumen cuando monta entonces el grafico queda vacio', () => {
    const { result } = renderHook(() => useStockEjecutivo());
    expect(result.current.stockPorBodega).toEqual([]);
  });

  it('dado resumen por bodega cuando llega entonces ordena de mayor a menor, abrevia y conserva el id', () => {
    const { result } = renderHook(() => useStockEjecutivo());
    act(() => {
      result.current.setResumenStock({
        total_cantidad: 160.555,
        productos: 3,
        bodegas: 3,
        por_bodega: [
          { bodega_id: 1, bodega: 'Merma', cantidad: 10.555, filas: 2 },
          { bodega_id: 2, bodega: 'Producto Terminado Empresa 1', cantidad: '150', filas: 5 },
          { bodega_id: 3, bodega: 'Vacía', cantidad: 0, filas: 1 },
        ],
      });
    });

    expect(result.current.stockPorBodega).toEqual([
      { name: expect.any(String), fullBodegaName: 'Producto Terminado Empresa 1', bodegaId: 2, value: 150 },
      { name: 'Merma', fullBodegaName: 'Merma', bodegaId: 1, value: 10.56 },
    ]);
    expect(result.current.stockPorBodega[0].name.length).toBeLessThanOrEqual(17);
  });

  it('dado búsqueda cuando filtra alertas entonces busca por código o nombre y ordena el top por faltante', () => {
    const { result } = renderHook(() => useStockEjecutivo());
    act(() => {
      result.current.setAlertas([
        { producto: 'Hilo azul', producto_codigo: 'H-AZ', bodega: 'B1', stock_actual: '1', stock_minimo: '5', faltante: 4 },
        { producto: 'Hilo rojo largo de prueba', producto_codigo: '', bodega: 'B1', stock_actual: '0', stock_minimo: '9', faltante: 9 },
        { producto: 'Tela', producto_codigo: 'T-1', bodega: 'B2', stock_actual: '0', stock_minimo: '1' },
      ]);
      result.current.setBusquedaAlertas('  HILO ');
    });
    expect(result.current.alertasFiltradas.map(a => a.producto)).toEqual(['Hilo azul', 'Hilo rojo largo de prueba']);
    expect(result.current.topAlertas.map(a => a.faltante)).toEqual([9, 4]);
    expect(result.current.topAlertas[0].name.length).toBeLessThanOrEqual(16);

    act(() => result.current.setBusquedaAlertas('t-1'));
    expect(result.current.topAlertas).toEqual([{ name: 'T-1', faltante: 0 }]);
  });
});

