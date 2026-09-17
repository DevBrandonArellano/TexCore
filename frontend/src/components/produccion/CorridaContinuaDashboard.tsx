import React, { useEffect, useState, useMemo } from 'react';
import apiClient from '../../lib/axios';
import {
  Area,
  Bodega,
  CorridaProduccion,
  Maquina,
  OperacionProduccion,
  Producto,
} from '../../lib/types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Play,
  Pause,
  Square,
  Scale,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Package,
  Layers,
  Printer,
  Search,
} from 'lucide-react';
import { toast } from 'sonner';

export function CorridaContinuaDashboard() {
  const [corridas, setCorridas] = useState<CorridaProduccion[]>([]);
  const [corridaActiva, setCorridaActiva] = useState<CorridaProduccion | null>(null);
  const [operaciones, setOperaciones] = useState<OperacionProduccion[]>([]);

  // Catálogos
  const [areas, setAreas] = useState<Area[]>([]);
  const [maquinas, setMaquinas] = useState<Maquina[]>([]);
  const [bodegas, setBodegas] = useState<Bodega[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Modales
  const [modalIniciar, setModalIniciar] = useState(false);
  const [modalRevertir, setModalRevertir] = useState(false);
  const [operacionARevertir, setOperacionARevertir] = useState<OperacionProduccion | null>(null);
  const [motivoReversion, setMotivoReversion] = useState('');

  // Formulario Iniciar Corrida
  const [nuevaCorridaForm, setNuevaCorridaForm] = useState({
    area_id: '',
    maquina_principal_id: '',
    turno: 'Mañana',
    observaciones: '',
  });

  // Formulario Registro Rápido de Operación (Pesaje Continuo)
  const [formOp, setFormOp] = useState({
    maquina_id: '',
    producto_entrada_id: '',
    bodega_origen_id: '',
    lote_origen_id: '',
    cantidad_consumida: '',
    producto_salida_id: '',
    bodega_destino_id: '',
    cantidad_neta: '',
    codigo_lote: '',
    clasificacion_calidad: 'primera',
    cantidad_metros: '',
    peso_merma: '0',
    tipo_merma: 'maquina',
    observaciones: '',
  });

  useEffect(() => {
    cargarCatalogos();
    cargarCorridas();
  }, []);

  useEffect(() => {
    if (corridaActiva) {
      cargarOperaciones(corridaActiva.id);
      setFormOp((prev) => ({
        ...prev,
        maquina_id: corridaActiva.maquina_principal ? String(corridaActiva.maquina_principal) : prev.maquina_id,
      }));
    } else {
      setOperaciones([]);
    }
  }, [corridaActiva]);

  const cargarCatalogos = async () => {
    try {
      const [resAreas, resMaquinas, resBodegas, resProductos] = await Promise.all([
        apiClient.get('/areas/'),
        apiClient.get('/maquinas/'),
        apiClient.get('/bodegas/'),
        apiClient.get('/productos/'),
      ]);
      setAreas(resAreas.data?.results || resAreas.data || []);
      setMaquinas(resMaquinas.data?.results || resMaquinas.data || []);
      setBodegas(resBodegas.data?.results || resBodegas.data || []);
      setProductos(resProductos.data?.results || resProductos.data || []);
    } catch (e) {
      console.error(e);
      toast.error('Error al cargar catálogos base');
    }
  };

  const cargarCorridas = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/corridas-produccion/?modalidad=CONTINUA');
      const lista: CorridaProduccion[] = res.data?.results || res.data || [];
      setCorridas(lista);
      // Seleccionar por defecto la primera corrida 'en_proceso' o 'pausada'
      const activa = lista.find((c) => c.estado === 'en_proceso' || c.estado === 'pausada');
      if (activa) {
        setCorridaActiva(activa);
      } else if (lista.length > 0 && !corridaActiva) {
        setCorridaActiva(lista[0]);
      }
    } catch (e) {
      console.error(e);
      toast.error('Error al cargar corridas de producción');
    } finally {
      setLoading(false);
    }
  };

  const cargarOperaciones = async (corridaId: number) => {
    try {
      const res = await apiClient.get(`/operaciones-produccion/?corrida=${corridaId}`);
      setOperaciones(res.data?.results || res.data || []);
    } catch (e) {
      console.error(e);
      toast.error('Error al cargar operaciones');
    }
  };

  // Balance de Masa en tiempo real
  const calculoBalance = useMemo(() => {
    const entrada = parseFloat(formOp.cantidad_consumida) || 0;
    const salida = parseFloat(formOp.cantidad_neta) || 0;
    const merma = parseFloat(formOp.peso_merma) || 0;
    const salidasYMermas = salida + merma;
    const diferencia = Math.abs(entrada - salidasYMermas);
    const balanceOk = entrada > 0 && diferencia <= 0.05;
    return {
      entrada,
      salida,
      merma,
      salidasYMermas,
      diferencia,
      balanceOk,
    };
  }, [formOp.cantidad_consumida, formOp.cantidad_neta, formOp.peso_merma]);

  const handleIniciarCorrida = async () => {
    if (!nuevaCorridaForm.area_id) {
      toast.error('Seleccione un área productiva.');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        area_id: parseInt(nuevaCorridaForm.area_id),
        maquina_principal_id: nuevaCorridaForm.maquina_principal_id ? parseInt(nuevaCorridaForm.maquina_principal_id) : null,
        modalidad: 'CONTINUA',
        turno: nuevaCorridaForm.turno,
        observaciones: nuevaCorridaForm.observaciones,
      };
      const res = await apiClient.post('/corridas-produccion/iniciar-corrida/', payload);
      toast.success(`Corrida ${res.data.codigo} iniciada exitosamente`);
      setModalIniciar(false);
      setCorridaActiva(res.data);
      cargarCorridas();
    } catch (e: any) {
      console.error(e);
      toast.error(e.response?.data?.error || 'Error al iniciar corrida');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePausarReanudar = async () => {
    if (!corridaActiva) return;
    try {
      const res = await apiClient.post(`/corridas-produccion/${corridaActiva.id}/pausar/`);
      setCorridaActiva(res.data);
      toast.success(`Corrida ${res.data.codigo} ahora está ${res.data.estado}`);
      cargarCorridas();
    } catch (e: any) {
      toast.error(e.response?.data?.error || 'Error al cambiar estado de la corrida');
    }
  };

  const handleFinalizarCorrida = async () => {
    if (!corridaActiva) return;
    if (!confirm(`¿Está seguro de cerrar formalmente la corrida ${corridaActiva.codigo}?`)) return;
    try {
      const res = await apiClient.post(`/corridas-produccion/${corridaActiva.id}/finalizar-corrida/`);
      setCorridaActiva(res.data);
      toast.success(`Corrida ${res.data.codigo} finalizada correctamente`);
      cargarCorridas();
    } catch (e: any) {
      toast.error(e.response?.data?.error || 'Error al finalizar corrida');
    }
  };

  const handleRegistrarOperacion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!corridaActiva) {
      toast.error('No hay una corrida activa seleccionada.');
      return;
    }
    if (corridaActiva.estado !== 'en_proceso') {
      toast.error(`La corrida está en estado '${corridaActiva.estado}'. Debe estar 'en_proceso' para registrar operaciones.`);
      return;
    }
    if (!formOp.producto_entrada_id || !formOp.bodega_origen_id || !formOp.cantidad_consumida) {
      toast.error('Complete los datos del insumo consumido.');
      return;
    }
    if (!formOp.producto_salida_id || !formOp.bodega_destino_id || !formOp.cantidad_neta) {
      toast.error('Complete los datos del producto transformado.');
      return;
    }
    if (!calculoBalance.balanceOk) {
      toast.error(`Desbalance de masa detectado: Entrada (${calculoBalance.entrada} kg) vs Salida+Merma (${calculoBalance.salidasYMermas} kg). Tolerancia máx: 0.050 kg`);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        maquina_id: formOp.maquina_id ? parseInt(formOp.maquina_id) : corridaActiva.maquina_principal,
        observaciones: formOp.observaciones,
        consumos: [{
          producto_id: parseInt(formOp.producto_entrada_id),
          bodega_origen_id: parseInt(formOp.bodega_origen_id),
          lote_origen_id: formOp.lote_origen_id ? parseInt(formOp.lote_origen_id) : null,
          cantidad_consumida: formOp.cantidad_consumida,
        }],
        salidas: [{
          producto_id: parseInt(formOp.producto_salida_id),
          bodega_destino_id: parseInt(formOp.bodega_destino_id),
          cantidad_neta: formOp.cantidad_neta,
          codigo_lote: formOp.codigo_lote || undefined,
          clasificacion_calidad: formOp.clasificacion_calidad,
          cantidad_metros: formOp.cantidad_metros || undefined,
        }],
        mermas: parseFloat(formOp.peso_merma) > 0 ? [{
          peso_merma: formOp.peso_merma,
          tipo_merma: formOp.tipo_merma,
        }] : [],
      };

      const res = await apiClient.post(
        `/corridas-produccion/${corridaActiva.id}/registrar-operacion/`,
        payload
      );

      toast.success(`Operación #${res.data.numero_secuencia} registrada exitosamente.`);

      // Resetear inputs de pesaje manteniendo bodegas sugeridas
      setFormOp((prev) => ({
        ...prev,
        cantidad_consumida: '',
        cantidad_neta: '',
        codigo_lote: '',
        cantidad_metros: '',
        peso_merma: '0',
        observaciones: '',
      }));

      cargarOperaciones(corridaActiva.id);
      cargarCorridas();
    } catch (e: any) {
      console.error(e);
      const msg = e.response?.data?.error || 'Error al registrar operación';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmarReversion = async () => {
    if (!corridaActiva || !operacionARevertir) return;
    if (!motivoReversion.trim()) {
      toast.error('Debe ingresar una justificación detallada para la reversión.');
      return;
    }
    setSubmitting(true);
    try {
      await apiClient.post(
        `/corridas-produccion/${corridaActiva.id}/revertir-operacion/`,
        {
          operacion_id: operacionARevertir.id,
          justificacion: motivoReversion.trim(),
        }
      );
      toast.success(`Operación #${operacionARevertir.numero_secuencia} revertida y saldos restaurados.`);
      setModalRevertir(false);
      setOperacionARevertir(null);
      setMotivoReversion('');
      cargarOperaciones(corridaActiva.id);
      cargarCorridas();
    } catch (e: any) {
      const msg = e.response?.data?.error || 'Error al revertir operación';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Encabezado Principal */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-card border rounded-xl p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">Producción Continua (MES)</h1>
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
              Modalidad Continua
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Gestión de turnos de planta, pesaje continuo de transformaciones y balance de masa en máquina.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setModalIniciar(true)}
            className="bg-primary hover:bg-primary/90 gap-2"
          >
            <Play className="h-4 w-4" />
            Nueva Corrida
          </Button>
        </div>
      </div>

      {/* Selector y Estado de Corrida Activa */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                Corrida Actual: {corridaActiva ? corridaActiva.codigo : 'Ninguna seleccionada'}
              </CardTitle>
              <CardDescription>
                {corridaActiva
                  ? `${corridaActiva.area_nombre} | Turno ${corridaActiva.turno} | Máquina: ${corridaActiva.maquina_principal_nombre || 'Múltiples'}`
                  : 'Seleccione o inicie una corrida de producción para operar.'}
              </CardDescription>
            </div>
            {corridaActiva && (
              <div className="flex items-center gap-2">
                <Badge
                  className={
                    corridaActiva.estado === 'en_proceso'
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : corridaActiva.estado === 'pausada'
                      ? 'bg-amber-100 text-amber-800 border-amber-300'
                      : 'bg-gray-100 text-gray-800'
                  }
                >
                  {corridaActiva.estado.toUpperCase()}
                </Badge>
                {corridaActiva.estado !== 'finalizada' && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePausarReanudar}
                      className="gap-1"
                    >
                      {corridaActiva.estado === 'en_proceso' ? (
                        <>
                          <Pause className="h-3.5 w-3.5" /> Pausar
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5" /> Reanudar
                        </>
                      )}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={handleFinalizarCorrida}
                      className="gap-1"
                    >
                      <Square className="h-3.5 w-3.5" /> Finalizar
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        </CardHeader>
        {corridas.length > 1 && (
          <CardContent className="pt-0">
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              <span className="text-xs text-muted-foreground whitespace-nowrap">Otras corridas:</span>
              {corridas.map((c) => (
                <Button
                  key={c.id}
                  variant={corridaActiva?.id === c.id ? 'secondary' : 'ghost'}
                  size="sm"
                  className="text-xs h-7"
                  onClick={() => setCorridaActiva(c)}
                >
                  {c.codigo} ({c.estado})
                </Button>
              ))}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Formulario de Pesaje Rápido en Máquina */}
      {corridaActiva && corridaActiva.estado !== 'finalizada' && (
        <Card className="border-primary/30 shadow-md">
          <CardHeader className="bg-muted/30 pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Scale className="h-4 w-4 text-primary" />
                Registro Rápido de Transformación y Pesaje
              </CardTitle>
              {/* Semáforo de Balance de Masa */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Balance de Masa:</span>
                <Badge
                  className={
                    calculoBalance.entrada === 0
                      ? 'bg-gray-100 text-gray-700'
                      : calculoBalance.balanceOk
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-red-100 text-red-800'
                  }
                >
                  {calculoBalance.entrada === 0
                    ? 'Esperando pesaje'
                    : calculoBalance.balanceOk
                    ? `Balance OK (Δ ${calculoBalance.diferencia.toFixed(3)} kg)`
                    : `Desbalance: Δ ${calculoBalance.diferencia.toFixed(3)} kg`}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-4">
            <form onSubmit={handleRegistrarOperacion} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Lado Izquierdo: Consumo de Insumo */}
                <div className="space-y-3 p-4 bg-muted/20 border rounded-lg">
                  <div className="flex items-center justify-between border-b pb-2">
                    <span className="font-semibold text-sm text-foreground">1. Insumo Consumido (Entrada)</span>
                    <Badge variant="outline" className="text-xs">
                      Origen
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prod_entrada">Producto de Entrada *</Label>
                    <Select
                      value={formOp.producto_entrada_id}
                      onValueChange={(val) => setFormOp({ ...formOp, producto_entrada_id: val })}
                    >
                      <SelectTrigger id="prod_entrada">
                        <SelectValue placeholder="Seleccione producto insumo" />
                      </SelectTrigger>
                      <SelectContent>
                        {productos.map((p) => (
                          <SelectItem key={p.id} value={String(p.id)}>
                            {p.codigo} - {p.descripcion} ({p.tipo})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="bodega_origen">Bodega Origen *</Label>
                      <Select
                        value={formOp.bodega_origen_id}
                        onValueChange={(val) => setFormOp({ ...formOp, bodega_origen_id: val })}
                      >
                        <SelectTrigger id="bodega_origen">
                          <SelectValue placeholder="Bodega" />
                        </SelectTrigger>
                        <SelectContent>
                          {bodegas.map((b) => (
                            <SelectItem key={b.id} value={String(b.id)}>
                              {b.nombre}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cant_consumida">Peso Consumido (kg) *</Label>
                      <Input
                        id="cant_consumida"
                        type="number"
                        step="0.001"
                        min="0.001"
                        placeholder="Ej. 150.000"
                        value={formOp.cantidad_consumida}
                        onChange={(e) => setFormOp({ ...formOp, cantidad_consumida: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Lado Derecho: Producto Resultante */}
                <div className="space-y-3 p-4 bg-muted/20 border rounded-lg">
                  <div className="flex items-center justify-between border-b pb-2">
                    <span className="font-semibold text-sm text-foreground">2. Producto Generado (Salida)</span>
                    <Badge variant="outline" className="text-xs">
                      Destino
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="prod_salida">Producto Resultante *</Label>
                    <Select
                      value={formOp.producto_salida_id}
                      onValueChange={(val) => setFormOp({ ...formOp, producto_salida_id: val })}
                    >
                      <SelectTrigger id="prod_salida">
                        <SelectValue placeholder="Seleccione producto generado" />
                      </SelectTrigger>
                      <SelectContent>
                        {productos.map((p) => (
                          <SelectItem key={p.id} value={String(p.id)}>
                            {p.codigo} - {p.descripcion}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="bodega_destino">Bodega Destino *</Label>
                      <Select
                        value={formOp.bodega_destino_id}
                        onValueChange={(val) => setFormOp({ ...formOp, bodega_destino_id: val })}
                      >
                        <SelectTrigger id="bodega_destino">
                          <SelectValue placeholder="Bodega" />
                        </SelectTrigger>
                        <SelectContent>
                          {bodegas.map((b) => (
                            <SelectItem key={b.id} value={String(b.id)}>
                              {b.nombre}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cant_neta">Peso Neto Producido (kg) *</Label>
                      <Input
                        id="cant_neta"
                        type="number"
                        step="0.001"
                        min="0.001"
                        placeholder="Ej. 142.500"
                        value={formOp.cantidad_neta}
                        onChange={(e) => setFormOp({ ...formOp, cantidad_neta: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Fila Inferior: Calidad, Mermas y Metros */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-muted/10 p-3 rounded-lg border">
                <div className="space-y-1">
                  <Label htmlFor="calidad">Calidad</Label>
                  <Select
                    value={formOp.clasificacion_calidad}
                    onValueChange={(val) => setFormOp({ ...formOp, clasificacion_calidad: val })}
                  >
                    <SelectTrigger id="calidad">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="primera">Primera Calidad</SelectItem>
                      <SelectItem value="segunda">Segunda Calidad</SelectItem>
                      <SelectItem value="saldo">Saldo / Retazo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="merma">Merma / Desperdicio (kg)</Label>
                  <Input
                    id="merma"
                    type="number"
                    step="0.001"
                    min="0"
                    value={formOp.peso_merma}
                    onChange={(e) => setFormOp({ ...formOp, peso_merma: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="tipo_merma">Tipo de Merma</Label>
                  <Select
                    value={formOp.tipo_merma}
                    onValueChange={(val) => setFormOp({ ...formOp, tipo_merma: val })}
                  >
                    <SelectTrigger id="tipo_merma">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="maquina">Falla de Máquina</SelectItem>
                      <SelectItem value="material">Defecto de Material</SelectItem>
                      <SelectItem value="setup">Setup / Arranque</SelectItem>
                      <SelectItem value="corte">Corte / Empalme</SelectItem>
                      <SelectItem value="humedad">Pérdida Humedad</SelectItem>
                      <SelectItem value="otro">Otro</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="metros">Metros (Opcional Telas)</Label>
                  <Input
                    id="metros"
                    type="number"
                    step="0.0001"
                    placeholder="Ej. 420.5000"
                    value={formOp.cantidad_metros}
                    onChange={(e) => setFormOp({ ...formOp, cantidad_metros: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="submit"
                  disabled={submitting || !calculoBalance.balanceOk}
                  className="bg-primary hover:bg-primary/90 gap-2 px-6"
                >
                  <Printer className="h-4 w-4" />
                  Confirmar Transformación y Generar Etiqueta
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Historial de Operaciones de la Corrida */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center justify-between">
            <span>Operaciones de la Corrida ({operaciones.length})</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => corridaActiva && cargarOperaciones(corridaActiva.id)}
              className="h-8 gap-1"
            >
              Actualizar
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {operaciones.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No hay operaciones registradas aún en esta corrida.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="py-2 px-3">#</th>
                    <th className="py-2 px-3">Máquina</th>
                    <th className="py-2 px-3">Operario</th>
                    <th className="py-2 px-3">Hora</th>
                    <th className="py-2 px-3">Insumos</th>
                    <th className="py-2 px-3">Lote Salida</th>
                    <th className="py-2 px-3">Neto</th>
                    <th className="py-2 px-3">Merma</th>
                    <th className="py-2 px-3">Estado</th>
                    <th className="py-2 px-3 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {operaciones.map((op) => (
                    <tr key={op.id} className="border-b hover:bg-muted/20">
                      <td className="py-2 px-3 font-semibold">{op.numero_secuencia}</td>
                      <td className="py-2 px-3">{op.maquina_nombre || 'N/A'}</td>
                      <td className="py-2 px-3">{op.operario_nombre || 'N/A'}</td>
                      <td className="py-2 px-3 text-xs text-muted-foreground">
                        {new Date(op.hora_inicio).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-2 px-3">
                        {op.consumos.map((c) => (
                          <div key={c.id} className="text-xs">
                            {c.cantidad_consumida} kg de {c.producto_codigo}
                          </div>
                        ))}
                      </td>
                      <td className="py-2 px-3">
                        {op.salidas.map((s) => (
                          <div key={s.id} className="font-mono text-xs font-semibold text-primary">
                            {s.lote_generado_codigo}
                          </div>
                        ))}
                      </td>
                      <td className="py-2 px-3 font-semibold">
                        {op.salidas.reduce((acc, s) => acc + parseFloat(String(s.cantidad_neta)), 0).toFixed(3)} kg
                      </td>
                      <td className="py-2 px-3 text-xs text-amber-700">
                        {op.mermas.reduce((acc, m) => acc + parseFloat(String(m.peso_merma)), 0).toFixed(3)} kg
                      </td>
                      <td className="py-2 px-3">
                        <Badge
                          variant="outline"
                          className={
                            op.estado === 'completada'
                              ? 'border-emerald-300 text-emerald-700 bg-emerald-50'
                              : op.estado === 'revertida'
                              ? 'border-red-300 text-red-700 bg-red-50'
                              : 'border-blue-300 text-blue-700 bg-blue-50'
                          }
                        >
                          {op.estado}
                        </Badge>
                      </td>
                      <td className="py-2 px-3 text-right">
                        {op.estado === 'completada' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setOperacionARevertir(op);
                              setModalRevertir(true);
                            }}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50 h-7 text-xs gap-1"
                          >
                            <RotateCcw className="h-3 w-3" /> Revertir
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal Iniciar Corrida */}
      <Dialog open={modalIniciar} onOpenChange={setModalIniciar}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Iniciar Corrida de Producción</DialogTitle>
            <DialogDescription>
              Abre un turno o jornada continua de transformación en planta.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label htmlFor="area">Área Productiva *</Label>
              <Select
                value={nuevaCorridaForm.area_id}
                onValueChange={(val) => setNuevaCorridaForm({ ...nuevaCorridaForm, area_id: val })}
              >
                <SelectTrigger id="area">
                  <SelectValue placeholder="Seleccione área" />
                </SelectTrigger>
                <SelectContent>
                  {areas.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      {a.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="maquina_p">Máquina Principal (Opcional)</Label>
              <Select
                value={nuevaCorridaForm.maquina_principal_id}
                onValueChange={(val) => setNuevaCorridaForm({ ...nuevaCorridaForm, maquina_principal_id: val })}
              >
                <SelectTrigger id="maquina_p">
                  <SelectValue placeholder="Seleccione máquina" />
                </SelectTrigger>
                <SelectContent>
                  {maquinas.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="turno">Turno</Label>
              <Select
                value={nuevaCorridaForm.turno}
                onValueChange={(val) => setNuevaCorridaForm({ ...nuevaCorridaForm, turno: val })}
              >
                <SelectTrigger id="turno">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Mañana">Mañana (06:00 - 14:00)</SelectItem>
                  <SelectItem value="Tarde">Tarde (14:00 - 22:00)</SelectItem>
                  <SelectItem value="Noche">Noche (22:00 - 06:00)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="obs_corrida">Observaciones</Label>
              <Textarea
                id="obs_corrida"
                placeholder="Detalles sobre arranque, materia prima o condiciones de turno..."
                value={nuevaCorridaForm.observaciones}
                onChange={(e) => setNuevaCorridaForm({ ...nuevaCorridaForm, observaciones: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalIniciar(false)}>
              Cancelar
            </Button>
            <Button onClick={handleIniciarCorrida} disabled={submitting}>
              Iniciar Corrida
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Revertir Operación */}
      <Dialog open={modalRevertir} onOpenChange={setModalRevertir}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Revertir Operación #{operacionARevertir?.numero_secuencia}
            </DialogTitle>
            <DialogDescription>
              Esta acción descontará los lotes generados y devolverá las materias primas consumidas a
              sus bodegas de origen. Se requiere justificación de auditoría obligatoria.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="justificacion_rev">Motivo de la Reversión *</Label>
            <Textarea
              id="justificacion_rev"
              rows={3}
              placeholder="Describa el error de pesaje, rotura de hilo o falla que motiva la anulación..."
              value={motivoReversion}
              onChange={(e) => setMotivoReversion(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalRevertir(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmarReversion}
              disabled={submitting || !motivoReversion.trim()}
            >
              Confirmar Reversión
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
