import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

import { AuditLogViewer } from './AuditLogViewer';

const mockGet = vi.fn();

vi.mock('../../lib/axios', () => ({
  default: {
    get: (...args: any[]) => mockGet(...args),
  },
}));

const LOG_CREATE = {
  id: 1,
  fecha_hora: '2026-07-10T15:30:00Z',
  usuario_nombre: 'Ana López',
  ip_address: '192.168.1.10',
  accion: 'CREATE',
  tabla_afectada: 'Producto',
  registro_id: 55,
  valor_anterior: null,
  valor_nuevo: { nombre: 'Tela X' },
  justificacion: 'Alta inicial',
};

const LOG_UPDATE = {
  id: 2,
  fecha_hora: '2026-07-11T08:00:00Z',
  usuario_nombre: 'Carlos Ruiz',
  ip_address: '10.0.0.5',
  accion: 'UPDATE',
  tabla_afectada: 'Inventario',
  registro_id: 12,
  valor_anterior: { cantidad: 10 },
  valor_nuevo: { cantidad: 25 },
  justificacion: 'Ajuste de stock',
};

const LOG_DELETE = {
  id: 3,
  fecha_hora: '2026-07-12T10:15:00Z',
  usuario_nombre: 'Beatriz Gómez',
  ip_address: '172.16.0.2',
  accion: 'DELETE',
  tabla_afectada: 'Cliente',
  registro_id: 9,
  valor_anterior: { nombre: 'Cliente Baja' },
  valor_nuevo: null,
  justificacion: 'Cliente inactivo',
};

function mockFetch(results: any[], count = results.length) {
  mockGet.mockResolvedValue({ data: { results, count } });
}

