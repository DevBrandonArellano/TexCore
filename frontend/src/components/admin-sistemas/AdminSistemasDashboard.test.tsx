import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AdminSistemasDashboard } from './AdminSistemasDashboard';
import type { Sede, Area, User, Producto, Quimico, Bodega, OrdenProduccion, FormulaColor, Cliente, Proveedor } from '../../lib/types';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
    delete: (...args: any[]) => mockDelete(...args),
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

vi.mock('./ManageUsers', () => ({
  ManageUsers: (props: any) => (
    <div data-testid="manage-users-mock">
      <span data-testid="users-count">{props.users.length}</span>
      <span data-testid="users-loading">{String(props.loading)}</span>
      <span data-testid="users-selected-sede">{String(props.selectedSedeId)}</span>
      <button onClick={() => props.onUserCreate({ username: 'nuevo', first_name: 'Nuevo' })}>crear-usuario</button>
      <button onClick={() => props.onUserUpdate(20, { first_name: 'Editado' })}>actualizar-usuario</button>
      <button onClick={() => props.onUserDelete(20)}>eliminar-usuario</button>
    </div>
  ),
}));

vi.mock('./ManageSedes', () => ({
  ManageSedes: (props: any) => (
    <div data-testid="manage-sedes-mock">
      <span data-testid="sedes-count">{props.sedes.length}</span>
      <span data-testid="sedes-loading">{String(props.sedesLoading)}</span>
      <button onClick={() => props.onSedeCreate({ nombre: 'Sede Nueva', location: 'Loja', status: 'activo' })}>crear-sede</button>
      <button onClick={() => props.onSedeUpdate(1, { nombre: 'Sede Editada' })}>actualizar-sede</button>
      <button onClick={() => props.onSedeDelete(1)}>eliminar-sede</button>
    </div>
  ),
}));

vi.mock('./ManageAreas', () => ({
  ManageAreas: (props: any) => (
    <div data-testid="manage-areas-mock">
      <span data-testid="areas-count">{props.areas.length}</span>
      <span data-testid="areas-loading">{String(props.loading)}</span>
      <button onClick={() => props.onAreaCreate({ nombre: 'Área Nueva' })}>crear-area</button>
      <button onClick={() => props.onAreaUpdate(10, { nombre: 'Área Editada' })}>actualizar-area</button>
      <button onClick={() => props.onAreaDelete(10)}>eliminar-area</button>
    </div>
  ),
}));

vi.mock('./ManageProductos', () => ({
  ManageProductos: (props: any) => (
    <div data-testid="manage-productos-mock">
      <span data-testid="productos-count">{props.productos.length}</span>
      <button onClick={() => props.onProductCreate({ codigo: 'P1', descripcion: 'Producto 1', precio_base: '10.5' })}>crear-producto</button>
      <button onClick={() => props.onProductUpdate(70, { codigo: 'P1', descripcion: 'Producto Editado', precio_base: '15.5' })}>actualizar-producto</button>
      <button onClick={() => props.onProductDelete(70)}>eliminar-producto</button>
    </div>
  ),
}));

vi.mock('./ManageQuimicos', () => ({
  ManageQuimicos: (props: any) => (
    <div data-testid="manage-quimicos-mock">
      <span data-testid="quimicos-count">{props.quimicos.length}</span>
      <button onClick={() => props.onChemicalCreate({ codigo: 'Q1', descripcion: 'Quimico 1', precio_base: '5' })}>crear-quimico</button>
      <button onClick={() => props.onChemicalUpdate(80, { codigo: 'Q1', descripcion: 'Quimico Editado' })}>actualizar-quimico</button>
      <button onClick={() => props.onChemicalDelete(80)}>eliminar-quimico</button>
    </div>
  ),
}));

vi.mock('./ManageFormulas', () => ({
  ManageFormulas: (props: any) => (
    <div data-testid="manage-formulas-mock">
      <span data-testid="formulas-count">{props.formulas.length}</span>
      <button onClick={() => props.onFormulaCreate({ codigo: 'F1', nombre_color: 'Rojo' })}>crear-formula</button>
      <button onClick={() => props.onFormulaUpdate(50, { codigo: 'F1', nombre_color: 'Rojo Editado' })}>actualizar-formula</button>
      <button onClick={() => props.onFormulaDelete(50)}>eliminar-formula</button>
    </div>
  ),
}));

vi.mock('./ManageBodegas', () => ({
  ManageBodegas: (props: any) => (
    <div data-testid="manage-bodegas-mock">
      <span data-testid="bodegas-count">{props.bodegas.length}</span>
      <button onClick={() => props.onBodegaCreate({ nombre: 'Bodega Nueva' })}>crear-bodega</button>
      <button onClick={() => props.onBodegaUpdate(30, { nombre: 'Bodega Editada' })}>actualizar-bodega</button>
      <button onClick={() => props.onBodegaDelete(30)}>eliminar-bodega</button>
    </div>
  ),
}));

