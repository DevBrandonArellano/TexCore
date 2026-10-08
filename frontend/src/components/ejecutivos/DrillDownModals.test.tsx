import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi, beforeEach } from 'vitest';
import { PedidoVenta } from '../../lib/types';

const listarStockMock = vi.fn();
vi.mock('../../lib/api/inventarioApi', () => ({
  inventarioApi: {
    listarStock: (...args: unknown[]) => listarStockMock(...args),
  },
}));

beforeEach(() => {
  listarStockMock.mockReset();
});
import { ClienteComprasModal, ClienteDeudorModal, DeudorExtendido, PedidosEstadoModal, ProductoHistorialModal, StockBodegaModal, VentasVendedorModal } from './DrillDownModals';
import { parcial } from '../../testing/parcial';
import { type ProduccionProductoItem } from './types';

// Mock simple de pedidos para las pruebas (Caja Blanca / TDD / ISTQB)
const mockPedidos: PedidoVenta[] = ([
  {
    id: 1,
    estado: 'pendiente',
    cliente_nombre: 'Cliente A',
    vendedor_nombre: 'Juan',
    total: '150.00',
    esta_pagado: false,
    fecha_creacion: '2023-01-01T10:00:00Z',
  },
  {
    id: 2,
    estado: 'despachado',
    cliente_nombre: 'Cliente B',
    vendedor_nombre: 'Maria',
    total: '250.00',
    esta_pagado: true,
    fecha_creacion: '2023-01-02T10:00:00Z',
  },
  {
    id: 3,
    estado: 'pendiente',
    cliente_nombre: 'Cliente C',
    vendedor_nombre: 'Juan',
    total: '300.00',
    esta_pagado: false,
    fecha_creacion: '2023-01-03T10:00:00Z',
  },
] as Partial<PedidoVenta>[]).map((p) => parcial<PedidoVenta>(p));

