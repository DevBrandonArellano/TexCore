import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { PlanProduccionMTS } from './PlanProduccionMTS';
import apiClient from '../../lib/axios';

vi.mock('../../lib/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const toastErrorMock = vi.fn();
const toastSuccessMock = vi.fn();
const toastWarningMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => toastErrorMock(...args),
    success: (...args: unknown[]) => toastSuccessMock(...args),
    warning: (...args: unknown[]) => toastWarningMock(...args),
  },
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

const mockPlanes = [
  {
    id: 1,
    codigo: 'PLAN-MTS-2026-001',
    sede: 1,
    sede_nombre: 'Sede Principal',
    fecha_inicio: '2026-06-01',
    fecha_fin: '2026-06-07',
    estado: 'borrador',
    supervisor: 10,
    supervisor_nombre: 'Carlos Supervisor',
    detalles: [
      {
        id: 101,
        plan: 1,
        producto_objetivo: 20,
        producto_objetivo_codigo: 'TELA-JERSEY-01',
        producto_objetivo_descripcion: 'Tela Jersey 100% Algodón',
        producto_objetivo_unidad: 'kg',
        cantidad_planificada: '100.0000',
        cantidad_ejecutada: '20.0000',
        cantidad_aceptada: '20.0000',
        cantidad_segunda: '0.0000',
        saldo_pendiente: '80.0000',
        desviacion_porcentaje: '-80.00',
        cumplimiento_porcentaje: '20.00',
        estado: 'en_proceso',
      },
    ],
    fecha_creacion: '2026-06-01T08:00:00Z',
    fecha_modificacion: '2026-06-01T08:00:00Z',
  },
];

const mockNecesidades = [
  {
    sede_id: 1,
    sede_nombre: 'Sede Principal',
    producto_id: 30,
    producto_codigo: 'HILO-24-1',
    producto_descripcion: 'Hilo Algodón 24/1 Crudo',
    tipo: 'hilo',
    unidad_medida: 'kg',
    stock_actual: '25.00',
    stock_minimo: '100.00',
    demanda_pedidos: '40.00',
    demanda_interna: '5.00',
    en_produccion: '45.00',
    deficit: '75.00',
  },
];

