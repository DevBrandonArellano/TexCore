import React from 'react';
import { render, screen } from '@testing-library/react';
import { PedidosEstadoModal, VentasVendedorModal } from './DrillDownModals';

// Mock simple de pedidos para las pruebas (Caja Blanca / TDD / ISTQB)
const mockPedidos: any[] = [
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
];

describe('DrillDownModals (Pruebas ISTQB - Caja Blanca)', () => {
  it('PedidosEstadoModal filtra y muestra solo los pedidos del estado seleccionado', () => {
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

  it('VentasVendedorModal filtra y muestra solo los pedidos del vendedor seleccionado', () => {
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
});