describe('AuditLogViewer', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('dado que la peticion esta en curso entonces muestra el estado de carga', async () => {
    let resolveRequest: (value: any) => void = () => {};
    mockGet.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );

    render(<AuditLogViewer />);

    expect(screen.getByText('Cargando registros...')).toBeInTheDocument();

    resolveRequest({ data: { results: [], count: 0 } });
    await waitFor(() =>
      expect(screen.getByText('No se encontraron registros de auditoría.')).toBeInTheDocument(),
    );
  });

  it('dado sin registros cuando carga entonces muestra el mensaje de vacio', async () => {
    mockFetch([], 0);
    render(<AuditLogViewer />);

    await waitFor(() =>
      expect(screen.getByText('No se encontraron registros de auditoría.')).toBeInTheDocument(),
    );
  });

  it('dado registros existentes cuando carga entonces muestra usuario, ip, accion, objeto y justificacion', async () => {
    mockFetch([LOG_UPDATE]);
    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText('Carlos Ruiz')).toBeInTheDocument());
    expect(screen.getByText('IP: 10.0.0.5')).toBeInTheDocument();
    expect(screen.getByText('EDITAR')).toBeInTheDocument();
    expect(screen.getByText(/Inventario/)).toBeInTheDocument();
    expect(screen.getByText(/#12/)).toBeInTheDocument();
    expect(screen.getByText('Ajuste de stock')).toBeInTheDocument();

    const expectedFecha = format(new Date(LOG_UPDATE.fecha_hora), 'dd MMM, HH:mm:ss', { locale: es });
    expect(screen.getByText(expectedFecha)).toBeInTheDocument();
  });

  it('dado un registro de creacion entonces muestra solo el valor nuevo como registro inicial', async () => {
    mockFetch([LOG_CREATE]);
    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText('CREAR')).toBeInTheDocument());
    expect(screen.getByText(/Registro inicial:/)).toBeInTheDocument();
    expect(screen.getByText(/Tela X/)).toBeInTheDocument();
    expect(screen.queryByText(/Anterior:/)).not.toBeInTheDocument();
  });

  it('dado un registro de edicion entonces muestra el valor anterior y el nuevo', async () => {
    mockFetch([LOG_UPDATE]);
    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText(/Anterior:/)).toBeInTheDocument());
    expect(screen.getByText(/Nuevo:/)).toBeInTheDocument();
    expect(screen.getByText(/"cantidad": 10/)).toBeInTheDocument();
    expect(screen.getByText(/"cantidad": 25/)).toBeInTheDocument();
  });

  it('dado un registro de eliminacion entonces muestra los valores eliminados', async () => {
    mockFetch([LOG_DELETE]);
    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText('ELIMINAR')).toBeInTheDocument());
    expect(screen.getByText(/Valores eliminados:/)).toBeInTheDocument();
    expect(screen.getByText(/Cliente Baja/)).toBeInTheDocument();
  });

  it('dado que el usuario escribe una busqueda cuando la envia entonces consulta con el termino y reinicia la pagina', async () => {
    mockFetch([]);
    render(<AuditLogViewer />);

    await waitFor(() =>
      expect(screen.getByText('No se encontraron registros de auditoría.')).toBeInTheDocument(),
    );
    mockGet.mockClear();

    await userEvent.type(screen.getByPlaceholderText('Buscar por usuario, tabla o ID...'), 'Ana');
    await userEvent.click(screen.getByRole('button', { name: 'Buscar' }));

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('search=Ana')),
    );
    expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('page=1'));
  });

  it('dado varias paginas de registros cuando hace clic en Siguiente entonces consulta la pagina siguiente', async () => {
    mockFetch([LOG_UPDATE], 45);
    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText('Página 1 de 3 (45 registros)')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Anterior/ })).toBeDisabled();

    mockGet.mockClear();
    await userEvent.click(screen.getByRole('button', { name: /Siguiente/ }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('page=2')));
    await waitFor(() => expect(screen.getByText('Página 2 de 3 (45 registros)')).toBeInTheDocument());
  });

  it('dado sedeId y permitirVerTodasSedes cuando marca ver todas las sedes entonces consulta sin filtrar por sede', async () => {
    mockFetch([LOG_UPDATE], 1);
    render(<AuditLogViewer sedeId="3" />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('sede_id=3')));
    mockGet.mockClear();

    await userEvent.click(screen.getByRole('checkbox', { name: /Ver todas las sedes/ }));

    await waitFor(() => {
      const lastCallUrl = mockGet.mock.calls.at(-1)?.[0] as string;
      expect(lastCallUrl).not.toContain('sede_id');
    });
  });

  it('dado permitirVerTodasSedes en false entonces no muestra la opcion de ver todas las sedes', async () => {
    mockFetch([], 0);
    render(<AuditLogViewer sedeId="3" permitirVerTodasSedes={false} />);

    await waitFor(() =>
      expect(screen.getByText('No se encontraron registros de auditoría.')).toBeInTheDocument(),
    );
    expect(screen.queryByText('Ver todas las sedes')).not.toBeInTheDocument();
  });

  it('dado clic en Refrescar entonces vuelve a consultar los registros', async () => {
    mockFetch([], 0);
    render(<AuditLogViewer />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getByRole('button', { name: /Refrescar/ }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2));
  });

  it('dado un error en la peticion entonces deja de cargar y muestra el mensaje de vacio', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGet.mockRejectedValue(new Error('network error'));

    render(<AuditLogViewer />);

    await waitFor(() =>
      expect(screen.getByText('No se encontraron registros de auditoría.')).toBeInTheDocument(),
    );
    expect(consoleErrorSpy).toHaveBeenCalledWith('Error fetching audit logs:', expect.any(Error));

    consoleErrorSpy.mockRestore();
  });

  it('dado un registro disperso sin usuario, ip, fecha, accion, tabla ni justificacion cuando renderiza entonces usa todos los valores por defecto', async () => {
    const LOG_DISPERSO: any = { id: 9 };
    mockFetch([LOG_DISPERSO]);

    render(<AuditLogViewer />);

    await waitFor(() => expect(screen.getByText('Sistema')).toBeInTheDocument());
    expect(screen.getByText('IP: Local')).toBeInTheDocument();
    expect(screen.getByText('EDITAR')).toBeInTheDocument(); // accion por defecto 'UPDATE'
    expect(screen.getByText(/N\/A #-/)).toBeInTheDocument();
    expect(screen.getAllByText('-').length).toBeGreaterThan(0); // fecha y justificacion
  });

  it('dado un registro con objeto_id en vez de registro_id cuando renderiza entonces usa object_id', async () => {
    const LOG_OBJECT_ID: any = { id: 10, tabla_afectada: 'Pedido', object_id: 42, accion: 'UPDATE' };
    mockFetch([LOG_OBJECT_ID]);

    render(<AuditLogViewer />);
    await waitFor(() => expect(screen.getByText(/Pedido #42/)).toBeInTheDocument());
  });

  it('dado accion desconocida cuando renderiza el badge entonces muestra la accion tal cual', async () => {
    const LOG_ACCION_RARA: any = { id: 11, accion: 'RESTORE', tabla_afectada: 'X', registro_id: 1 };
    mockFetch([LOG_ACCION_RARA]);

    render(<AuditLogViewer />);
    await waitFor(() => expect(screen.getByText('RESTORE')).toBeInTheDocument());
  });
});
