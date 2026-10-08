import { describe, it, expect } from 'vitest';
import { datosDeError, estadoHttp, getApiErrorMessage, mensajeDeLaApi } from './apiError';

// Estilo de tabla — mismo patrón que errorUtils.test.ts: sin mocks, sin
// render, un caso por status. Cubre el switch completo (400/401/403/404/
// 409/500-504/default) y las dos formas de extraerDetalleValidacion.

describe('getApiErrorMessage', () => {
  it('dado 400 con detail cuando formatea entonces retorna el detail', () => {
    const error = { response: { status: 400, data: { detail: 'Campo requerido' } } };
    expect(getApiErrorMessage(error)).toBe('Campo requerido');
  });

  it('dado 400 con error string cuando formatea entonces retorna ese mensaje', () => {
    const error = { response: { status: 400, data: { error: 'Formato inválido' } } };
    expect(getApiErrorMessage(error)).toBe('Formato inválido');
  });

  // Sobre del handler unificado del backend (gestion/exceptions.py).
  it('dado 400 con el sobre del backend cuando formatea entonces retorna error.message', () => {
    const error = { response: { status: 400, data: {
      success: false,
      error: { code: 400, message: 'porcentaje: La mezcla supera el 100 %.', fields: { porcentaje: ['La mezcla supera el 100 %.'] } },
    } } };
    expect(getApiErrorMessage(error)).toBe('porcentaje: La mezcla supera el 100 %.');
  });

  it('dado 403 con el sobre del backend cuando formatea entonces retorna error.message', () => {
    const error = { response: { status: 403, data: {
      success: false, error: { code: 403, message: 'No tiene permiso para realizar esta acción.' },
    } } };
    expect(getApiErrorMessage(error)).toBe('No tiene permiso para realizar esta acción.');
  });

  it('dado 400 con errores por campo cuando formatea entonces los une legibles', () => {
    const error = { response: { status: 400, data: { username: ['Ya existe'], email: ['Inválido'] } } };
    expect(getApiErrorMessage(error)).toBe('username: Ya existe | email: Inválido');
  });

  it('dado 400 sin cuerpo interpretable cuando formatea entonces usa el mensaje generico de validacion', () => {
    const error = { response: { status: 400, data: null } };
    expect(getApiErrorMessage(error)).toBe('Datos inválidos. Revisa los campos e intenta de nuevo.');
  });

  it('dado 401 cuando formatea entonces indica sesion expirada', () => {
    const error = { response: { status: 401 } };
    expect(getApiErrorMessage(error)).toBe('Tu sesión expiró. Vuelve a iniciar sesión.');
  });

  it('dado 403 con detail cuando formatea entonces retorna el detail', () => {
    const error = { response: { status: 403, data: { detail: 'No autorizado para esta sede' } } };
    expect(getApiErrorMessage(error)).toBe('No autorizado para esta sede');
  });

  it('dado 403 sin cuerpo cuando formatea entonces usa el mensaje generico de permiso', () => {
    const error = { response: { status: 403, data: {} } };
    expect(getApiErrorMessage(error)).toBe('No tienes permiso para realizar esta acción.');
  });

  it('dado 404 cuando formatea entonces indica recurso inexistente', () => {
    const error = { response: { status: 404 } };
    expect(getApiErrorMessage(error)).toBe('El recurso no existe o ya fue eliminado.');
  });

  it('dado 409 cuando formatea entonces indica conflicto de version', () => {
    const error = { response: { status: 409 } };
    expect(getApiErrorMessage(error)).toBe('El recurso cambió mientras trabajabas. Recarga e intenta de nuevo.');
  });

  it.each([500, 502, 503, 504])('dado %i cuando formatea entonces indica error del servidor', (status) => {
    const error = { response: { status } };
    expect(getApiErrorMessage(error)).toBe('Error del servidor. Si persiste, contacta al administrador.');
  });

  it('dado sin respuesta y con request cuando formatea entonces indica problema de red', () => {
    const error = { request: {}, response: undefined };
    expect(getApiErrorMessage(error)).toBe('Sin conexión con el servidor. Verifica tu red e intenta de nuevo.');
  });

  it('dado codigo ERR_NETWORK cuando formatea entonces indica problema de red', () => {
    const error = { code: 'ERR_NETWORK', response: undefined };
    expect(getApiErrorMessage(error)).toBe('Sin conexión con el servidor. Verifica tu red e intenta de nuevo.');
  });

  it('dado status no clasificado cuando formatea entonces retorna el fallback por defecto', () => {
    const error = { response: { status: 418 } };
    expect(getApiErrorMessage(error)).toBe('Ocurrió un error inesperado. Intenta de nuevo.');
  });

  it('dado fallback personalizado cuando el error no es clasificable entonces lo retorna', () => {
    const error = {};
    expect(getApiErrorMessage(error, 'No se pudo completar la operación.')).toBe(
      'No se pudo completar la operación.',
    );
  });
});

// Helpers tipados para los `catch` (reemplazan `catch (error: any)` sin cambiar el mensaje
// que envía el backend). Fase 8 del plan, ESLint no-explicit-any.
describe('mensajeDeLaApi / estadoHttp / datosDeError', () => {
  it('dado error string del backend cuando extrae entonces lo devuelve tal cual', () => {
    const error = { response: { status: 409, data: { error: 'El pedido ya fue despachado.' } } };
    expect(mensajeDeLaApi(error, 'respaldo')).toBe('El pedido ya fue despachado.');
  });

  it('dado el sobre unificado cuando extrae entonces devuelve error.message y no un objeto', () => {
    const error = { response: { status: 400, data: { success: false, error: { code: 400, message: 'monto: inválido' } } } };
    expect(mensajeDeLaApi(error, 'respaldo')).toBe('monto: inválido');
  });

  it('dado error sin respuesta cuando extrae entonces usa el respaldo', () => {
    expect(mensajeDeLaApi(new Error('red'), 'Sin conexión')).toBe('Sin conexión');
    expect(mensajeDeLaApi(undefined, 'Sin conexión')).toBe('Sin conexión');
  });

  it('dado respuesta con status cuando consulta entonces lo devuelve', () => {
    expect(estadoHttp({ response: { status: 404 } })).toBe(404);
    expect(estadoHttp(new Error('x'))).toBeUndefined();
  });

  it('dado respuesta con cuerpo cuando consulta entonces devuelve los datos', () => {
    expect(datosDeError({ response: { data: { items_incompletos: { a: 1 } } } })).toEqual({ items_incompletos: { a: 1 } });
    expect(datosDeError(null)).toBeUndefined();
  });
});

describe('extraerDetalleValidacion con objetos anidados', () => {
  it('dado un campo con un objeto anidado cuando extrae entonces lo serializa en vez de [object Object]', () => {
    const error = { response: { status: 400, data: { error: { campo: ['inválido'] } } } };
    expect(mensajeDeLaApi(error, 'respaldo')).toBe('error: {"campo":["inválido"]}');
  });
});