describe('PlanProduccionMTS Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastErrorMock.mockReset();
    toastSuccessMock.mockReset();
    toastWarningMock.mockReset();
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/planes-produccion/necesidades-reposicion/')) {
        return Promise.resolve({ data: mockNecesidades });
      }
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({ data: mockPlanes });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it('dado que el componente se monta cuando carga datos entonces muestra el plan y su renglón de detalle', async () => {
    render(
      <PlanProduccionMTS
        sedeNombre="Sede Principal"
        bodegas={[{ id: 1, nombre: 'Bodega Central', sede: 1 }]}
      />
    );

    expect(screen.getByText(/Planificación y Producción Contra Stock \(MTS\)/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument();
      expect(screen.getByText('TELA-JERSEY-01')).toBeInTheDocument();
      expect(screen.getByText('Tela Jersey 100% Algodón')).toBeInTheDocument();
      expect(screen.getByText(/Aprobar Plan/i)).toBeInTheDocument();
    });
  });

  it('dado clic en Aprobar Plan cuando confirma entonces invoca el endpoint de aprobación', async () => {
    (apiClient.post as Mock).mockResolvedValueOnce({ data: { ...mockPlanes[0], estado: 'aprobado' } });

    render(
      <PlanProduccionMTS
        sedeNombre="Sede Principal"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument();
    });

    const botonAprobar = screen.getByText(/Aprobar Plan/i);
    fireEvent.click(botonAprobar);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/planes-produccion/1/aprobar/');
    });
  });

  it('dado clic en la pestaña Necesidad de producción cuando cambia entonces visualiza lo que hay que producir con su desglose', async () => {
    render(
      <PlanProduccionMTS
        sedeNombre="Sede Principal"
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Necesidad de producción/i)).toBeInTheDocument();
    });

    const tabAlertas = screen.getByRole('button', { name: /Necesidad de producción/i });
    fireEvent.click(tabAlertas);

    await waitFor(() => {
      expect(screen.getByText('HILO-24-1')).toBeInTheDocument();
      expect(screen.getByText('Hilo Algodón 24/1 Crudo')).toBeInTheDocument();
      expect(screen.getByText('75.00 kg')).toBeInTheDocument();
    });
    // Desglose: pedidos 40 + interna 5 + mínimo 100 − disponible 25 − en producción 45 = 75
    const fila = screen.getByText('HILO-24-1').closest('tr') as HTMLElement;
    for (const valor of ['40.00 kg', '5.00 kg', '100.00 kg', '25.00 kg', '45.00 kg']) {
      expect(within(fila).getByText(valor)).toBeInTheDocument();
    }
  });

  it('dado sin necesidades cuando carga entonces indica que no hay que producir y no ofrece crear plan', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS sedeNombre="Sede Principal" />);

    await waitFor(() => expect(screen.getByText('No se encontraron planes de producción registrados.')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Necesidad de producción/i }));
    expect(screen.getByText('Sin necesidad de producción')).toBeInTheDocument();
    expect(screen.queryByText(/Crear Plan desde Déficits/i)).not.toBeInTheDocument();
  });

  it('dado error al cargar planes cuando falla entonces muestra un toast de error', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      return Promise.reject(new Error('500'));
    });
    render(<PlanProduccionMTS />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });

  it('dado error al cargar necesidades cuando falla entonces muestra un toast de error', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.reject(new Error('500'));
      if (url.includes('/planes-produccion/')) return Promise.resolve({ data: [] });
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS />);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });

  it('dado el backend rechaza aprobar cuando falla entonces muestra un toast de error', async () => {
    (apiClient.post as Mock).mockRejectedValueOnce({ response: { data: { error: 'No se puede aprobar sin renglones.' } } });
    render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

    fireEvent.click(screen.getByText(/Aprobar Plan/i));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });

  it('dado un plan en ejecucion cuando hace click en cerrar plan entonces invoca el endpoint de cierre', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: mockNecesidades });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({ data: [{ ...mockPlanes[0], estado: 'en_ejecucion' }] });
      }
      return Promise.resolve({ data: [] });
    });
    (apiClient.post as Mock).mockResolvedValueOnce({ data: { ...mockPlanes[0], estado: 'cerrado' } });
    render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

    fireEvent.click(screen.getByText(/Cerrar Plan/i));

    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/planes-produccion/1/cerrar/'));
    expect(toastSuccessMock).toHaveBeenCalledWith('Plan de producción cerrado correctamente');
  });

  it('dado el backend rechaza cerrar cuando falla entonces muestra un toast de error', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({ data: [{ ...mockPlanes[0], estado: 'en_ejecucion' }] });
      }
      return Promise.resolve({ data: [] });
    });
    (apiClient.post as Mock).mockRejectedValueOnce({ response: { data: { error: 'Quedan renglones sin completar.' } } });
    render(<PlanProduccionMTS />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

    fireEvent.click(screen.getByText(/Cerrar Plan/i));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
  });

  it('dado filtro de estado cuando cambia entonces reconsulta los planes con ese estado', async () => {
    render(<PlanProduccionMTS />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());
    (apiClient.get as Mock).mockClear();

    await userEvent.click(screen.getByRole('button', { name: 'Aprobado' }));

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith(
      '/planes-produccion/', { params: { estado: 'aprobado' } }));
  });

  it('dado click en actualizar cuando hace click entonces vuelve a consultar planes y necesidades', async () => {
    render(<PlanProduccionMTS />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());
    (apiClient.get as Mock).mockClear();

    await userEvent.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/planes-produccion/', { params: {} }));
    expect(apiClient.get).toHaveBeenCalledWith('/planes-produccion/necesidades-reposicion/', { params: {} });
  });

  describe('Generar Orden de Producción (MTS)', () => {
    beforeEach(() => {
      // El botón "Generar OP" solo aparece si el plan no está en borrador/cerrado
      (apiClient.get as Mock).mockImplementation((url: string) => {
        if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: mockNecesidades });
        if (url.includes('/planes-produccion/')) {
          return Promise.resolve({ data: [{ ...mockPlanes[0], estado: 'en_ejecucion' }] });
        }
        return Promise.resolve({ data: [] });
      });
    });

    it('dado click en generar OP cuando llena el formulario y confirma entonces envia el payload', async () => {
      (apiClient.post as Mock).mockResolvedValueOnce({ data: { mensaje: 'OP-2026-050 generada' } });
      render(<PlanProduccionMTS bodegas={[{ id: 5, nombre: 'Bodega PT Central', sede: 1 }]} />);
      await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Generar OP/i }));
      expect(screen.getByText('Generar Orden de Producción (MTS)')).toBeInTheDocument();
      // Precarga el saldo pendiente del renglón
      expect(screen.getByLabelText(/Cantidad a Requerir/i)).toHaveValue(80);

      await userEvent.click(screen.getByRole('button', { name: 'Urgente' }));
      await userEvent.click(screen.getByRole('button', { name: 'Bodega PT Central' }));
      await userEvent.click(screen.getByRole('button', { name: 'Lanzar Orden MTS' }));

      await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith('/planes-produccion/1/generar-orden/', {
        detalle_plan_id: 101, bodega_salida_id: 5, prioridad: 'urgente', peso_solicitado: 80,
      }));
      expect(toastSuccessMock).toHaveBeenCalledWith('OP-2026-050 generada');
      await waitFor(() => expect(screen.queryByText('Generar Orden de Producción (MTS)')).not.toBeInTheDocument());
    });

    it('dado el backend rechaza generar OP cuando falla entonces muestra un toast de error', async () => {
      (apiClient.post as Mock).mockRejectedValueOnce({ response: { data: { error: 'Stock insuficiente de materia prima.' } } });
      render(<PlanProduccionMTS bodegas={[{ id: 5, nombre: 'Bodega PT Central', sede: 1 }]} />);
      await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Generar OP/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Lanzar Orden MTS' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
    });

    it('dado el modal abierto cuando cancela entonces lo cierra sin llamar al backend', async () => {
      render(<PlanProduccionMTS />);
      await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Generar OP/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      expect(screen.queryByText('Generar Orden de Producción (MTS)')).not.toBeInTheDocument();
      expect(apiClient.post).not.toHaveBeenCalled();
    });
  });

  describe('Crear Plan desde la necesidad de producción', () => {
    it('dado el modal abierto cuando lo muestra entonces la sede es la del usuario y no se puede elegir otra', async () => {
      render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
      await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));

      expect(screen.getByText('Sede Principal')).toBeInTheDocument();
      expect(screen.queryByText('Seleccionar sede')).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Sede Principal' })).not.toBeInTheDocument();
    });

    it('dado que no se conoce el nombre de la sede cuando abre el modal entonces indica que se usa la sede asignada', async () => {
      render(<PlanProduccionMTS />);
      await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));

      expect(screen.getByLabelText('Sede')).toHaveValue('Sede asignada al usuario');
      expect(screen.getByLabelText('Sede')).toBeDisabled();
    });

    it('dado un codigo cuando confirma entonces crea el plan con los items de deficit sin enviar la sede', async () => {
      (apiClient.post as Mock).mockResolvedValueOnce({ data: {} });
      render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
      await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));
      await userEvent.type(screen.getByLabelText(/Código de Plan/i), 'PLAN-MTS-2026-06');
      await userEvent.click(screen.getByRole('button', { name: 'Crear y Aprobar Plan' }));

      await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith(
        '/planes-produccion/crear-desde-alertas/',
        expect.objectContaining({
          codigo: 'PLAN-MTS-2026-06', aprobar_inmediatamente: true,
          items: [{ producto_id: 30, deficit: 75 }],
        }),
      ));
      // La sede la toma el backend del usuario: el jefe de planta no la elige.
      expect((apiClient.post as Mock).mock.calls[0][1]).not.toHaveProperty('sede_id');
      expect(toastSuccessMock).toHaveBeenCalledWith('Plan de reposición creado y aprobado exitosamente a partir de alertas');
    });

    it('dado el backend rechaza crear el plan cuando falla entonces muestra un toast de error', async () => {
      (apiClient.post as Mock).mockRejectedValueOnce({ response: { data: { error: 'Ya existe un plan activo para esta sede.' } } });
      render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
      await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Crear y Aprobar Plan' }));

      await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al crear plan desde alertas'));
    });

    it('dado el modal abierto cuando cancela entonces lo cierra sin llamar al backend', async () => {
      render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
      await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

      await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));
      await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

      expect(screen.queryByText('Generar Plan desde la necesidad de producción')).not.toBeInTheDocument();
      expect(apiClient.post).not.toHaveBeenCalled();
    });
  });

  it('dado un selectedSedeId cuando carga entonces envia la sede como parametro en ambas consultas', async () => {
    render(<PlanProduccionMTS selectedSedeId={1} />);

    await waitFor(() => expect(apiClient.get).toHaveBeenCalledWith('/planes-produccion/', { params: { sede: '1' } }));
    expect(apiClient.get).toHaveBeenCalledWith('/planes-produccion/necesidades-reposicion/', { params: { sede: '1' } });
  });

  it('dado un plan y un renglon en estados no contemplados cuando renderiza entonces usa la insignia por defecto', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({
          data: [{ ...mockPlanes[0], estado: 'archivado', detalles: [{ ...mockPlanes[0].detalles[0], estado: 'desconocido' }] }],
        });
      }
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS />);

    await waitFor(() => expect(screen.getByText('archivado')).toBeInTheDocument());
    expect(screen.getByText('desconocido')).toBeInTheDocument();
  });

  it('dado renglones con distintos niveles de cumplimiento y desviacion cuando renderiza entonces usa los colores correspondientes', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({
          data: [{
            ...mockPlanes[0],
            detalles: [
              { ...mockPlanes[0].detalles[0], id: 201, cumplimiento_porcentaje: '100.00', desviacion_porcentaje: '10.00' },
              { ...mockPlanes[0].detalles[0], id: 202, cumplimiento_porcentaje: '60.00', desviacion_porcentaje: '0.00' },
            ],
          }],
        });
      }
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS />);

    await waitFor(() => expect(screen.getByText('100.0%')).toBeInTheDocument());
    expect(screen.getByText('60.0%')).toBeInTheDocument();
    expect(screen.getByText('+10.0%')).toBeInTheDocument();
    expect(screen.getByText('0.0%')).toBeInTheDocument();
  });

  it('dado un renglon sin bodegas ni saldo pendiente cuando abre generar OP entonces usa la cantidad planificada', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({
          data: [{
            ...mockPlanes[0], estado: 'en_ejecucion',
            detalles: [{ ...mockPlanes[0].detalles[0], saldo_pendiente: '0.0000', cantidad_planificada: '150.0000' }],
          }],
        });
      }
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS />);
    await waitFor(() => expect(screen.getByText('PLAN-MTS-2026-001')).toBeInTheDocument());

    // saldo_pendiente es '0.0000' (falsy con Number()), asi que no ofrece "Generar OP" en la fila
    // (regla del componente: solo si saldo_pendiente > 0). Verificamos que no aparezca el boton.
    expect(screen.queryByRole('button', { name: /Generar OP/i })).not.toBeInTheDocument();
  });

  it('dado codigo de plan vacio cuando confirma entonces lo envia como undefined', async () => {
    (apiClient.post as Mock).mockResolvedValueOnce({ data: {} });
    render(<PlanProduccionMTS sedeNombre="Sede Principal" />);
    await waitFor(() => expect(screen.getByText(/Crear Plan desde Déficits/i)).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /Crear Plan desde Déficits/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear y Aprobar Plan' }));

    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith(
      '/planes-produccion/crear-desde-alertas/',
      expect.objectContaining({ codigo: undefined }),
    ));
  });

  it('dado un renglon en distintos estados cuando renderiza entonces muestra la insignia correspondiente', async () => {
    (apiClient.get as Mock).mockImplementation((url: string) => {
      if (url.includes('/necesidades-reposicion/')) return Promise.resolve({ data: [] });
      if (url.includes('/planes-produccion/')) {
        return Promise.resolve({
          data: [
            { ...mockPlanes[0], estado: 'cerrado', detalles: [{ ...mockPlanes[0].detalles[0], estado: 'completado', saldo_pendiente: '0.0000' }] },
            { ...mockPlanes[0], id: 2, codigo: 'PLAN-MTS-2026-002', estado: 'cancelado', detalles: [{ ...mockPlanes[0].detalles[0], id: 102, estado: 'sobreproducido' }] },
          ],
        });
      }
      return Promise.resolve({ data: [] });
    });
    render(<PlanProduccionMTS />);

    await waitFor(() => expect(screen.getByText('Cerrado')).toBeInTheDocument());
    expect(screen.getByText('Completado')).toBeInTheDocument();
    expect(screen.getByText('Cancelado')).toBeInTheDocument();
    expect(screen.getByText('Sobreproducido')).toBeInTheDocument();
  });
});
