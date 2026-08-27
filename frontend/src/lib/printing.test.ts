import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  printLabel,
  resolvePreferredMode,
  getDefaultZebraDevice,
  sendZpl,
  abrirPdfParaImprimir,
} from './printing';

// printing.ts concentra efectos de plataforma (Zebra Browser Print, blobs,
// portapapeles) que jsdom no implementa. Siguiendo el patrón ya establecido
// en el repo (EmpaquetadoDashboard.test.tsx, HistorialEtiquetasModal.test.tsx),
// se stubean los globals reales directamente aquí — sin introducir un patrón
// de inyección de dependencias nuevo. Cada unidad antes privada se exporta
// para poder apuntarle con un test propio, sin cambiar su comportamiento.

const mockGet = vi.fn();
vi.mock('./axios', () => ({
  default: { get: (...args: any[]) => mockGet(...args) },
}));

describe('resolvePreferredMode', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('dado sin valor guardado cuando resuelve entonces retorna auto', () => {
    expect(resolvePreferredMode()).toBe('auto');
  });

  it('dado valor pdf guardado cuando resuelve entonces retorna pdf', () => {
    window.localStorage.setItem('texcore_preferred_printer', 'pdf');
    expect(resolvePreferredMode()).toBe('pdf');
  });

  it('dado localStorage.getItem lanzando excepcion cuando resuelve entonces cae a auto', () => {
    const spy = vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
      throw new Error('acceso denegado (modo incognito)');
    });
    expect(resolvePreferredMode()).toBe('auto');
    spy.mockRestore();
  });
});

describe('getDefaultZebraDevice', () => {
  afterEach(() => {
    delete (window as any).BrowserPrint;
  });

  it('dado BrowserPrint ausente cuando resuelve entonces retorna null', async () => {
    delete (window as any).BrowserPrint;
    await expect(getDefaultZebraDevice()).resolves.toBeNull();
  });

  it('dado getDefaultDevice con exito cuando resuelve entonces retorna el device', async () => {
    const device = { name: 'ZebraLP', uid: 'zebra-1', connection: 'usb', send: vi.fn() };
    (window as any).BrowserPrint = {
      getDefaultDevice: (_type: string, onSuccess: (d: any) => void) => onSuccess(device),
    };
    await expect(getDefaultZebraDevice()).resolves.toEqual(device);
  });

  it('dado getDefaultDevice invocando onError cuando resuelve entonces retorna null', async () => {
    (window as any).BrowserPrint = {
      getDefaultDevice: (_type: string, _onSuccess: any, onError: (err: string) => void) => onError('sin impresora'),
    };
    await expect(getDefaultZebraDevice()).resolves.toBeNull();
  });
});

describe('sendZpl', () => {
  it('dado device.send con exito cuando envia entonces resuelve', async () => {
    const device = { send: (_zpl: string, onSuccess?: () => void) => onSuccess?.() } as any;
    await expect(sendZpl(device, '^XA^XZ')).resolves.toBeUndefined();
  });

  it('dado device.send con onError cuando envia entonces rechaza con Error', async () => {
    const device = { send: (_zpl: string, _onSuccess?: any, onError?: (e: string) => void) => onError?.('impresora sin papel') } as any;
    await expect(sendZpl(device, '^XA^XZ')).rejects.toThrow('impresora sin papel');
  });
});

describe('abrirPdfParaImprimir', () => {
  let createObjectURLMock: ReturnType<typeof vi.fn>;
  let revokeObjectURLMock: ReturnType<typeof vi.fn>;
  let windowOpenMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockGet.mockReset();
    createObjectURLMock = vi.fn().mockReturnValue('blob:mock-url');
    revokeObjectURLMock = vi.fn();
    (global as any).URL.createObjectURL = createObjectURLMock;
    (global as any).URL.revokeObjectURL = revokeObjectURLMock;
    windowOpenMock = vi.fn();
    vi.stubGlobal('open', windowOpenMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('dado respuesta exitosa cuando abre entonces crea el blob y abre la ventana con print', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });
    const printMock = vi.fn();
    const ventana: any = {};
    Object.defineProperty(ventana, 'onload', {
      set(fn: () => void) { fn(); },
    });
    ventana.print = printMock;
    windowOpenMock.mockReturnValue(ventana);

    await abrirPdfParaImprimir(7, { tipo_evento: 'REETIQUETADO', version: 2 });

    expect(createObjectURLMock).toHaveBeenCalled();
    expect(windowOpenMock).toHaveBeenCalledWith('blob:mock-url', '_blank');
    expect(printMock).toHaveBeenCalled();
  });

  it('dado popup bloqueado (window.open retorna null) cuando abre entonces no lanza', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });
    windowOpenMock.mockReturnValue(null);

    await expect(abrirPdfParaImprimir(7)).resolves.toBeUndefined();
  });

  it('dado exito cuando pasa el tiempo entonces revoca el blob a los 60 segundos', async () => {
    vi.useFakeTimers();
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });
    windowOpenMock.mockReturnValue(null);

    await abrirPdfParaImprimir(7);
    expect(revokeObjectURLMock).not.toHaveBeenCalled();
    vi.advanceTimersByTime(60_000);
    expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:mock-url');
  });
});

describe('printLabel', () => {
  beforeEach(() => {
    mockGet.mockReset();
    window.localStorage.clear();
    delete (window as any).BrowserPrint;
    (global as any).URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-url');
    (global as any).URL.revokeObjectURL = vi.fn();
    vi.stubGlobal('open', vi.fn().mockReturnValue(null));
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('dado preferencia pdf y exito cuando imprime entonces retorna pdf', async () => {
    window.localStorage.setItem('texcore_preferred_printer', 'pdf');
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('pdf');
  });

  it('dado preferencia pdf y fallo cuando imprime entonces cae a portapapeles', async () => {
    window.localStorage.setItem('texcore_preferred_printer', 'pdf');
    mockGet.mockRejectedValue(new Error('servicio caido'));

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('clipboard');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('^XA^XZ');
  });

  it('dado modo auto con zebra disponible y envio exitoso cuando imprime entonces retorna zebra', async () => {
    const device = { send: (_z: string, onSuccess?: () => void) => onSuccess?.() };
    (window as any).BrowserPrint = {
      getDefaultDevice: (_t: string, onSuccess: (d: any) => void) => onSuccess(device),
    };

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('zebra');
    expect(mockGet).not.toHaveBeenCalled();
  });

  it('dado modo auto con zebra disponible pero envio fallido cuando imprime entonces cae a pdf', async () => {
    const device = { send: (_z: string, _onSuccess?: any, onError?: (e: string) => void) => onError?.('sin papel') };
    (window as any).BrowserPrint = {
      getDefaultDevice: (_t: string, onSuccess: (d: any) => void) => onSuccess(device),
    };
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('pdf');
  });

  it('dado modo auto sin zebra disponible cuando imprime entonces va directo a pdf', async () => {
    mockGet.mockResolvedValue({ data: new Blob(['%PDF']) });

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('pdf');
  });

  it('dado modo auto sin zebra y pdf tambien falla cuando imprime entonces cae a portapapeles', async () => {
    mockGet.mockRejectedValue(new Error('servicio caido'));

    await expect(printLabel(1, '^XA^XZ')).resolves.toBe('clipboard');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('^XA^XZ');
  });
});
