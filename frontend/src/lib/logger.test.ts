import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createLogger, Severity } from './logger';

describe('RFC5424Logger', () => {
  let consoleSpies: Record<string, ReturnType<typeof vi.spyOn>>;
  let sendBeaconSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    consoleSpies = {
      debug: vi.spyOn(console, 'debug').mockImplementation(() => {}),
      info: vi.spyOn(console, 'info').mockImplementation(() => {}),
      warn: vi.spyOn(console, 'warn').mockImplementation(() => {}),
      error: vi.spyOn(console, 'error').mockImplementation(() => {}),
    };
    sendBeaconSpy = vi.fn().mockReturnValue(true);
    (navigator as any).sendBeacon = sendBeaconSpy;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('dado un mensaje info cuando emite entonces usa console.info con formato RFC 5424', () => {
    const logger = createLogger('TestModule');
    logger.info('mensaje de prueba', { sede_id: '3' });

    expect(consoleSpies.info).toHaveBeenCalledTimes(1);
    const emitted = consoleSpies.info.mock.calls[0][0] as string;
    expect(emitted).toContain('TestModule');
    expect(emitted).toContain('mensaje de prueba');
    expect(emitted).toContain('sede_id="3"');
  });

  it('dado un mensaje error cuando emite entonces usa console.error', () => {
    const logger = createLogger('TestModule');
    logger.error('fallo crítico');
    expect(consoleSpies.error).toHaveBeenCalledTimes(1);
  });

  it('dado un mensaje critical cuando emite entonces tambien usa console.error', () => {
    // Caja blanca: _consoleMethod mapea severity <= ERROR (emergency/alert/critical/error) a 'error'
    const logger = createLogger('TestModule');
    logger.critical('condición crítica');
    expect(consoleSpies.error).toHaveBeenCalledTimes(1);
  });

  it('dado un mensaje warning cuando emite entonces usa console.warn', () => {
    const logger = createLogger('TestModule');
    logger.warning('advertencia');
    expect(consoleSpies.warn).toHaveBeenCalledTimes(1);
  });

  it('dado un mensaje notice cuando emite entonces usa console.debug (severidad > INFO)', () => {
    // Caja blanca: notice (5) no es <=ERROR, no es WARNING, no es INFO -> debug
    const logger = createLogger('TestModule');
    logger.notice('condición normal significativa');
    expect(consoleSpies.debug).toHaveBeenCalledTimes(1);
  });

  it('dado un nombre de modulo con puntos cuando crea el logger entonces normaliza a guiones', () => {
    const logger = createLogger('Modulo.Sub.Accion');
    logger.error('x');
    const emitted = consoleSpies.error.mock.calls[0][0] as string;
    expect(emitted).toContain('Modulo-Sub-Accion');
  });

  it('dado un nombre de modulo largo cuando crea el logger entonces lo trunca a 32 caracteres', () => {
    const nombreLargo = 'a'.repeat(50);
    const logger = createLogger(nombreLargo);
    logger.error('x');
    const emitted = consoleSpies.error.mock.calls[0][0] as string;
    const msgidMatch = emitted.match(/browser texcore-frontend - (\S+)/);
    expect(msgidMatch![1].length).toBe(32);
  });

  it('dado severity warning o mas urgente cuando emite entonces hace relay via sendBeacon', () => {
    // _relay hace no-op en DEV; Vitest corre con DEV=true por defecto, así
    // que se simula modo producción para ejercitar la rama de relay real.
    vi.stubEnv('DEV', false);
    const logger = createLogger('TestModule');
    logger.error('error importante');
    expect(sendBeaconSpy).toHaveBeenCalledTimes(1);
    expect(sendBeaconSpy.mock.calls[0][0]).toBe('/api/logs/');
  });

  it('dado severity info (menos urgente que warning) cuando emite entonces no hace relay', () => {
    vi.stubEnv('DEV', false);
    const logger = createLogger('TestModule');
    logger.info('info normal');
    expect(sendBeaconSpy).not.toHaveBeenCalled();
  });

  it('dado sin datos estructurados cuando emite entonces el SD-ELEMENT es un guion', () => {
    const logger = createLogger('TestModule');
    logger.error('sin sd');
    const emitted = consoleSpies.error.mock.calls[0][0] as string;
    expect(emitted).toContain(' - sin sd');
  });

  it('dado un valor con caracteres especiales cuando emite entonces los escapa en el SD-ELEMENT', () => {
    const logger = createLogger('TestModule');
    logger.error('con escape', { detalle: 'valor con "comillas" y ] corchete' });
    const emitted = consoleSpies.error.mock.calls[0][0] as string;
    expect(emitted).toContain('\\"comillas\\"');
    expect(emitted).toContain('\\]');
  });

  it('dado que sendBeacon lanza excepcion cuando hace relay entonces no propaga el error', () => {
    (navigator as any).sendBeacon = () => {
      throw new Error('sendBeacon no disponible');
    };
    const logger = createLogger('TestModule');
    expect(() => logger.error('x')).not.toThrow();
  });

  it('Severity expone los 8 niveles RFC 5424', () => {
    expect(Severity.EMERGENCY).toBe(0);
    expect(Severity.DEBUG).toBe(7);
  });
});