vi.mock('./ManageClientes', () => ({
  ManageClientes: (props: any) => (
    <div data-testid="manage-clientes-mock">
      <span data-testid="clientes-count">{props.clientes.length}</span>
      <button onClick={() => props.onClienteCreate({ nombre_razon_social: 'Cliente Nuevo' })}>crear-cliente</button>
      <button onClick={() => props.onClienteUpdate(90, { nombre_razon_social: 'Cliente Editado' })}>actualizar-cliente</button>
      <button onClick={() => props.onClienteDelete(90)}>eliminar-cliente</button>
    </div>
  ),
}));

vi.mock('./ManageProveedores', () => ({
  ManageProveedores: (props: any) => (
    <div data-testid="manage-proveedores-mock">
      <span data-testid="proveedores-count">{props.proveedores.length}</span>
      <button onClick={() => props.onProveedorCreate({ nombre: 'Proveedor Nuevo' })}>crear-proveedor</button>
      <button onClick={() => props.onProveedorUpdate(60, { nombre: 'Proveedor Editado' })}>actualizar-proveedor</button>
      <button onClick={() => props.onProveedorDelete(60)}>eliminar-proveedor</button>
    </div>
  ),
}));

vi.mock('./InventoryDashboard', () => ({
  InventoryDashboard: (props: any) => (
    <div data-testid="inventory-dashboard-mock">
      <span data-testid="inv-productos">{props.productos.length}</span>
      <span data-testid="inv-bodegas">{props.bodegas.length}</span>
      <span data-testid="inv-sede">{String(props.sedeId)}</span>
      <button onClick={props.onDataRefresh}>refrescar-inventario</button>
    </div>
  ),
}));

vi.mock('../shared/AuditLogViewer', () => ({
  AuditLogViewer: (props: any) => (
    <div data-testid="audit-log-mock">
      <span data-testid="audit-sede">{String(props.sedeId)}</span>
    </div>
  ),
}));

const SEDE_1: Sede = { id: 1, nombre: 'Sede Norte', location: 'Quito', status: 'activo', num_areas: 2, num_users: 3, num_bodegas: 1, num_ordenes: 1 };
const SEDE_2: Sede = { id: 2, nombre: 'Sede Sur', location: 'Cuenca', status: 'activo', num_areas: 0, num_users: 0, num_bodegas: 0, num_ordenes: 0 };
const GROUP_1 = { id: 1, name: 'admin_sistemas' };

const AREA_1: Area = { id: 10, nombre: 'Tintorería', sede: 1 };
const USER_1: User = {
  id: 20, username: 'jdoe', first_name: 'John', last_name: 'Doe', email: 'j@x.com',
  area: null, sede: 1, groups: [1], permissions: [], bodegas_asignadas: [],
};
const PRODUCTO_1: Producto = {
  id: 70, codigo: 'HP-001', descripcion: 'Hilo Poliéster', tipo: 'hilo',
  unidad_medida: 'kg', stock_minimo: 10, precio_base: 5000, sede: 1,
};
const QUIMICO_1: Quimico = {
  id: 80, codigo: 'QX-1', descripcion: 'Soda Cáustica', tipo: 'quimico',
  unidad_medida: 'kg', precio_base: 100,
};
const BODEGA_1: Bodega = { id: 30, nombre: 'Bodega Central', sede: 1 };
const ORDEN_1: OrdenProduccion = {
  id: 40, codigo: 'OP-1', producto: 70, formula_color: 50, peso_neto_requerido: 100,
  estado: 'pendiente', fecha_creacion: '2026-01-01T00:00:00', fecha_modificacion: '2026-01-01T00:00:00', sede: 1,
};
const FORMULA_1: FormulaColor = {
  id: 50, codigo: 'F1', nombre_color: 'Rojo Carmesí', tipo_sustrato: 'algodon', version: 1, estado: 'aprobada',
};
const CLIENTE_1: Cliente = {
  id: 90, ruc_cedula: '123', nombre_razon_social: 'Cliente Uno', direccion_envio: 'Calle 1',
  nivel_precio: 'normal', tiene_beneficio: false, saldo_pendiente: 0, limite_credito: 1000, sede: 1,
};
const PROVEEDOR_1: Proveedor = { id: 60, nombre: 'Proveedor Uno', sede: 1 };
const PEDIDO_1 = {
  id: 95, cliente: 90, guia_remision: 'GR-1', fecha_pedido: '2026-01-01',
  estado: 'pendiente' as const, esta_pagado: false, sede: 1,
};

// Sede sin conteos anotados por el backend (num_areas === undefined) para forzar el cálculo local (fallback) en getSedeStats
const SEDE_3: Sede = { id: 3, nombre: 'Sede Fallback', location: 'Loja', status: 'activo' } as Sede;
const AREA_3: Area = { id: 12, nombre: 'Área Fallback', sede: 3 };
const USER_3: User = {
  id: 22, username: 'fallback', first_name: 'Fall', last_name: 'Back', email: 'f@x.com',
  area: null, sede: 3, groups: [], permissions: [], bodegas_asignadas: [],
};
const BODEGA_3: Bodega = { id: 32, nombre: 'Bodega Fallback', sede: 3 };
const ORDEN_3: OrdenProduccion = {
  id: 42, codigo: 'OP-3', producto: 70, formula_color: 50, peso_neto_requerido: 50,
  estado: 'pendiente', fecha_creacion: '2026-01-01T00:00:00', fecha_modificacion: '2026-01-01T00:00:00', sede: 3,
};