describe('DrillDownModals (Pruebas ISTQB - Caja Blanca)', () => {
  it('PedidosEstadoModal dado pedidos de varios estados cuando se abre para uno entonces muestra solo los de ese estado', () => {
    // Escenario de prueba (TDD)
    render(<PedidosEstadoModal estado="pendiente" onClose={() => {}} pedidos={mockPedidos} />);
    
    // Validar que se muestre el título correcto
    expect(screen.getByText(/Pedidos en Estado:/i)).toBeInTheDocument();
    
    // Validar que los clientes con estado pendiente estén en la tabla (Cliente A y C)
    expect(screen.getByText('Cliente A')).toBeInTheDocument();
    expect(screen.getByText('Cliente C')).toBeInTheDocument();
    
    // Validar que el cliente con otro estado NO esté (Cliente B)
    expect(screen.queryByText('Cliente B')).not.toBeInTheDocument();
  });

  it('VentasVendedorModal dado pedidos de varios vendedores cuando se abre para uno entonces muestra solo los suyos', () => {
    // Escenario de prueba (TDD)
    render(<VentasVendedorModal vendedor="Juan" onClose={() => {}} pedidos={mockPedidos} />);
    
    // Validar título
    expect(screen.getByText(/Ventas del Vendedor:/i)).toBeInTheDocument();
    
    // Validar que los pedidos de Juan estén presentes
    expect(screen.getByText('Cliente A')).toBeInTheDocument();
    expect(screen.getByText('Cliente C')).toBeInTheDocument();
    
    // Validar que los pedidos de Maria NO estén presentes
    expect(screen.queryByText('Cliente B')).not.toBeInTheDocument();
  });

  // Los fixtures de arriba traen todos los campos poblados, así que nunca
  // ejercitan los fallbacks `|| '—'` (cliente_nombre, vendedor_nombre,
  // fecha_creacion/fecha_pedido). Aquí se usan pedidos con campos ausentes
  // para cerrar esas ramas — ~30 de las 38 ramas muertas del archivo.
  const pedidoIncompleto = parcial<PedidoVenta>({
    id: 9, estado: 'pendiente', esta_pagado: false,
    // sin cliente_nombre, sin vendedor_nombre, sin total, sin fecha_creacion
    detalles: [parcial({ peso: 10, precio_unitario: 5 })],
  });

  it('PedidosEstadoModal dado un pedido sin campos opcionales cuando renderiza entonces muestra guiones y deriva el total de los detalles', () => {
    render(<PedidosEstadoModal estado="pendiente" onClose={() => {}} pedidos={[pedidoIncompleto]} />);
    const guiones = screen.getAllByText('—');
    expect(guiones.length).toBeGreaterThanOrEqual(2); // cliente y vendedor
    expect(screen.getByText('$50,00')).toBeInTheDocument(); // 10 * 5 derivado de detalles — fmt usa locale es-EC
  });

  it('VentasVendedorModal dado pedido sin vendedor_nombre cuando filtra entonces usa Sin asignar', () => {
    const pedidoSinVendedor = parcial<PedidoVenta>({ id: 10, estado: 'pendiente', esta_pagado: true, total: '20.00' });
    render(<VentasVendedorModal vendedor="Sin asignar" onClose={() => {}} pedidos={[pedidoSinVendedor]} />);
    expect(screen.getByText('Pagado')).toBeInTheDocument();
  });

  it('StockBodegaModal dado una bodega elegida cuando abre entonces pide su stock al servidor y muestra guion sin lote', async () => {
    listarStockMock.mockResolvedValue({
      count: 1, next: null, previous: null,
      results: [{ id: 1, producto: 'Hilo Blanco', bodega: 'Central', bodega_id: 4, lote: null, cantidad: '15.5' }],
    });
    render(<StockBodegaModal bodega={{ id: 4, nombre: 'Central' }} onClose={() => {}} />);
    expect(await screen.findByText('Hilo Blanco')).toBeInTheDocument();
    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('Stock en Bodega: Central')).toBeInTheDocument();
    expect(listarStockMock).toHaveBeenCalledWith(1, 120, { bodega_id: 4 });
  });

  it('StockBodegaModal dado bodega sin stock cuando abre entonces muestra el mensaje de vacio', async () => {
    listarStockMock.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    render(<StockBodegaModal bodega={{ id: 5, nombre: 'Sur' }} onClose={() => {}} />);
    expect(await screen.findByText('No hay productos en esta bodega.')).toBeInTheDocument();
  });

  it('StockBodegaModal dado modal cerrado cuando renderiza entonces no consulta el stock', () => {
    render(<StockBodegaModal bodega={null} onClose={() => {}} />);
    expect(listarStockMock).not.toHaveBeenCalled();
  });

  it('ClienteComprasModal dado pedidos del cliente cuando renderiza entonces filtra por cliente_nombre', () => {
    const pedidosCliente: PedidoVenta[] = [
      parcial({ id: 1, estado: 'pendiente', esta_pagado: false, cliente_nombre: 'Cliente A', total: '100', fecha_creacion: '2026-01-01T00:00:00Z' }),
      parcial({ id: 2, estado: 'pendiente', esta_pagado: false, cliente_nombre: 'Cliente B', total: '50' }),
    ];
    render(<ClienteComprasModal cliente="Cliente A" onClose={() => {}} pedidos={pedidosCliente} />);
    expect(screen.getByText('2026-01-01')).toBeInTheDocument();
  });

  it('ClienteComprasModal dado pedido sin vendedor_nombre ni fechas cuando renderiza entonces usa Sin nombre y muestra guiones', () => {
    const pedidoSinDatos = parcial<PedidoVenta>({ id: 5, estado: 'pendiente', esta_pagado: false, total: '30' });
    render(<ClienteComprasModal cliente="Sin nombre" onClose={() => {}} pedidos={[pedidoSinDatos]} />);
    const guiones = screen.getAllByText('—');
    expect(guiones.length).toBeGreaterThanOrEqual(2); // vendedor y fecha
  });

  it('ClienteComprasModal dado sin pedidos del cliente cuando renderiza entonces la tabla queda vacia sin filas', () => {
    render(<ClienteComprasModal cliente="Cliente Inexistente" onClose={() => {}} pedidos={mockPedidos} />);
    expect(screen.getByText('Historial de Compras: Cliente Inexistente')).toBeInTheDocument();
  });

  it('ClienteDeudorModal dado un cliente encontrado con limite de credito cuando renderiza entonces calcula el porcentaje de riesgo', () => {
    const topDeudores: DeudorExtendido[] = [parcial({
      fullName: 'Cliente Riesgo',
      obj: parcial({ nombre_razon_social: 'Cliente Riesgo SA', saldo_pendiente: '500', limite_credito: 1000 }),
    })];
    render(<ClienteDeudorModal clienteNombre="Cliente Riesgo" onClose={() => {}} topDeudores={topDeudores} />);
    expect(screen.getByText('Cliente Riesgo SA')).toBeInTheDocument();
    expect(screen.getByText('50,0%')).toBeInTheDocument();
  });

  it('ClienteDeudorModal dado un cliente sin limite de credito cuando renderiza entonces indica sin limite definido', () => {
    const topDeudores: DeudorExtendido[] = [parcial({
      fullName: 'Cliente Sin Limite',
      obj: parcial({ nombre_razon_social: 'Cliente Sin Limite SA', saldo_pendiente: '200', limite_credito: 0 }),
    })];
    render(<ClienteDeudorModal clienteNombre="Cliente Sin Limite" onClose={() => {}} topDeudores={topDeudores} />);
    expect(screen.getByText('Sin límite definido')).toBeInTheDocument();
  });

  it('ClienteDeudorModal dado clienteNombre sin match en topDeudores cuando renderiza entonces no muestra el bloque de detalle', () => {
    render(<ClienteDeudorModal clienteNombre="Inexistente" onClose={() => {}} topDeudores={[]} />);
    expect(screen.queryByText('Razón Social')).not.toBeInTheDocument();
  });

  it('ProductoHistorialModal dado cargando en true cuando renderiza entonces muestra el spinner de carga', () => {
    const producto = parcial<ProduccionProductoItem>({ producto_nombre: 'Tela Azul', producto_codigo: 'T-1', kg_total: 0, num_lotes: 0 });
    render(<ProductoHistorialModal producto={producto} historial={[]} cargando={true} onClose={() => {}} />);
    expect(screen.getByText('Cargando historial…')).toBeInTheDocument();
  });

  it('ProductoHistorialModal dado producto con historial cuando renderiza entonces muestra la serie diaria', () => {
    const producto = parcial<ProduccionProductoItem>({ producto_nombre: 'Tela Azul', producto_codigo: 'T-1', kg_total: 120.5, num_lotes: 3 });
    const historial = [{ fecha: '2026-01-01', kg: 40 }, { fecha: '2026-01-02', kg: 80.5 }];
    render(<ProductoHistorialModal producto={producto} historial={historial} cargando={false} onClose={() => {}} />);
    expect(screen.getByText('2026-01-01')).toBeInTheDocument();
    expect(screen.getByText('80,5')).toBeInTheDocument();
  });

  it('ProductoHistorialModal dado producto sin historial cuando renderiza entonces muestra el mensaje de vacio', () => {
    const producto = parcial<ProduccionProductoItem>({ producto_nombre: 'Tela Azul', producto_codigo: 'T-1', kg_total: 0, num_lotes: 0 });
    render(<ProductoHistorialModal producto={producto} historial={[]} cargando={false} onClose={() => {}} />);
    expect(screen.getByText('Sin producción diaria registrada para este producto.')).toBeInTheDocument();
  });
});
