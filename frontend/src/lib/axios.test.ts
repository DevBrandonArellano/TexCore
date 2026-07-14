import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockPost = vi.fn();
const mockApiClientCall = vi.fn();

let responseSuccessHandler: (response: any) => any;
let responseErrorHandler: (error: any) => any;

vi.mock('axios', () => {
  const instance: any = vi.fn((config: any) => mockApiClientCall(config));
  instance.post = (...args: any[]) => mockPost(...args);
  instance.interceptors = {
    response: {
      use: (onSuccess: any, onError: any) => {
        responseSuccessHandler = onSuccess;
        responseErrorHandler = onError;
      },
    },
  };
  return {
    default: {
      create: () => instance,
    },
  };
});

vi.mock('./logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    notice: vi.fn(),
    critical: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  }),
}));

describe('apiClient (axios interceptor)', () => {
  beforeEach(async () => {
    vi.resetModules();
    mockPost.mockReset();
    mockApiClientCall.mockReset();
    await import('./axios');
  });

  it('dado una respuesta exitosa cuando pasa por el interceptor entonces la retorna sin cambios', () => {
    const response = { config: { method: 'get', url: '/productos/' }, status: 200 };
    expect(responseSuccessHandler(response)).toBe(response);
  });

  it('dado un 401 en un endpoint distinto de token/profile cuando falla entonces reintenta tras refrescar', async () => {
    mockPost.mockResolvedValueOnce({});
    mockApiClientCall.mockResolvedValueOnce({ status: 200, data: 'ok' });

    const originalRequest: any = { url: '/productos/', method: 'get' };
    const error = { config: originalRequest, response: { status: 401 } };

    const result = await responseErrorHandler(error);

    expect(mockPost).toHaveBeenCalledWith('/token/refresh/');
    expect(originalRequest._retry).toBe(true);
    expect(result).toEqual({ status: 200, data: 'ok' });
  });

  it('dado que el refresh tambien falla cuando hay 401 entonces dispara auth:session-expired y rechaza', async () => {
    const refreshError = new Error('refresh inválido');
    mockPost.mockRejectedValueOnce(refreshError);
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent');

    const originalRequest: any = { url: '/productos/', method: 'get' };
    const error = { config: originalRequest, response: { status: 401 } };

    await expect(responseErrorHandler(error)).rejects.toBe(refreshError);
    expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({ type: 'auth:session-expired' }));
  });

  it('dado un 401 en /token/ cuando falla entonces no intenta refrescar (evita bucle de login)', async () => {
    const originalRequest: any = { url: '/token/', method: 'post' };
    const error = { config: originalRequest, response: { status: 401 } };

    await expect(responseErrorHandler(error)).rejects.toBe(error);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado un 401 en /profile/ cuando falla entonces no intenta refrescar', async () => {
    const originalRequest: any = { url: '/profile/', method: 'get' };
    const error = { config: originalRequest, response: { status: 401 } };

    await expect(responseErrorHandler(error)).rejects.toBe(error);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado un 401 ya reintentado (_retry=true) cuando falla de nuevo entonces no reintenta otra vez', async () => {
    const originalRequest: any = { url: '/productos/', method: 'get', _retry: true };
    const error = { config: originalRequest, response: { status: 401 } };

    await expect(responseErrorHandler(error)).rejects.toBe(error);
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('dado un error 500 cuando falla entonces rechaza con el error original', async () => {
    const error = { config: { url: '/reportes/', method: 'get' }, response: { status: 500 } };
    await expect(responseErrorHandler(error)).rejects.toBe(error);
  });

  it('dado un error de red (sin response) cuando falla entonces rechaza con el error original', async () => {
    const error = { config: { url: '/reportes/', method: 'get' } };
    await expect(responseErrorHandler(error)).rejects.toBe(error);
  });
});