const LOTE_1 = {
  id: 200, orden_produccion: 40, codigo_lote: 'LT-1', peso_neto_producido: 95,
  operario: 1, maquina: 1, maquina_nombre: 'Máquina 1', turno: 'mañana',
  hora_inicio: '08:00', hora_final: '16:00',
};

const ORDENES_MANY: OrdenProduccion[] = Array.from({ length: 25 }, (_, i) => ({
  id: 500 + i,
  codigo: `OP-M-${i + 1}`,
  producto: 70,
  formula_color: 50,
  peso_neto_requerido: 10,
  estado: 'pendiente' as const,
  fecha_creacion: '2026-01-01T00:00:00',
  fecha_modificacion: '2026-01-01T00:00:00',
  sede: 1,
}));

function mockEndpoints(overrides: Record<string, any> = {}) {
  const defaults: Record<string, any> = {
    '/sedes/': [SEDE_1, SEDE_2],
    '/groups/': [GROUP_1],
    '/users/': [],
    '/areas/': [],
    '/productos/': [],
    '/chemicals/': [],
    '/bodegas/': [],
    '/ordenes-produccion/': [],
    '/lotes-produccion/': [],
    '/formula-colors/': [],
    '/pedidos-venta/': [],
    '/clientes/': [],
    '/proveedores/': [],
  };
  const data = { ...defaults, ...overrides };
  mockGet.mockImplementation((url: string) => {
    if (url in data) return Promise.resolve({ data: data[url] });
    return Promise.resolve({ data: [] });
  });
}

function mockFullSedeData() {
  mockEndpoints({
    '/users/': [USER_1],
    '/areas/': [AREA_1],
    '/productos/': [PRODUCTO_1],
    '/chemicals/': [QUIMICO_1],
    '/bodegas/': [BODEGA_1],
    '/ordenes-produccion/': [ORDEN_1],
    '/formula-colors/': [FORMULA_1],
    '/clientes/': [CLIENTE_1],
    '/proveedores/': [PROVEEDOR_1],
    '/pedidos-venta/': [PEDIDO_1],
  });
}

const renderAt = (path = '/admin-sistemas') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <AdminSistemasDashboard />
    </MemoryRouter>,
  );

