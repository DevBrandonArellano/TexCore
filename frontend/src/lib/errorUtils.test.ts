import { describe, it, expect } from 'vitest';
import { formatApiError } from './errorUtils';

describe('formatApiError (Seguridad ISO 27001 & Usabilidad ISO 25010)', () => {
  it('dado error 403 cuando formatea entonces retorna mensaje accesible sin exponer endpoints', () => {
    const error = { response: { status: 403 } };
    const result = formatApiError(error);
    expect(result.message).toBe('Acceso restringido.');
    expect(result.note).toContain('permisos o rol requeridos');
  });

  it('dado error 500 cuando formatea entonces no expone stack trace ni detalles de BD', () => {
    const error = {
      response: {
        status: 500,
        data: 'IntegrityError: (23000) SQL Server CK_lote_empaque_cono_1 violated in table dbo.gestion_loteproduccion',
      },
    };
    const result = formatApiError(error);
    expect(result.message).toBe('No se pudo completar la operación.');
    expect(result.note).not.toContain('SQL');
    expect(result.note).not.toContain('CK_lote_empaque_cono_1');
    expect(result.note).toContain('Inconveniente en el servicio central');
  });

  it('dado error de merma cuando formatea entonces incluye la nota explicativa operacional', () => {
    const error = {
      response: {
        status: 400,
        data: { detail: 'La merma no puede ser mayor a la orden de producción.' },
      },
    };
    const result = formatApiError(error);
    expect(result.message).toBe('La merma no puede ser mayor a la orden de producción.');
    expect(result.note).toContain('no puede ser superior a la cantidad requerida');
  });

  it('dado error de campos tecnicos (snake_case) cuando formatea entonces traduce el nombre del campo a etiqueta legible', () => {
    const error = {
      response: {
        status: 400,
        data: { peso_neto_producido: ['Debe ser un número positivo.'] },
      },
    };
    const result = formatApiError(error);
    expect(result.message).toBe('Peso Neto Producido: Debe ser un número positivo.');
    expect(result.fieldErrors?.['Peso Neto Producido']).toBe('Debe ser un número positivo.');
  });

  it('dado mensaje con fuga de informacion (SQL / URLs) cuando formatea entonces sanitiza la salida', () => {
    const error = {
      response: {
        status: 400,
        data: { detail: 'Error en /api/ordenes-produccion/ SELECT FROM dbo.gestion_ordenproduccion' },
      },
    };
    const result = formatApiError(error);
    expect(result.message).toBe('La operación no pudo ser procesada por una restricción de datos.');
    expect(result.message).not.toContain('SELECT');
    expect(result.message).not.toContain('/api/');
  });
});
