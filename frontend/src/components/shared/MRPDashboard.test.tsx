import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MRPDashboard } from './MRPDashboard';
import type { MRPEjecucion, NecesidadReposicion, OrdenCompraSugerida, RequerimientoMaterial } from '../../lib/types';

const mrp = {
  listarSugerencias: vi.fn(),
  listarRequerimientos: vi.fn(),
  ultimaEjecucion: vi.fn(),
  necesidadesProduccion: vi.fn(),
  ejecutar: vi.fn(),
};
vi.mock('../../lib/api/mrpApi', () => ({
  mrpApi: {
    listarSugerencias: (...a: unknown[]) => mrp.listarSugerencias(...a),
    listarRequerimientos: (...a: unknown[]) => mrp.listarRequerimientos(...a),
    ultimaEjecucion: (...a: unknown[]) => mrp.ultimaEjecucion(...a),
    necesidadesProduccion: (...a: unknown[]) => mrp.necesidadesProduccion(...a),
    ejecutar: (...a: unknown[]) => mrp.ejecutar(...a),
  },
}));

const toast = { error: vi.fn(), success: vi.fn(), warning: vi.fn() };
vi.mock('sonner', () => ({
  toast: {
    error: (...a: unknown[]) => toast.error(...a),
    success: (...a: unknown[]) => toast.success(...a),
    warning: (...a: unknown[]) => toast.warning(...a),
  },
}));

const EJECUCION: MRPEjecucion = {
  id: 7, sede: 1, sede_nombre: 'Sede Norte', iniciada_por_nombre: 'bodega1',
  inicio: '2026-10-13T15:30:00Z', fin: '2026-10-13T15:30:02Z', estado: 'completada',
  requerimientos: 12, sugerencias_compra: 4, productos_a_producir: 3,
  advertencias: ['OP E1-CONT-01: sin peso requerido (producción continua); no se calculan sus materiales.'],
  mensaje_error: '',
};

const SUGERENCIA: OrdenCompraSugerida = {
  id: 1, ejecucion: 7, producto: 10, producto_nombre: 'Algodón crudo', producto_codigo: 'MP-ALG',
  sede: 1, sede_nombre: 'Sede Norte', requerido: '60.000', stock_minimo: '20.000', stock_disponible: '10.000',
  cantidad_sugerida: '70.000', fecha_generacion: '2026-10-13T15:30:01Z',
};

const REQUERIMIENTO: RequerimientoMaterial = {
  id: 1, ejecucion: 7, producto_requerido: 10, producto_nombre: 'Igualante', producto_codigo: 'Q-IGU',
  cantidad_necesaria: '1.600', sede: 1, sede_nombre: 'Sede Norte', orden_produccion: 3,
  orden_codigo: 'OP-0042', fecha_requerida: '2026-10-20',
};

const NECESIDAD: NecesidadReposicion = {
  sede_id: 1, sede_nombre: 'Sede Norte', producto_id: 20, producto_codigo: 'HI-AZ',
  producto_descripcion: 'Hilo azul', tipo: 'hilo', unidad_medida: 'kg', stock_actual: '20.0000',
  stock_minimo: '10.0000', demanda_pedidos: '270.0000', demanda_interna: '0.0000', en_produccion: '100.0000',
  deficit: '160.0000',
};

const pagina = <T,>(results: T[]) => ({ count: results.length, next: null, previous: null, results });

function datos({
  ejecuciones = [EJECUCION], sugerencias = [SUGERENCIA], requerimientos = [REQUERIMIENTO], necesidades = [NECESIDAD],
}: {
  ejecuciones?: MRPEjecucion[]; sugerencias?: OrdenCompraSugerida[];
  requerimientos?: RequerimientoMaterial[]; necesidades?: NecesidadReposicion[];
} = {}) {
  mrp.ultimaEjecucion.mockResolvedValue(ejecuciones);
  mrp.listarSugerencias.mockResolvedValue(pagina(sugerencias));
  mrp.listarRequerimientos.mockResolvedValue(pagina(requerimientos));
  mrp.necesidadesProduccion.mockResolvedValue(necesidades);
}