describe('AdminSistemasDashboard', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockPatch.mockReset();
    mockDelete.mockReset();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
  });

  describe('carga de datos', () => {
    it('dado que monta el componente cuando no hay sede en la url entonces solicita sedes y grupos globales', async () => {
      mockEndpoints();
      renderAt();

      await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/sedes/'));
      expect(mockGet).toHaveBeenCalledWith('/groups/');
    });

    it('dado sedes obtenidas sin sede en la url cuando termina de cargar entonces selecciona automáticamente la primera sede', async () => {
      mockFullSedeData();
      renderAt();

      await waitFor(() =>
        expect(mockGet).toHaveBeenCalledWith('/users/', { params: { sede_id: '1' } }),
      );
    });

    it('dado una sede seleccionada cuando carga entonces solicita todos los recursos de esa sede con el parámetro sede_id', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');

      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());
      const expectedParams = { params: { sede_id: '1' } };
      expect(mockGet).toHaveBeenCalledWith('/users/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/areas/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/productos/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/chemicals/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/bodegas/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/ordenes-produccion/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/lotes-produccion/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/formula-colors/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/pedidos-venta/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/clientes/', expectedParams);
      expect(mockGet).toHaveBeenCalledWith('/proveedores/', expectedParams);
    });

    it('dado respuestas en formato paginado ({results:[...]}) cuando carga entonces extrae los arreglos correctamente', async () => {
      mockEndpoints({
        '/users/': { results: [USER_1] },
        '/areas/': { results: [AREA_1] },
      });
      renderAt('/admin-sistemas?sede=1');

      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await waitFor(() => expect(screen.getByTestId('users-count')).toHaveTextContent('1'));

      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));
      expect(screen.getByTestId('areas-count')).toHaveTextContent('1');
    });

    it('dado datos aún no resueltos cuando monta entonces pasa loading en true a los hijos de gestión', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url === '/sedes/') return Promise.resolve({ data: [SEDE_1] });
        if (url === '/groups/') return Promise.resolve({ data: [] });
        return new Promise(() => {});
      });
      renderAt();

      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await waitFor(() => expect(screen.getByTestId('users-loading')).toHaveTextContent('true'));
    });

    it('dado un error al obtener los datos de la sede cuando falla la petición entonces muestra un toast de error', async () => {
      mockGet.mockImplementation((url: string) => {
        if (url === '/sedes/') return Promise.resolve({ data: [SEDE_1] });
        if (url === '/groups/') return Promise.resolve({ data: [] });
        return Promise.reject(new Error('network error'));
      });
      renderAt();

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al cargar datos de la sede'));
    });
  });

  describe('navegación entre pestañas', () => {
    it('dado que carga por defecto entonces muestra la pestaña Resumen con las estadísticas de la sede seleccionada', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');

      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());
      expect(screen.getByText('Áreas')).toBeInTheDocument();
      expect(screen.getByText('departamentos en sede').previousSibling).toHaveTextContent('2');
      expect(screen.getByText('personal registrado').previousSibling).toHaveTextContent('3');
      expect(screen.getByText('almacenamiento activo').previousSibling).toHaveTextContent('1');
    });

    it('dado clic en la pestaña Producción entonces muestra las órdenes de producción de la sede', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: 'Producción' }));

      expect(screen.getByText('OP-1')).toBeInTheDocument();
      expect(screen.getByText('Hilo Poliéster')).toBeInTheDocument();
    });

    it('dado clic en la pestaña Inventario entonces renderiza InventoryDashboard con los productos y bodegas de la sede', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: 'Inventario' }));

      expect(screen.getByTestId('inventory-dashboard-mock')).toBeInTheDocument();
      expect(screen.getByTestId('inv-productos')).toHaveTextContent('1');
      expect(screen.getByTestId('inv-bodegas')).toHaveTextContent('1');
      expect(screen.getByTestId('inv-sede')).toHaveTextContent('1');
    });

    it('dado clic en refrescar dentro de InventoryDashboard entonces vuelve a pedir los datos de la sede', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());
      await userEvent.click(screen.getByRole('tab', { name: 'Inventario' }));

      mockGet.mockClear();
      await userEvent.click(screen.getByText('refrescar-inventario'));

      await waitFor(() => expect(mockGet).toHaveBeenCalledWith('/productos/', { params: { sede_id: '1' } }));
    });

    it('dado clic en la pestaña Gestión entonces muestra la subpestaña de Usuarios por defecto', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: 'Gestión' }));

      expect(screen.getByTestId('manage-users-mock')).toBeInTheDocument();
      expect(screen.getByTestId('users-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Sedes cuando está en Gestión entonces muestra ManageSedes con la lista completa de sedes', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      expect(screen.getByTestId('manage-sedes-mock')).toBeInTheDocument();
      expect(screen.getByTestId('sedes-count')).toHaveTextContent('2');
    });

    it('dado clic en la subpestaña Áreas cuando está en Gestión entonces muestra ManageAreas filtrada por la sede', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      expect(screen.getByTestId('manage-areas-mock')).toBeInTheDocument();
      expect(screen.getByTestId('areas-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Productos cuando está en Gestión entonces muestra ManageProductos', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      expect(screen.getByTestId('manage-productos-mock')).toBeInTheDocument();
      expect(screen.getByTestId('productos-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Químicos cuando está en Gestión entonces muestra ManageQuimicos', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      expect(screen.getByTestId('manage-quimicos-mock')).toBeInTheDocument();
      expect(screen.getByTestId('quimicos-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Fórmulas cuando está en Gestión entonces muestra ManageFormulas', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      expect(screen.getByTestId('manage-formulas-mock')).toBeInTheDocument();
      expect(screen.getByTestId('formulas-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Bodegas cuando está en Gestión entonces muestra ManageBodegas', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      expect(screen.getByTestId('manage-bodegas-mock')).toBeInTheDocument();
      expect(screen.getByTestId('bodegas-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Clientes cuando está en Gestión entonces muestra ManageClientes', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      expect(screen.getByTestId('manage-clientes-mock')).toBeInTheDocument();
      expect(screen.getByTestId('clientes-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Proveedores cuando está en Gestión entonces muestra ManageProveedores', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      expect(screen.getByTestId('manage-proveedores-mock')).toBeInTheDocument();
      expect(screen.getByTestId('proveedores-count')).toHaveTextContent('1');
    });

    it('dado clic en la subpestaña Roles cuando está en Gestión entonces muestra los grupos con su conteo de usuarios', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: 'Roles' }));

      expect(screen.getByText('ADMIN SISTEMAS')).toBeInTheDocument();
      expect(screen.getByText('1 Usuarios')).toBeInTheDocument();
    });

    it('dado clic en la pestaña Auditoría entonces muestra AuditLogViewer con la sede seleccionada', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('tab', { name: 'Auditoría' }));

      expect(screen.getByTestId('audit-log-mock')).toBeInTheDocument();
      expect(screen.getByTestId('audit-sede')).toHaveTextContent('1');
    });

    it('dado clic en una sede distinta en el sidebar entonces actualiza la sede seleccionada y solicita sus datos', async () => {
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await waitFor(() => expect(screen.getByText('Gestión de Sede Norte')).toBeInTheDocument());
      mockGet.mockClear();

      await userEvent.click(screen.getByText('Sede Sur'));

      await waitFor(() => expect(screen.getByText('Gestión de Sede Sur')).toBeInTheDocument());
      expect(mockGet).toHaveBeenCalledWith('/users/', { params: { sede_id: '2' } });
    });
  });

  describe('creación, actualización y eliminación de recursos', () => {
    it('dado clic en crear sede cuando la petición tiene éxito entonces hace POST a /sedes/ y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { id: 3, nombre: 'Sede Nueva', location: 'Loja', status: 'activo' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('crear-sede'));

      await waitFor(() => expect(mockPost).toHaveBeenCalledWith('/sedes/', expect.objectContaining({ nombre: 'Sede Nueva' })));
      expect(toastSuccessMock).toHaveBeenCalledWith('Sede creada exitosamente');
    });

    it('dado clic en crear sede cuando la petición falla con un error de validación 400 entonces muestra un toast con el detalle', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce({ response: { status: 400, data: { nombre: ['Ya existe una sede con ese nombre'] } } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('crear-sede'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Error de validación', {
          description: 'nombre: Ya existe una sede con ese nombre',
        }),
      );
    });

    it('dado clic en actualizar sede cuando la petición tiene éxito entonces hace PATCH a /sedes/:id/ y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...SEDE_1, nombre: 'Sede Editada' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('actualizar-sede'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/sedes/1/', { nombre: 'Sede Editada' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Sede actualizada exitosamente');
    });

    it('dado clic en eliminar sede cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('eliminar-sede'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/sedes/1/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Sede eliminada exitosamente');
    });

    it('dado clic en eliminar sede cuando el usuario cancela entonces no elimina nada', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('eliminar-sede'));

      await waitFor(() => expect(mockDelete).not.toHaveBeenCalled());
    });

    it('dado clic en crear área cuando hay una sede seleccionada entonces envía el id de sede en el payload', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { id: 11, nombre: 'Área Nueva', sede: 1 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('crear-area'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/areas/', { nombre: 'Área Nueva', sede: 1 }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Área creada exitosamente');
    });

    it('dado clic en actualizar área cuando la petición tiene éxito entonces hace PATCH y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...AREA_1, nombre: 'Área Editada' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('actualizar-area'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/areas/10/', { nombre: 'Área Editada' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Área actualizada exitosamente');
    });

    it('dado clic en eliminar área cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('eliminar-area'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/areas/10/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Área eliminada exitosamente');
    });

    it('dado clic en crear usuario cuando hay una sede seleccionada entonces envía el id de sede en el payload y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...USER_1, id: 21, username: 'nuevo' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('crear-usuario'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/users/', { username: 'nuevo', first_name: 'Nuevo', sede: 1 }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Usuario creado exitosamente');
    });

    it('dado clic en actualizar usuario cuando la petición tiene éxito entonces hace PATCH a /users/:id/', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...USER_1, first_name: 'Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('actualizar-usuario'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/users/20/', { first_name: 'Editado' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Usuario actualizado exitosamente');
    });

    it('dado clic en eliminar usuario cuando el usuario confirma entonces hace DELETE a /users/:id/', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('eliminar-usuario'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/users/20/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Usuario eliminado exitosamente');
    });

    it('dado clic en eliminar usuario cuando el usuario cancela entonces no elimina nada', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      mockFullSedeData();
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('eliminar-usuario'));

      await waitFor(() => expect(mockDelete).not.toHaveBeenCalled());
    });

    it('dado clic en crear fórmula cuando no hay guardia de sede entonces se crea igualmente enviando el sede actual', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...FORMULA_1, id: 51 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('crear-formula'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/formula-colors/', { codigo: 'F1', nombre_color: 'Rojo', sede: 1 }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Fórmula creada exitosamente');
    });

    it('dado clic en eliminar fórmula cuando la petición tiene éxito entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('eliminar-formula'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/formula-colors/50/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Fórmula eliminada exitosamente');
    });

    it('dado clic en crear químico entonces arma el payload con los valores por defecto del backend', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...QUIMICO_1, id: 81 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('crear-quimico'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/chemicals/', {
          codigo: 'Q1',
          descripcion: 'Quimico 1',
          tipo: 'quimico',
          unidad_medida: 'kg',
          stock_minimo: 0,
          precio_base: 5,
          presentacion: null,
          sede: 1,
        }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Químico creado exitosamente');
    });

    it('dado clic en crear producto entonces arma el payload con los valores por defecto del backend', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...PRODUCTO_1, id: 71 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('crear-producto'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/productos/', {
          codigo: 'P1',
          descripcion: 'Producto 1',
          tipo: 'hilo',
          unidad_medida: 'kg',
          stock_minimo: 0,
          precio_base: 10.5,
          presentacion: null,
          pais_origen: null,
          calidad: null,
          sede: 1,
        }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Producto creado exitosamente');
    });

    it('dado clic en crear proveedor entonces envía únicamente nombre y sede en el payload', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...PROVEEDOR_1, id: 61 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('crear-proveedor'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/proveedores/', { nombre: 'Proveedor Nuevo', sede: 1 }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Proveedor creado exitosamente');
    });

    it('dado clic en eliminar proveedor cuando la petición tiene éxito entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('eliminar-proveedor'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/proveedores/60/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Proveedor eliminado exitosamente');
    });
  });

  describe('manejo de errores en operaciones CRUD', () => {
    it('dado un error 403 al crear un área entonces muestra un toast indicando falta de permisos', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce({ response: { status: 403 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('crear-area'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('No tienes permiso para crear el área'));
    });

    it('dado un error 401 al eliminar un usuario entonces muestra un toast de sesión expirada', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce({ response: { status: 401 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('eliminar-usuario'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Sesión expirada. Inicia sesión de nuevo.'));
    });

    it('dado un error genérico con detalle al actualizar una bodega entonces muestra el mensaje de detalle del backend', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Error interno del servidor' } } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('actualizar-bodega'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error interno del servidor'));
    });

    it('dado que no hay sedes disponibles cuando se intenta crear un cliente sin sede seleccionada entonces igual permite crear enviando sede en null', async () => {
      mockEndpoints({ '/sedes/': [], '/groups/': [] });
      mockPost.mockResolvedValueOnce({ data: { ...CLIENTE_1, id: 91, sede: null } });
      renderAt('/admin-sistemas');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('crear-cliente'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/clientes/', { nombre_razon_social: 'Cliente Nuevo', sede: null }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Cliente creado exitosamente');
    });
  });

  describe('guardas de creación cuando hay sedes pero ninguna está seleccionada', () => {
    async function crearSedeSinSeleccionarla() {
      mockEndpoints({ '/sedes/': [], '/groups/': [] });
      mockPost.mockResolvedValueOnce({ data: { id: 5, nombre: 'Sede Nueva', location: 'Loja', status: 'activo' } });
      renderAt('/admin-sistemas');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));
      await userEvent.click(screen.getByText('crear-sede'));
      await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith('Sede creada exitosamente'));
    }

    it('dado una sede creada pero no seleccionada cuando se crea un área entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('crear-area'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un área'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/areas/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea un usuario entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: 'Usuarios' }));

      await userEvent.click(screen.getByText('crear-usuario'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un usuario'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/users/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea un cliente entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('crear-cliente'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un cliente'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/clientes/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea una bodega entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('crear-bodega'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear una bodega'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/bodegas/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea un químico entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('crear-quimico'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un químico'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/chemicals/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea un producto entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('crear-producto'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un producto'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/productos/', expect.anything());
    });

    it('dado una sede creada pero no seleccionada cuando se crea un proveedor entonces muestra un toast pidiendo seleccionar sede', async () => {
      await crearSedeSinSeleccionarla();
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('crear-proveedor'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('Selecciona una sede en el menú lateral antes de crear un proveedor'),
      );
      expect(mockPost).not.toHaveBeenCalledWith('/proveedores/', expect.anything());
    });

    it('dado que no hay ninguna sede en el sistema cuando se crea un área entonces muestra un toast distinto indicando que no hay sedes', async () => {
      mockEndpoints({ '/sedes/': [], '/groups/': [] });
      renderAt('/admin-sistemas');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('crear-area'));

      await waitFor(() =>
        expect(toastErrorMock).toHaveBeenCalledWith('No hay sedes disponibles. Crea o selecciona una sede primero.'),
      );
    });
  });

  describe('rutas de error (catch) no cubiertas de las operaciones CRUD', () => {
    it('dado un error al actualizar una sede entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('actualizar-sede'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar la sede'));
    });

    it('dado un error al eliminar una sede entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await userEvent.click(screen.getByText('eliminar-sede'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar la sede'));
    });

    it('dado un error al actualizar un área entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('actualizar-area'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el área'));
    });

    it('dado un error al eliminar un área entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Áreas/ }));

      await userEvent.click(screen.getByText('eliminar-area'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el área'));
    });

    it('dado un error al crear un usuario entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('crear-usuario'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear el usuario'));
    });

    it('dado un error al actualizar un usuario entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('actualizar-usuario'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el usuario'));
    });

    it('dado un error al eliminar un usuario entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByText('eliminar-usuario'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el usuario'));
    });

    it('dado un error al crear un cliente entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('crear-cliente'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear el cliente'));
    });

    it('dado clic en actualizar cliente cuando la petición tiene éxito entonces hace PATCH y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...CLIENTE_1, nombre_razon_social: 'Cliente Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('actualizar-cliente'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/clientes/90/', { nombre_razon_social: 'Cliente Editado' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Cliente actualizado exitosamente');
    });

    it('dado un error al actualizar un cliente entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('actualizar-cliente'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el cliente'));
    });

    it('dado clic en eliminar cliente cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('eliminar-cliente'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/clientes/90/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Cliente eliminado exitosamente');
    });

    it('dado un error al eliminar un cliente entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Clientes/ }));

      await userEvent.click(screen.getByText('eliminar-cliente'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el cliente'));
    });

    it('dado clic en crear bodega cuando hay una sede seleccionada entonces envía el id de sede en el payload', async () => {
      mockFullSedeData();
      mockPost.mockResolvedValueOnce({ data: { ...BODEGA_1, id: 31 } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('crear-bodega'));

      await waitFor(() =>
        expect(mockPost).toHaveBeenCalledWith('/bodegas/', { nombre: 'Bodega Nueva', sede: 1 }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Bodega creada exitosamente');
    });

    it('dado un error al crear una bodega entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('crear-bodega'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear la bodega'));
    });

    it('dado clic en actualizar bodega cuando la petición tiene éxito entonces hace PATCH y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...BODEGA_1, nombre: 'Bodega Editada' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('actualizar-bodega'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/bodegas/30/', { nombre: 'Bodega Editada' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Bodega actualizada exitosamente');
    });

    it('dado clic en eliminar bodega cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('eliminar-bodega'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/bodegas/30/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Bodega eliminada exitosamente');
    });

    it('dado un error al eliminar una bodega entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Bodegas/ }));

      await userEvent.click(screen.getByText('eliminar-bodega'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar la bodega'));
    });

    it('dado un error al crear una fórmula entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('crear-formula'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear la fórmula'));
    });

    it('dado clic en actualizar fórmula cuando la petición tiene éxito entonces hace PATCH y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...FORMULA_1, nombre_color: 'Rojo Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('actualizar-formula'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/formula-colors/50/', { codigo: 'F1', nombre_color: 'Rojo Editado' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Fórmula actualizada exitosamente');
    });

    it('dado un error al actualizar una fórmula entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('actualizar-formula'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar la fórmula'));
    });

    it('dado un error al eliminar una fórmula entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Fórmulas/ }));

      await userEvent.click(screen.getByText('eliminar-formula'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar la fórmula'));
    });

    it('dado un error al crear un químico entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('crear-quimico'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear el químico'));
    });

    it('dado clic en actualizar químico cuando la petición tiene éxito entonces hace PATCH con los valores por defecto del backend', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...QUIMICO_1, descripcion: 'Quimico Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('actualizar-quimico'));

      await waitFor(() =>
        expect(mockPatch).toHaveBeenCalledWith('/chemicals/80/', {
          codigo: 'Q1',
          descripcion: 'Quimico Editado',
          tipo: 'quimico',
          unidad_medida: 'kg',
          presentacion: null,
          precio_base: 0,
        }),
      );
      expect(toastSuccessMock).toHaveBeenCalledWith('Químico actualizado exitosamente');
    });

    it('dado un error al actualizar un químico entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('actualizar-quimico'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el químico'));
    });

    it('dado clic en eliminar químico cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('eliminar-quimico'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/chemicals/80/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Químico eliminado exitosamente');
    });

    it('dado un error al eliminar un químico entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      await userEvent.click(screen.getByText('eliminar-quimico'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el químico'));
    });

    it('dado un error al crear un producto entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('crear-producto'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear el producto'));
    });

    it('dado clic en actualizar producto cuando la petición tiene éxito entonces hace PATCH incluyendo precio_base cuando es numérico', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...PRODUCTO_1, descripcion: 'Producto Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('actualizar-producto'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/productos/70/', expect.objectContaining({
        codigo: 'P1',
        descripcion: 'Producto Editado',
      })));
      expect(toastSuccessMock).toHaveBeenCalledWith('Producto actualizado exitosamente');
    });

    it('dado un error al actualizar un producto entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('actualizar-producto'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el producto'));
    });

    it('dado clic en eliminar producto cuando el usuario confirma entonces hace DELETE y muestra un toast de éxito', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockResolvedValueOnce({ data: {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('eliminar-producto'));

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('/productos/70/'));
      expect(toastSuccessMock).toHaveBeenCalledWith('Producto eliminado exitosamente');
    });

    it('dado un error al eliminar un producto entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Productos/ }));

      await userEvent.click(screen.getByText('eliminar-producto'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el producto'));
    });

    it('dado un error al crear un proveedor entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPost.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('crear-proveedor'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear el proveedor'));
    });

    it('dado clic en actualizar proveedor cuando la petición tiene éxito entonces hace PATCH y muestra un toast de éxito', async () => {
      mockFullSedeData();
      mockPatch.mockResolvedValueOnce({ data: { ...PROVEEDOR_1, nombre: 'Proveedor Editado' } });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('actualizar-proveedor'));

      await waitFor(() => expect(mockPatch).toHaveBeenCalledWith('/proveedores/60/', { nombre: 'Proveedor Editado' }));
      expect(toastSuccessMock).toHaveBeenCalledWith('Proveedor actualizado exitosamente');
    });

    it('dado un error al actualizar un proveedor entonces muestra el toast de error genérico', async () => {
      mockFullSedeData();
      mockPatch.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('actualizar-proveedor'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al actualizar el proveedor'));
    });

    it('dado un error al eliminar un proveedor entonces muestra el toast de error genérico', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockFullSedeData();
      mockDelete.mockRejectedValueOnce(new Error('boom'));
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Proveedores/ }));

      await userEvent.click(screen.getByText('eliminar-proveedor'));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al eliminar el proveedor'));
    });
  });

  describe('rutas restantes de carga de datos y cálculo de estadísticas', () => {
    it('dado un error al obtener sedes/grupos globales entonces registra el error en consola y de todas formas marca la carga de sedes como finalizada', async () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mockGet.mockImplementation((url: string) => {
        if (url === '/sedes/') return Promise.reject(new Error('network down'));
        if (url === '/groups/') return Promise.resolve({ data: [] });
        return Promise.resolve({ data: [] });
      });
      renderAt();
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));
      await userEvent.click(screen.getByRole('tab', { name: /Sedes/ }));

      await waitFor(() => expect(screen.getByTestId('sedes-loading')).toHaveTextContent('false'));
      expect(consoleErrorSpy).toHaveBeenCalledWith('Error fetching global data:', expect.any(Error));
      consoleErrorSpy.mockRestore();
    });

    it('dado que no hay ninguna sede seleccionada cuando se refresca el inventario entonces no vuelve a solicitar los datos de la sede', async () => {
      mockEndpoints({ '/sedes/': [], '/groups/': [] });
      renderAt('/admin-sistemas');
      await userEvent.click(await screen.findByRole('tab', { name: 'Inventario' }));
      mockGet.mockClear();

      await userEvent.click(screen.getByText('refrescar-inventario'));

      await waitFor(() => expect(mockGet).not.toHaveBeenCalledWith('/users/', expect.anything()));
    });

    it('dado que un recurso responde con un objeto sin campo results ni arreglo entonces getData devuelve un arreglo vacío', async () => {
      mockEndpoints({ '/chemicals/': {} });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Gestión' }));

      await userEvent.click(screen.getByRole('tab', { name: /Químicos/ }));

      expect(screen.getByTestId('quimicos-count')).toHaveTextContent('0');
    });

    it('dado una sede sin conteos anotados por el backend entonces calcula las estadísticas a partir de los arreglos locales', async () => {
      mockEndpoints({
        '/sedes/': [SEDE_3],
        '/areas/': [AREA_3],
        '/users/': [USER_3],
        '/bodegas/': [BODEGA_3],
        '/ordenes-produccion/': [ORDEN_3],
      });
      renderAt('/admin-sistemas?sede=3');

      await waitFor(() => expect(screen.getByText('Gestión de Sede Fallback')).toBeInTheDocument());
      const sedeCard = screen.getByText('Sede Fallback').closest('button')!;
      expect(within(sedeCard).getByText('Áreas:').nextSibling).toHaveTextContent('1');
      expect(within(sedeCard).getByText('Users:').nextSibling).toHaveTextContent('1');
      expect(within(sedeCard).getByText('Bodegas:').nextSibling).toHaveTextContent('1');
      expect(within(sedeCard).getByText('Órdenes:').nextSibling).toHaveTextContent('1');
    });
  });

  describe('paginación de órdenes de producción y lotes producidos', () => {
    it('dado más de 20 órdenes de producción cuando se hace clic en Siguiente entonces avanza a la página 2', async () => {
      mockEndpoints({ '/ordenes-produccion/': ORDENES_MANY });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Producción' }));
      await screen.findByText('OP-M-1');

      await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
      expect(screen.getByText('OP-M-21')).toBeInTheDocument();
    });

    it('dado estar en la página 2 cuando se hace clic en Anterior entonces regresa a la página 1', async () => {
      mockEndpoints({ '/ordenes-produccion/': ORDENES_MANY });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Producción' }));
      await screen.findByText('OP-M-1');
      await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));
      await screen.findByText('OP-M-21');

      await userEvent.click(screen.getByRole('button', { name: /Anterior/ }));

      expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
      expect(screen.getByText('OP-M-1')).toBeInTheDocument();
    });

    it('dado escribir un número de página y presionar Enter entonces navega directamente a esa página', async () => {
      mockEndpoints({ '/ordenes-produccion/': ORDENES_MANY });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Producción' }));
      await screen.findByText('OP-M-1');
      const input = screen.getByRole('spinbutton');

      await userEvent.clear(input);
      await userEvent.type(input, '2{Enter}');

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    });

    it('dado escribir un número de página y quitar el foco (blur) entonces navega directamente a esa página', async () => {
      mockEndpoints({ '/ordenes-produccion/': ORDENES_MANY });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Producción' }));
      await screen.findByText('OP-M-1');
      const input = screen.getByRole('spinbutton');

      await userEvent.clear(input);
      await userEvent.type(input, '2');
      await userEvent.tab();

      expect(screen.getByText('Página 2 de 2')).toBeInTheDocument();
    });

    it('dado lotes de producción disponibles cuando se muestra la pestaña Producción entonces lista los lotes producidos', async () => {
      mockEndpoints({ '/lotes-produccion/': [LOTE_1] });
      renderAt('/admin-sistemas?sede=1');
      await userEvent.click(await screen.findByRole('tab', { name: 'Producción' }));

      expect(await screen.findByText('LT-1')).toBeInTheDocument();
      expect(screen.getByText('95 Kg')).toBeInTheDocument();
      expect(screen.getByText(/1 - Turno mañana/)).toBeInTheDocument();
    });
  });
});
