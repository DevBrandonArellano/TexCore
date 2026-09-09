import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  toLocalDatetimeInput, getOrdenVencimientoStatus, estadoBadge, prioridadBadge,
  buildOrdenPayload, validateOrdenForm, EMPTY_ORDEN_FORM_DATA, type OrdenFormData,
} from './ordenUtils';

describe('toLocalDatetimeInput', () => {
  it('dado una fecha cuando formatea entonces retorna YYYY-MM-DDTHH:mm con ceros a la izquierda', () => {
    const d = new Date(2026, 0, 5, 9, 5); // 5 enero 2026, 09:05 local
    expect(toLocalDatetimeInput(d)).toBe('2026-01-05T09:05');
  });
});

describe('getOrdenVencimientoStatus', () => {
  it('dado fecha fin en el pasado y estado no finalizada cuando evalua entonces marca vencida', () => {
    const { isOverdue, isToday } = getOrdenVencimientoStatus({ estado: 'pendiente', fecha_fin_planificada: '2020-01-01' });
    expect(isOverdue).toBeTruthy();
    expect(isToday).toBeFalsy();
  });

  it('dado fecha fin hoy y estado no finalizada cuando evalua entonces marca vence hoy', () => {
    const hoy = new Date().toISOString().split('T')[0];
    const { isOverdue, isToday } = getOrdenVencimientoStatus({ estado: 'en_proceso', fecha_fin_planificada: hoy });
    expect(isOverdue).toBeFalsy();
    expect(isToday).toBeTruthy();
  });

  it('dado orden finalizada cuando evalua entonces nunca marca vencida ni vence hoy', () => {
    const { isOverdue, isToday } = getOrdenVencimientoStatus({ estado: 'finalizada', fecha_fin_planificada: '2020-01-01' });
    expect(isOverdue).toBeFalsy();
    expect(isToday).toBeFalsy();
  });

  it('dado sin fecha fin planificada cuando evalua entonces no marca ni vencida ni vence hoy', () => {
    const { isOverdue, isToday } = getOrdenVencimientoStatus({ estado: 'pendiente', fecha_fin_planificada: null as any });
    expect(isOverdue).toBeFalsy();
    expect(isToday).toBeFalsy();
  });
});

describe('estadoBadge', () => {
  it.each([
    ['pendiente', 'Pendiente'],
    ['en_proceso', 'En Proceso'],
    ['finalizada', 'Finalizada'],
  ])('dado estado %s cuando genera el badge entonces muestra %s', (estado, texto) => {
    render(<>{estadoBadge(estado)}</>);
    expect(screen.getByText(texto)).toBeInTheDocument();
  });

  it('dado un estado no reconocido cuando genera el badge entonces usa el texto capitalizado por defecto', () => {
    render(<>{estadoBadge('en_pausa')}</>);
    expect(screen.getByText('en pausa')).toBeInTheDocument();
  });
});

describe('prioridadBadge', () => {
  it.each([
    ['baja', 'Baja'],
    ['normal', 'Normal'],
    ['alta', 'Alta'],
    ['urgente', 'Urgente'],
  ])('dado prioridad %s cuando genera el badge entonces muestra %s', (prioridad, texto) => {
    render(<>{prioridadBadge(prioridad)}</>);
    expect(screen.getByText(texto)).toBeInTheDocument();
  });

  it('dado una prioridad no reconocida cuando genera el badge entonces retorna null', () => {
    const { container } = render(<>{prioridadBadge('desconocida')}</>);
    expect(container.textContent).toBe('');
  });
});

describe('buildOrdenPayload', () => {
  const formData: OrdenFormData = {
    ...EMPTY_ORDEN_FORM_DATA,
    codigo: 'OP-001', producto_entrada: '1', producto_salida: '2',
    bodega_entrada: '3', bodega_salida: '4', formula_color: '5',
    sede: '6', area: '7', bodega_quimicos: '8', maquina_asignada: '9',
    fecha_inicio_planificada: '2026-01-01', fecha_fin_planificada: '2026-01-10',
  };

  it('dado ids como string cuando construye el payload entonces los convierte a numero', () => {
    const payload = buildOrdenPayload(formData);
    expect(payload.producto_entrada).toBe(1);
    expect(payload.bodega_entrada).toBe(3);
    expect(payload.formula_color).toBe(5);
    expect(payload.maquina_asignada).toBe(9);
  });

  it('dado campos opcionales vacios cuando construye el payload entonces los deja en null', () => {
    const payload = buildOrdenPayload({ ...formData, bodega_entrada: '', formula_color: '', sede: '', area: '', bodega_quimicos: '', maquina_asignada: '' });
    expect(payload.bodega_entrada).toBeNull();
    expect(payload.formula_color).toBeNull();
    expect(payload.sede).toBeNull();
    expect(payload.maquina_asignada).toBeNull();
  });

  it('dado maquina_asignada en 0 cuando construye el payload entonces la trata como sin asignar', () => {
    const payload = buildOrdenPayload({ ...formData, maquina_asignada: '0' });
    expect(payload.maquina_asignada).toBeNull();
  });

  it('dado fechas vacias cuando construye el payload entonces las deja en null', () => {
    const payload = buildOrdenPayload({ ...formData, fecha_inicio_planificada: '', fecha_fin_planificada: '' });
    expect(payload.fecha_inicio_planificada).toBeNull();
    expect(payload.fecha_fin_planificada).toBeNull();
  });
});

describe('validateOrdenForm', () => {
  it('dado formulario vacio en modo creacion cuando valida entonces exige codigo, area y peso pero no productos', () => {
    const errors = validateOrdenForm(EMPTY_ORDEN_FORM_DATA, false);
    expect(errors.codigo).toBeDefined();
    expect(errors.area).toBeDefined();
    expect(errors.peso_neto_requerido).toBeDefined();
    expect(errors.producto_entrada).toBeUndefined();
  });

  it('dado formulario vacio en modo edicion cuando valida entonces tambien exige productos de entrada y salida', () => {
    const errors = validateOrdenForm(EMPTY_ORDEN_FORM_DATA, true);
    expect(errors.producto_entrada).toBeDefined();
    expect(errors.producto_salida).toBeDefined();
  });

  it('dado peso requerido cero o negativo cuando valida entonces marca error de peso', () => {
    expect(validateOrdenForm({ ...EMPTY_ORDEN_FORM_DATA, codigo: 'X', area: '1', peso_neto_requerido: '0' }, false).peso_neto_requerido).toBeDefined();
    expect(validateOrdenForm({ ...EMPTY_ORDEN_FORM_DATA, codigo: 'X', area: '1', peso_neto_requerido: '-5' }, false).peso_neto_requerido).toBeDefined();
  });

  it('dado formulario valido en modo creacion cuando valida entonces no retorna errores', () => {
    const errors = validateOrdenForm({ ...EMPTY_ORDEN_FORM_DATA, codigo: 'OP-1', area: '1', peso_neto_requerido: '100' }, false);
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it('dado formulario valido y completo en modo edicion cuando valida entonces no retorna errores', () => {
    const errors = validateOrdenForm({
      ...EMPTY_ORDEN_FORM_DATA, codigo: 'OP-1', area: '1', peso_neto_requerido: '100',
      producto_entrada: '1', producto_salida: '2',
    }, true);
    expect(Object.keys(errors)).toHaveLength(0);
  });
});