describe('MRPDashboard', () => {
  beforeEach(() => {
    Object.values(mrp).forEach((m) => m.mockReset());
    Object.values(toast).forEach((m) => m.mockReset());
    datos();
  });

  it('dado una ejecucion previa cuando carga entonces muestra la ultima ejecucion con sus conteos y advertencias', async () => {
    render(<MRPDashboard />);
    const tarjeta = await screen.findByTestId('ultima-ejecucion-1');
    expect(within(tarjeta).getByText('Sede Norte')).toBeInTheDocument();
    expect(within(tarjeta).getByText(/bodega1/)).toBeInTheDocument();
    expect(within(tarjeta).getByText('Completada')).toBeInTheDocument();
    expect(within(tarjeta).getByText(/4 sugerencias de compra/)).toBeInTheDocument();
    expect(within(tarjeta).getByText(/3 productos a producir/)).toBeInTheDocument();
    expect(within(tarjeta).getByText(/E1-CONT-01/)).toBeInTheDocument();
  });

  it('dado sin ejecuciones cuando carga entonces invita a ejecutar el MRP', async () => {
    datos({ ejecuciones: [] });
    render(<MRPDashboard />);
    expect(await screen.findByText(/Aún no se ha ejecutado el MRP/)).toBeInTheDocument();
  });

  it('dado sugerencias cuando carga entonces muestra el desglose de cada una', async () => {
    render(<MRPDashboard />);
    const fila = (await screen.findByText('Algodón crudo')).closest('tr') as HTMLElement;
    for (const valor of ['60', '20', '10', '70']) {
      expect(within(fila).getByText(valor)).toBeInTheDocument();
    }
  });

  it('dado sin sugerencias cuando carga entonces indica que el stock cubre la demanda', async () => {
    datos({ sugerencias: [] });
    render(<MRPDashboard />);
    expect(await screen.findByText(/No hay sugerencias de compra/)).toBeInTheDocument();
  });

  it('dado la pestaña de requerimientos cuando la abre entonces muestra la orden de origen y su fecha', async () => {
    render(<MRPDashboard />);
    await userEvent.click(await screen.findByRole('tab', { name: /Requerimientos por orden/ }));
    const fila = (await screen.findByText('OP-0042')).closest('tr') as HTMLElement;
    expect(within(fila).getByText('Igualante')).toBeInTheDocument();
    expect(within(fila).getByText('1,6')).toBeInTheDocument();
    expect(within(fila).getByText('20/10/2026')).toBeInTheDocument();
  });

  it('dado la pestaña de necesidad de produccion cuando la abre entonces muestra el desglose', async () => {
    render(<MRPDashboard />);
    await userEvent.click(await screen.findByRole('tab', { name: /Necesidad de producción/ }));
    const fila = (await screen.findByText('Hilo azul')).closest('tr') as HTMLElement;
    for (const valor of ['270', '100', '160']) {
      expect(within(fila).getByText(valor)).toBeInTheDocument();
    }
  });

  it('dado un usuario de sede cuando ejecuta entonces calcula su sede y recarga los resultados', async () => {
    mrp.ejecutar.mockResolvedValueOnce([EJECUCION]);
    render(<MRPDashboard />);
    await screen.findByTestId('ultima-ejecucion-1');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP/ }));

    await waitFor(() => expect(mrp.ejecutar).toHaveBeenCalledWith({}));
    expect(toast.success).toHaveBeenCalledWith('MRP calculado: 4 sugerencias de compra y 3 productos a producir.');
    expect(toast.warning).toHaveBeenCalledWith('El cálculo dejó 1 advertencia: revísela en la última ejecución.');
    await waitFor(() => expect(mrp.ultimaEjecucion).toHaveBeenCalledTimes(2));
  });

  it('dado todas las sedes en un rol global cuando ejecuta entonces calcula todas', async () => {
    mrp.ejecutar.mockResolvedValueOnce([{ ...EJECUCION, advertencias: [] }]);
    render(<MRPDashboard sedeId="todas" />);
    await screen.findByTestId('ultima-ejecucion-1');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP \(todas las sedes\)/ }));

    await waitFor(() => expect(mrp.ejecutar).toHaveBeenCalledWith({ todas: true }));
    expect(mrp.listarSugerencias).toHaveBeenCalledWith(1, expect.any(Number), undefined);
  });

  it('dado una sede elegida en un rol global cuando consulta y ejecuta entonces usa esa sede', async () => {
    mrp.ejecutar.mockResolvedValueOnce([{ ...EJECUCION, advertencias: [] }]);
    render(<MRPDashboard sedeId="3" />);
    await screen.findByTestId('ultima-ejecucion-1');
    expect(mrp.listarSugerencias).toHaveBeenCalledWith(1, expect.any(Number), '3');
    expect(mrp.ultimaEjecucion).toHaveBeenCalledWith('3');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP/ }));

    await waitFor(() => expect(mrp.ejecutar).toHaveBeenCalledWith({ sede_id: 3 }));
  });

  it('dado una ejecucion fallida cuando ejecuta entonces muestra el error de la sede', async () => {
    mrp.ejecutar.mockResolvedValueOnce([{ ...EJECUCION, estado: 'fallida', mensaje_error: 'Error interno al calcular' }]);
    render(<MRPDashboard />);
    await screen.findByTestId('ultima-ejecucion-1');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Sede Norte: Error interno al calcular'));
    expect(toast.success).not.toHaveBeenCalled();
  });

  it('dado un error de la peticion cuando ejecuta entonces avisa con el mensaje de la API', async () => {
    mrp.ejecutar.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'Solo puede calcular el MRP de su sede.' } } });
    render(<MRPDashboard />);
    await screen.findByTestId('ultima-ejecucion-1');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Solo puede calcular el MRP de su sede.'));
  });

  it('dado una ultima ejecucion fallida sin usuario cuando carga entonces muestra el error y el origen sistema', async () => {
    datos({ ejecuciones: [{ ...EJECUCION, estado: 'fallida', iniciada_por_nombre: null, advertencias: [],
      mensaje_error: 'Error interno al calcular el MRP de la sede.' }] });
    render(<MRPDashboard />);
    const tarjeta = await screen.findByTestId('ultima-ejecucion-1');
    expect(within(tarjeta).getByText('Fallida')).toBeInTheDocument();
    expect(within(tarjeta).getByText(/sistema/)).toBeInTheDocument();
    expect(within(tarjeta).getByText('Error interno al calcular el MRP de la sede.')).toBeInTheDocument();
  });

  it('dado todas las sedes con una fallida y otra completada cuando ejecuta entonces avisa ambas', async () => {
    mrp.ejecutar.mockResolvedValueOnce([
      { ...EJECUCION, sede: 1, sede_nombre: 'Sede Norte', estado: 'fallida', mensaje_error: 'Error interno' },
      { ...EJECUCION, id: 8, sede: 2, sede_nombre: 'Sede Sur', sugerencias_compra: 1, productos_a_producir: 1,
        advertencias: ['a', 'b'] },
    ]);
    render(<MRPDashboard sedeId="todas" />);
    await screen.findByTestId('ultima-ejecucion-1');

    await userEvent.click(screen.getByRole('button', { name: /Ejecutar MRP/ }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Sede Norte: Error interno'));
    expect(toast.success).toHaveBeenCalledWith('MRP calculado: 1 sugerencia de compra y 1 producto a producir.');
    expect(toast.warning).toHaveBeenCalledWith('El cálculo dejó 2 advertencias: revíselas en la última ejecución.');
  });

  it('dado mas sugerencias que una pagina cuando carga entonces pagina en el servidor', async () => {
    const muchas = Array.from({ length: 25 }, (_, i) => ({ ...SUGERENCIA, id: i + 1, producto_codigo: `MP-${i}` }));
    mrp.listarSugerencias.mockImplementation((bloque: number, tamano: number) => Promise.resolve({
      count: muchas.length, next: null, previous: null, results: muchas.slice((bloque - 1) * tamano, bloque * tamano),
    }));
    render(<MRPDashboard />);
    expect(await screen.findByText('MP-0')).toBeInTheDocument();
    expect(screen.queryByText('MP-24')).not.toBeInTheDocument();
    expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument();
  });

  it('dado un error al cargar cuando consulta entonces avisa', async () => {
    mrp.ultimaEjecucion.mockRejectedValueOnce(new Error('caído'));
    render(<MRPDashboard />);
    expect(await screen.findByText(/No se pudo cargar la información del MRP/)).toBeInTheDocument();
  });
});
