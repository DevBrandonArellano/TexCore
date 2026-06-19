import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area, Bodega } from '../../lib/types';
import { Factory, Pencil, Trash2, ChevronLeft, ChevronRight, MoreHorizontal, PlusCircle, Calendar, MessageSquare, Monitor, ClipboardList, Play, CheckCircle2 } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../ui/dialog';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from '../ui/sheet';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';
import { Separator } from '../ui/separator';
import { Progress } from '../ui/progress';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';
import apiClient from '../../lib/axios';

interface ManageOrdenesProduccionProps {
  ordenes: OrdenProduccion[];
  productos: Producto[];
  formulas: FormulaColor[];
  sedes: Sede[];
  maquinas: Maquina[];
  areas: Area[];
  bodegas: Bodega[];
  onOrdenCreate: (data: any) => Promise<boolean>;
  onOrdenUpdate: (id: number, data: any) => Promise<boolean>;
  onOrderStatusChange?: (id: number, newStatus: string) => Promise<boolean>;
  onOrdenDelete: (id: number) => void;
  loading: boolean;
  onDataRefresh: () => void;
}

const ITEMS_PER_PAGE = 20;

function RequisitosMaterialesDialog({ open, onOpenChange, orden }: { open: boolean, onOpenChange: (open: boolean) => void, orden: OrdenProduccion | null }) {
  const [loading, setLoading] = useState(false);
  const [requisitos, setRequisitos] = useState<any>(null);

  useEffect(() => {
    if (open && orden) {
      const fetchRequisitos = async () => {
        setLoading(true);
        try {
          const response = await apiClient.get(`/ordenes-produccion/${orden.id}/requisitos_materiales/`);
          setRequisitos(response.data);
        } catch (error) {
          toast.error("Error al cargar los requisitos de materiales.");
        } finally {
          setLoading(false);
        }
      };
      fetchRequisitos();
    }
  }, [open, orden]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Requisitos de Materiales para OP: {orden?.codigo}</DialogTitle>
          <DialogDescription>
            Cálculo detallado de insumos basados en la fórmula y peso requerido.
          </DialogDescription>
        </DialogHeader>
        {loading ? (
          <div className="space-y-4 py-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : requisitos ? (
          <div className="space-y-6 py-4">
            <div className="grid grid-cols-2 gap-4">
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Peso Requerido</div>
                  <div className="text-2xl font-bold">{requisitos.peso_total_op} Kg</div>
                </CardContent>
              </Card>
              <Card className="bg-slate-50 border-none">
                <CardContent className="pt-6">
                  <div className="text-sm text-muted-foreground">Total Insumos</div>
                  <div className="text-2xl font-bold">{requisitos.requisitos.length}</div>
                </CardContent>
              </Card>
            </div>

            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead>Producto</TableHead>
                    <TableHead>Tipo</TableHead>
                    <TableHead className="text-right">Cantidad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requisitos.requisitos.map((req: any, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{req.producto_nombre}</TableCell>
                      <TableCell>
                        <Badge variant={req.es_base ? "default" : "secondary"}>
                          {req.tipo === 'quimico' ? '🧪 Químico' : '🧶 Materia Prima'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {req.cantidad_requerida} {req.unidad}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RegistrarLoteDialog({ open, onOpenChange, orden, maquinas, onLotCreated }: { open: boolean, onOpenChange: (open: boolean) => void, orden: OrdenProduccion | null, maquinas: Maquina[], onLotCreated: () => void }) {
  const [formData, setFormData] = useState({ codigo_lote: '', peso_neto_producido: '', maquina: '', turno: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (orden) {
      setFormData({
        codigo_lote: '',
        peso_neto_producido: '',
        maquina: orden.maquina_asignada?.toString() || '',
        turno: ''
      });
    }
  }, [orden]);

  if (!orden) return null;

  const handleSubmit = async () => {
    if (!formData.codigo_lote || !formData.peso_neto_producido) {
      toast.error("El código del lote y el peso producido son requeridos.");
      return;
    }
    setIsSubmitting(true);
    const now = new Date().toISOString();
    try {
      await apiClient.post(`/ordenes-produccion/${orden.id}/registrar-lote/`, {
        ...formData,
        hora_final: now,
        hora_inicio: now, // Simplificado: inicio = ahora si se registra al empaquetar
      });
      toast.success("Lote de producción registrado exitosamente.");
      onLotCreated();
      onOpenChange(false);
    } catch (error: any) {
      const errorMsg = error.response?.data?.error || "Ocurrió un error al registrar el lote.";
      toast.error("Error", { description: errorMsg });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Registrar Lote para OP: {orden.codigo}</DialogTitle>
          <DialogDescription>
            Producto: {orden.producto_nombre}. Complete los detalles del lote producido.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="codigo_lote">Código de Lote</Label>
            <Input id="codigo_lote" value={formData.codigo_lote} onChange={e => setFormData(f => ({ ...f, codigo_lote: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="peso_neto_producido">Peso Neto Producido (Kg)</Label>
            <Input id="peso_neto_producido" type="number" value={formData.peso_neto_producido} onChange={e => setFormData(f => ({ ...f, peso_neto_producido: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="maquina">Máquina</Label>
            <Select value={formData.maquina} onValueChange={v => setFormData(f => ({ ...f, maquina: v }))}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona una máquina" />
              </SelectTrigger>
              <SelectContent>
                {maquinas.map(m => (
                  <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="turno">Turno</Label>
            <Select value={formData.turno} onValueChange={v => setFormData(f => ({ ...f, turno: v }))}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona un turno" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Mañana">Mañana</SelectItem>
                <SelectItem value="Tarde">Tarde</SelectItem>
                <SelectItem value="Noche">Noche</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Registrando..." : "Registrar Lote"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface OrdenDetalleSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orden: OrdenProduccion | null;
  onEdit: (orden: OrdenProduccion) => void;
  onDelete: (id: number) => void;
  onStatusChange: (id: number, newStatus: 'en_proceso' | 'finalizada') => void;
  onOpenLotDialog: (orden: OrdenProduccion) => void;
  onOpenRequisitosDialog: (orden: OrdenProduccion) => void;
  sedes: Sede[];
  areas: Area[];
  bodegas: Bodega[];
  formulas: FormulaColor[];
}

function OrdenDetalleSheet({
  open,
  onOpenChange,
  orden,
  onEdit,
  onDelete,
  onStatusChange,
  onOpenLotDialog,
  onOpenRequisitosDialog,
  sedes,
  areas,
  bodegas,
  formulas,
}: OrdenDetalleSheetProps) {
  if (!orden) return null;

  const today = new Date().toISOString().split('T')[0];
  const isOverdue = orden.estado !== 'finalizada' && orden.fecha_fin_planificada && orden.fecha_fin_planificada < today;
  const isToday = orden.estado !== 'finalizada' && orden.fecha_fin_planificada === today;
  const pesoProd = Number(orden.peso_producido || 0);
  const pesoReq = Number(orden.peso_neto_requerido || 0);
  const porcentaje = pesoReq > 0 ? Math.min(100, Math.round((pesoProd / pesoReq) * 100)) : 0;

  // Resolver nombres desde catálogos (la API solo devuelve IDs para estos campos)
  const ordenAny = orden as any;
  const productoNombre = ordenAny.producto_entrada_detail?.descripcion || orden.producto_nombre;
  const formulaNombre = formulas.find(f => f.id === orden.formula_color)?.nombre_color;
  const sedeNombre = sedes.find(s => s.id === orden.sede)?.nombre;
  const areaNombre = areas.find(a => a.id === orden.area)?.nombre;
  const bodegaEntradaNombre = bodegas.find(b => b.id === ordenAny.bodega_entrada)?.nombre;
  const bodegaQuimicosNombre = bodegas.find(b => b.id === orden.bodega_quimicos)?.nombre;

  const estadoBadge = () => {
    if (orden.estado === 'pendiente') return <Badge variant="secondary" className="bg-slate-100 text-slate-600 border-slate-200">Pendiente</Badge>;
    if (orden.estado === 'en_proceso') return <Badge variant="secondary" className="bg-blue-50 text-blue-600 border-blue-200">En Proceso</Badge>;
    return <Badge variant="secondary" className="bg-emerald-50 text-emerald-600 border-emerald-200">Finalizada</Badge>;
  };

  const prioridadBadge = () => {
    if (orden.prioridad === 'baja') return <Badge variant="secondary" className="bg-slate-100 text-slate-600">Baja</Badge>;
    if (orden.prioridad === 'normal') return <Badge variant="secondary" className="bg-blue-50 text-blue-600">Normal</Badge>;
    if (orden.prioridad === 'alta') return <Badge variant="secondary" className="bg-orange-50 text-orange-600 border-orange-200">Alta</Badge>;
    if (orden.prioridad === 'urgente') return <Badge variant="secondary" className="bg-red-50 text-red-600 border-red-200 font-bold">Urgente</Badge>;
    return null;
  };

  const DetailRow = ({ label, value }: { label: string; value?: string | null }) => (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value || <span className="text-muted-foreground italic">—</span>}</span>
    </div>
  );

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto flex flex-col gap-0 p-0">
        <SheetHeader className="p-6 pb-4 border-b">
          <div className="flex items-center gap-2 flex-wrap">
            <SheetTitle className="font-mono text-lg">{orden.codigo}</SheetTitle>
            {estadoBadge()}
            {prioridadBadge()}
            {isOverdue && <Badge variant="destructive" className="text-xs">Vencida</Badge>}
            {isToday && !isOverdue && <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-xs">Vence hoy</Badge>}
          </div>
          <SheetDescription>Detalle completo de la orden de producción</SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* General */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Información General</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Producto" value={productoNombre} />
              <DetailRow label="Fórmula Color" value={formulaNombre} />
              <DetailRow label="Sede" value={sedeNombre} />
              <DetailRow label="Área Responsable" value={areaNombre} />
            </div>
          </div>

          <Separator />

          {/* Progreso */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Progreso de Producción</h3>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">{pesoProd} / {pesoReq} Kg</span>
                <span className="font-semibold">{porcentaje}%</span>
              </div>
              <Progress value={porcentaje} className="h-2" />
            </div>
            {orden.inventario_descontado && (
              <Badge className="bg-green-100 text-green-800 border-green-200 w-fit">✓ Químicos descontados</Badge>
            )}
          </div>

          <Separator />

          {/* Fechas */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Fechas</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Inicio Planificado" value={orden.fecha_inicio_planificada || undefined} />
              <div className="flex flex-col gap-0.5">
                <span className="text-xs text-muted-foreground">Fin Planificado</span>
                <span className={`text-sm font-medium ${isOverdue ? 'text-red-600' : isToday ? 'text-amber-600' : ''}`}>
                  {orden.fecha_fin_planificada || <span className="text-muted-foreground italic">—</span>}
                </span>
              </div>
              <DetailRow label="Fecha de Creación" value={orden.fecha_creacion ? orden.fecha_creacion.split('T')[0] : undefined} />
            </div>
          </div>

          <Separator />

          {/* Almacén */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Almacén</h3>
            <div className="grid grid-cols-2 gap-3">
              <DetailRow label="Bodega Entrada" value={bodegaEntradaNombre} />
              <DetailRow label="Bodega Químicos" value={bodegaQuimicosNombre} />
            </div>
          </div>

          {(orden.observaciones || orden.justificacion) && (
            <>
              <Separator />
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Notas</h3>
                {orden.observaciones && (
                  <div className="rounded-md bg-muted px-3 py-2 text-sm">{orden.observaciones}</div>
                )}
                {orden.justificacion && (
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs text-muted-foreground">Justificación</span>
                    <div className="rounded-md bg-muted px-3 py-2 text-sm">{orden.justificacion}</div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <SheetFooter className="border-t p-4 flex flex-col gap-2">
          {/* Cambio de estado */}
          {orden.estado === 'pendiente' && (
            <Button
              className="w-full"
              variant="outline"
              onClick={() => onStatusChange(orden.id, 'en_proceso')}
            >
              <Play className="w-4 h-4 mr-2" /> Iniciar Proceso
            </Button>
          )}
          {orden.estado === 'en_proceso' && (
            <Button
              className="w-full"
              variant="outline"
              onClick={() => onStatusChange(orden.id, 'finalizada')}
            >
              <CheckCircle2 className="w-4 h-4 mr-2" /> Marcar como Finalizada
            </Button>
          )}

          {/* Acciones secundarias */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onOpenRequisitosDialog(orden)}
            >
              <ClipboardList className="w-4 h-4 mr-2" /> Requisitos
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              disabled={orden.estado === 'finalizada'}
              onClick={() => onOpenLotDialog(orden)}
            >
              <PlusCircle className="w-4 h-4 mr-2" /> Lote
            </Button>
          </div>

          {/* Editar / Eliminar */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onEdit(orden)}
            >
              <Pencil className="w-4 h-4 mr-2" /> Editar
            </Button>
            <Button
              variant="destructive"
              className="flex-1"
              onClick={() => onDelete(orden.id)}
            >
              <Trash2 className="w-4 h-4 mr-2" /> Eliminar
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

export function ManageOrdenesProduccion({
  ordenes,
  productos,
  formulas,
  sedes,
  maquinas,
  areas: areasProp,
  bodegas,
  onOrdenCreate,
  onOrdenUpdate,
  onOrderStatusChange,
  onOrdenDelete,
  loading,
  onDataRefresh
}: ManageOrdenesProduccionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [areas, setAreas] = useState<Area[]>(areasProp);

  // Sincronizar con actualizaciones del prop padre (ej. refresh del dashboard)
  useEffect(() => {
    if (!isOpen) setAreas(areasProp);
  }, [areasProp]);

  // Cargar todas las áreas al abrir el formulario (sin paginación en el backend)
  useEffect(() => {
    if (isOpen) {
      apiClient.get('/areas/').then(r => {
        const data = Array.isArray(r.data) ? r.data : (r.data as any).results ?? [];
        setAreas(data);
      }).catch(() => {
        // Si falla, se conservan las áreas del prop
      });
    }
  }, [isOpen]);
  const [editingOrden, setEditingOrden] = useState<OrdenProduccion | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    producto_entrada: '',
    bodega_entrada: '',
    producto_salida: '',
    bodega_salida: '',
    formula_color: '',
    peso_neto_requerido: '',
    sede: '',
    area: '',
    bodega_quimicos: '',
    estado: 'pendiente',
    fecha_inicio_planificada: '',
    fecha_fin_planificada: '',
    maquina_asignada: '',
    observaciones: '',
    prioridad: 'normal',
    justificacion: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const statusFilter = searchParams.get('status') || 'all';
  const machineFilter = searchParams.get('maquina') || 'all';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const [isLotDialogOpen, setIsLotDialogOpen] = useState(false);
  const [isRequisitosDialogOpen, setIsRequisitosDialogOpen] = useState(false);
  const [selectedOrdenForLot, setSelectedOrdenForLot] = useState<OrdenProduccion | null>(null);
  const [selectedOrdenForRequisitos, setSelectedOrdenForRequisitos] = useState<OrdenProduccion | null>(null);
  const [selectedOrdenForDetail, setSelectedOrdenForDetail] = useState<OrdenProduccion | null>(null);

  const handleOpenLotDialog = (orden: OrdenProduccion) => {
    setSelectedOrdenForLot(orden);
    setIsLotDialogOpen(true);
  };

  const handleOpenRequisitosDialog = (orden: OrdenProduccion) => {
    setSelectedOrdenForRequisitos(orden);
    setIsRequisitosDialogOpen(true);
  };

  const filteredOrdenes = useMemo(() => {
    return ordenes.filter(o => {
      const matchesSearch = o.codigo.toLowerCase().includes(searchTerm.toLowerCase()) || o.producto_nombre?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || o.estado === statusFilter;
      const matchesMachine = machineFilter === 'all' || o.maquina_asignada?.toString() === machineFilter;
      return matchesSearch && matchesStatus && matchesMachine;
    });
  }, [ordenes, searchTerm, statusFilter, machineFilter]);

  const paginatedOrdenes = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredOrdenes.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredOrdenes, currentPage]);

  const totalPages = Math.max(1, Math.ceil(filteredOrdenes.length / ITEMS_PER_PAGE));

  const resetForm = () => {
    setFormData({
      codigo: '',
      producto_entrada: '',
      bodega_entrada: '',
      producto_salida: '',
      bodega_salida: '',
      formula_color: '',
      peso_neto_requerido: '',
      sede: '',
      area: '',
      bodega_quimicos: '',
      estado: 'pendiente',
      fecha_inicio_planificada: '',
      fecha_fin_planificada: '',
      maquina_asignada: '',
      observaciones: '',
      prioridad: 'normal',
      justificacion: ''
    });
    setErrors({});
    setEditingOrden(null);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
    if (!formData.area) newErrors.area = 'El área es requerida';
    if (!formData.peso_neto_requerido || parseFloat(formData.peso_neto_requerido) <= 0) newErrors.peso_neto_requerido = 'El peso es requerido y debe ser mayor a 0';

    // Al editar, requiere productos y bodegas
    if (editingOrden) {
      if (!formData.producto_entrada) newErrors.producto_entrada = 'El producto de entrada es requerido';
      if (!formData.producto_salida) newErrors.producto_salida = 'El producto de salida es requerido';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    const dataToSend = {
      ...formData,
      producto_entrada: parseInt(formData.producto_entrada),
      bodega_entrada: formData.bodega_entrada ? parseInt(formData.bodega_entrada) : null,
      producto_salida: parseInt(formData.producto_salida),
      bodega_salida: formData.bodega_salida ? parseInt(formData.bodega_salida) : null,
      formula_color: formData.formula_color ? parseInt(formData.formula_color) : null,
      sede: formData.sede ? parseInt(formData.sede) : null,
      area: formData.area ? parseInt(formData.area) : null,
      bodega_quimicos: formData.bodega_quimicos ? parseInt(formData.bodega_quimicos) : null,
      maquina_asignada: (formData.maquina_asignada && formData.maquina_asignada !== '0') ? parseInt(formData.maquina_asignada) : null,
      fecha_inicio_planificada: formData.fecha_inicio_planificada || null,
      fecha_fin_planificada: formData.fecha_fin_planificada || null,
    };

    setIsSubmitting(true);
    let success = false;
    try {
      if (editingOrden) {
        success = await onOrdenUpdate(editingOrden.id, dataToSend);
      } else {
        success = await onOrdenCreate(dataToSend);
      }

      if (success) {
        setIsOpen(false);
        resetForm();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (orden: OrdenProduccion) => {
    setEditingOrden(orden);
    const ordenAny = orden as any;
    setFormData({
      codigo: orden.codigo,
      producto_entrada: (ordenAny.producto_entrada ?? ordenAny.producto ?? '').toString(),
      bodega_entrada: (ordenAny.bodega_entrada ?? '').toString(),
      producto_salida: (ordenAny.producto_salida ?? '').toString(),
      bodega_salida: (ordenAny.bodega_salida ?? '').toString(),
      formula_color: orden.formula_color?.toString() || '',
      peso_neto_requerido: orden.peso_neto_requerido.toString(),
      sede: orden.sede?.toString() || '',
      area: orden.area?.toString() || '',
      bodega_quimicos: orden.bodega_quimicos?.toString() || '',
      estado: orden.estado,
      fecha_inicio_planificada: orden.fecha_inicio_planificada || '',
      fecha_fin_planificada: orden.fecha_fin_planificada || '',
      maquina_asignada: orden.maquina_asignada?.toString() || '',
      observaciones: orden.observaciones || '',
      prioridad: orden.prioridad || 'normal',
      justificacion: orden.justificacion || ''
    });
    setIsOpen(true);
  };

  const handleStatusChange = async (id: number, newStatus: 'en_proceso' | 'finalizada') => {
    if (onOrderStatusChange) {
      await onOrderStatusChange(id, newStatus);
    } else {
      // Fallback if not provided, though it should be
      toast.error('La función de cambio de estado no está implementada.');
    }
  };

  return (
    <Card className="flex flex-col h-full min-h-0">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Órdenes de Producción</CardTitle>
            <CardDescription>Crea y administra las órdenes de producción.</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => { setIsOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button disabled={loading}>
                <Factory className="w-4 h-4 mr-2" />
                {loading ? 'Cargando Catálogos...' : 'Nueva Orden'}
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>{editingOrden ? 'Editar Orden de Producción' : 'Nueva Orden de Producción'}</DialogTitle>
                <DialogDescription>
                  {editingOrden ? 'Modifica los datos de la orden.' : 'Completa el formulario para crear una nueva orden de producción.'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
                  <Input id="codigo" value={formData.codigo} onChange={e => setFormData({ ...formData, codigo: e.target.value })} className={errors.codigo ? 'border-destructive' : ''} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="peso_neto_requerido">Peso Neto Requerido (Kg) <span className="text-destructive">*</span></Label>
                  <Input id="peso_neto_requerido" type="number" value={formData.peso_neto_requerido} onChange={e => setFormData({ ...formData, peso_neto_requerido: e.target.value })} className={errors.peso_neto_requerido ? 'border-destructive' : ''} />
                </div>
                {editingOrden && (
                  <div className="space-y-2">
                    <Label htmlFor="producto_entrada">Producto Entrada <span className="text-destructive">*</span></Label>
                    <Select value={formData.producto_entrada} onValueChange={v => setFormData({ ...formData, producto_entrada: v })}>
                      <SelectTrigger className={errors.producto_entrada ? 'border-destructive' : ''}>
                        <SelectValue placeholder={productos.length ? "Selecciona producto de entrada" : "No hay productos disponibles"} />
                      </SelectTrigger>
                      <SelectContent>
                        {productos.length > 0 ? (
                          productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)
                        ) : (
                          <div className="py-2 px-4 text-sm text-muted-foreground">Sin productos</div>
                        )}
                      </SelectContent>
                    </Select>
                    {errors.producto_entrada && <p className="text-sm text-destructive">{errors.producto_entrada}</p>}
                  </div>
                )}
                {editingOrden && (
                  <div className="space-y-2">
                    <Label htmlFor="bodega_entrada">Bodega Entrada</Label>
                    <Select value={formData.bodega_entrada} onValueChange={v => setFormData({ ...formData, bodega_entrada: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder={bodegas.length ? "Selecciona bodega de entrada" : "No hay bodegas disponibles"} />
                      </SelectTrigger>
                      <SelectContent>
                        {bodegas.length > 0 ? (
                          bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)
                        ) : (
                          <div className="py-2 px-4 text-sm text-muted-foreground">Sin bodegas</div>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                {editingOrden && (
                  <div className="space-y-2">
                    <Label htmlFor="producto_salida">Producto Salida <span className="text-destructive">*</span></Label>
                    <Select value={formData.producto_salida} onValueChange={v => setFormData({ ...formData, producto_salida: v })}>
                      <SelectTrigger className={errors.producto_salida ? 'border-destructive' : ''}>
                        <SelectValue placeholder={productos.length ? "Selecciona producto de salida" : "No hay productos disponibles"} />
                      </SelectTrigger>
                      <SelectContent>
                        {productos.length > 0 ? (
                          productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)
                        ) : (
                          <div className="py-2 px-4 text-sm text-muted-foreground">Sin productos</div>
                        )}
                      </SelectContent>
                    </Select>
                    {errors.producto_salida && <p className="text-sm text-destructive">{errors.producto_salida}</p>}
                  </div>
                )}
                {editingOrden && (
                  <div className="space-y-2">
                    <Label htmlFor="bodega_salida">Bodega Salida</Label>
                    <Select value={formData.bodega_salida} onValueChange={v => setFormData({ ...formData, bodega_salida: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder={bodegas.length ? "Selecciona bodega de salida" : "No hay bodegas disponibles"} />
                      </SelectTrigger>
                      <SelectContent>
                        {bodegas.length > 0 ? (
                          bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)
                        ) : (
                          <div className="py-2 px-4 text-sm text-muted-foreground">Sin bodegas</div>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="area">Área Responsable <span className="text-destructive">*</span></Label>
                  <Select value={formData.area} onValueChange={v => setFormData({ ...formData, area: v })}>
                    <SelectTrigger><SelectValue placeholder={areas.length ? "Selecciona el área de destino" : "No hay áreas registradas"} /></SelectTrigger>
                    <SelectContent>
                      {areas.length > 0 ? (
                        areas.map(a => <SelectItem key={a.id} value={a.id.toString()}>{a.nombre}</SelectItem>)
                      ) : (
                        <div className="py-2 px-4 text-sm text-muted-foreground">Sin áreas disponibles</div>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prioridad">Prioridad <span className="text-destructive">*</span></Label>
                  <Select value={formData.prioridad} onValueChange={v => setFormData({ ...formData, prioridad: v })}>
                    <SelectTrigger><SelectValue placeholder="Selecciona una prioridad" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="baja">Baja</SelectItem>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="alta">Alta</SelectItem>
                      <SelectItem value="urgente">Urgente</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fecha_inicio_planificada">Fecha Inicio</Label>
                  <Input id="fecha_inicio_planificada" type="date" value={formData.fecha_inicio_planificada} onChange={e => setFormData({ ...formData, fecha_inicio_planificada: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fecha_fin_planificada">Fecha Fin</Label>
                  <Input id="fecha_fin_planificada" type="date" value={formData.fecha_fin_planificada} onChange={e => setFormData({ ...formData, fecha_fin_planificada: e.target.value })} />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="observaciones">Observaciones</Label>
                  <Input id="observaciones" value={formData.observaciones} onChange={e => setFormData({ ...formData, observaciones: e.target.value })} placeholder="Instrucciones especiales..." />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit} disabled={isSubmitting}>
                  {isSubmitting ? 'Guardando...' : (editingOrden ? 'Actualizar' : 'Crear')}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4 flex flex-col sm:flex-row gap-4">
          <Input
            placeholder="Buscar por código, producto..."
            value={searchTerm}
            onChange={(e) => {
              const val = e.target.value;
              setSearchParams(prev => {
                if (val) prev.set('search', val);
                else prev.delete('search');
                prev.set('page', '1');
                return prev;
              }, { replace: true });
            }}
            className="w-full sm:w-1/2 md:w-1/3"
          />
          <Select 
            value={statusFilter} 
            onValueChange={(val) => {
              setSearchParams(prev => {
                if (val === 'all') prev.delete('status');
                else prev.set('status', val);
                prev.set('page', '1');
                return prev;
              }, { replace: true });
            }}
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Estado..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los estados</SelectItem>
              <SelectItem value="pendiente">Pendiente</SelectItem>
              <SelectItem value="en_proceso">En Proceso</SelectItem>
              <SelectItem value="finalizada">Finalizada</SelectItem>
            </SelectContent>
          </Select>
          <Select 
            value={machineFilter} 
            onValueChange={(val) => {
              setSearchParams(prev => {
                if (val === 'all') prev.delete('maquina');
                else prev.set('maquina', val);
                prev.set('page', '1');
                return prev;
              }, { replace: true });
            }}
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Máquina..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas las máquinas</SelectItem>
              {maquinas.map(m => (
                <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
        <div className="flex-1 overflow-auto rounded-md border relative">
          <Table className="min-w-max">
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Producto & Fórmula</TableHead>
                <TableHead>Máquina</TableHead>
                <TableHead>Entrega</TableHead>
                <TableHead>Prioridad</TableHead>
                <TableHead>Peso Req.</TableHead>
                <TableHead>Progreso</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-8 w-8" /></TableCell>
                  </TableRow>
                ))
              ) : paginatedOrdenes.map(orden => {
                const today = new Date().toISOString().split('T')[0];
                const isOverdue = orden.estado !== 'finalizada' && orden.fecha_fin_planificada && orden.fecha_fin_planificada < today;
                const isToday = orden.estado !== 'finalizada' && orden.fecha_fin_planificada === today;

                return (
                <TableRow
                  key={orden.id}
                  onClick={() => setSelectedOrdenForDetail(orden)}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <TableCell className="font-mono">{orden.codigo}</TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium">{orden.producto_nombre}</span>
                      <span className="text-xs text-muted-foreground">{orden.formula_color_nombre}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {orden.maquina_asignada_nombre ? (
                      <Badge variant="outline" className="bg-slate-50">{orden.maquina_asignada_nombre}</Badge>
                    ) : (
                      <span className="text-muted-foreground text-xs">Sin asignar</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {orden.fecha_fin_planificada ? (
                      <span className={`text-sm ${isOverdue ? 'text-red-600 font-semibold' : isToday ? 'text-amber-600 font-semibold' : 'text-slate-600'}`}>
                        {orden.fecha_fin_planificada}
                      </span>
                    ) : (
                      <span className="text-muted-foreground text-xs">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {orden.prioridad === 'baja' && <Badge variant="secondary" className="bg-slate-100 text-slate-600">Baja</Badge>}
                    {orden.prioridad === 'normal' && <Badge variant="secondary" className="bg-blue-50 text-blue-600">Normal</Badge>}
                    {orden.prioridad === 'alta' && <Badge variant="secondary" className="bg-orange-50 text-orange-600 border-orange-200">Alta</Badge>}
                    {orden.prioridad === 'urgente' && <Badge variant="secondary" className="bg-red-50 text-red-600 border-red-200 font-bold animate-pulse">Urgente</Badge>}
                  </TableCell>
                  <TableCell>{orden.peso_neto_requerido} Kg</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1 text-xs">
                      <span className="text-muted-foreground">{orden.peso_producido || 0} / {orden.peso_neto_requerido} Kg</span>
                      <div className="w-24 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: `${Math.min(100, ((orden.peso_producido || 0) / orden.peso_neto_requerido) * 100)}%` }}></div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-1">
                      <div>
                        {orden.estado === 'pendiente' && <Badge variant="secondary" className="bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200">Pendiente</Badge>}
                        {orden.estado === 'en_proceso' && <Badge variant="secondary" className="bg-blue-50 text-blue-600 hover:bg-blue-100 border-blue-200">En Proceso</Badge>}
                        {orden.estado === 'finalizada' && <Badge variant="secondary" className="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 border-emerald-200">Finalizada</Badge>}
                        {!['pendiente', 'en_proceso', 'finalizada'].includes(orden.estado) && <Badge variant="outline" className="capitalize">{orden.estado.replace('_', ' ')}</Badge>}
                      </div>
                      {orden.inventario_descontado && <Badge className="bg-green-100 text-green-800 hover:bg-green-200 border-green-200 w-fit">✓ QUÍMICOS DESCONTADOS</Badge>}
                    </div>
                  </TableCell>
                  <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <span className="sr-only">Abrir menu</span>
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Acciones</DropdownMenuLabel>
                        <DropdownMenuItem onClick={() => handleEdit(orden)}>
                          <Pencil className="mr-2 h-4 w-4" /> Editar
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleOpenRequisitosDialog(orden)}>
                          <ClipboardList className="mr-2 h-4 w-4" /> Ver Requisitos
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleOpenLotDialog(orden)}
                          disabled={orden.estado === 'finalizada'}
                        >
                          <PlusCircle className="mr-2 h-4 w-4" /> Registrar Lote
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuLabel>Cambiar Estado</DropdownMenuLabel>
                        <DropdownMenuItem
                          onClick={() => handleStatusChange(orden.id, 'en_proceso')}
                          disabled={orden.estado !== 'pendiente'}
                        >
                          Iniciar Proceso
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleStatusChange(orden.id, 'finalizada')}
                          disabled={orden.estado !== 'en_proceso'}
                        >
                          Marcar como Finalizada
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => onOrdenDelete(orden.id)} className="text-destructive">
                          <Trash2 className="mr-2 h-4 w-4" /> Eliminar
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        <div className="flex items-center justify-between mt-4 flex-shrink-0">
          <span className="text-sm text-muted-foreground">
            Página {currentPage} de {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setSearchParams(prev => { prev.set('page', Math.max(1, currentPage - 1).toString()); return prev; })} disabled={currentPage === 1 || loading}>
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </Button>
            <span className="flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">Ir a</span>
              <Input
                type="number"
                min={1}
                max={totalPages}
                defaultValue={currentPage}
                key={currentPage}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const v = parseInt((e.target as HTMLInputElement).value, 10);
                    if (!isNaN(v) && v >= 1 && v <= totalPages) {
                      setSearchParams(prev => { prev.set('page', String(v)); return prev; });
                    }
                  }
                }}
                onBlur={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!isNaN(v) && v >= 1 && v <= totalPages) {
                    setSearchParams(prev => { prev.set('page', String(v)); return prev; });
                  }
                }}
                className="w-14 h-8 text-center py-0 px-1"
              />
            </span>
            <Button size="sm" variant="outline" onClick={() => setSearchParams(prev => { prev.set('page', Math.min(totalPages, currentPage + 1).toString()); return prev; })} disabled={currentPage === totalPages || loading}>
              Siguiente <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
      <RegistrarLoteDialog
        open={isLotDialogOpen}
        onOpenChange={setIsLotDialogOpen}
        orden={selectedOrdenForLot}
        maquinas={maquinas}
        onLotCreated={onDataRefresh}
      />
      <RequisitosMaterialesDialog
        open={isRequisitosDialogOpen}
        onOpenChange={setIsRequisitosDialogOpen}
        orden={selectedOrdenForRequisitos}
      />
      <OrdenDetalleSheet
        open={selectedOrdenForDetail !== null}
        onOpenChange={(open) => { if (!open) setSelectedOrdenForDetail(null); }}
        orden={selectedOrdenForDetail}
        onEdit={(o) => { setSelectedOrdenForDetail(null); handleEdit(o); }}
        onDelete={(id) => { setSelectedOrdenForDetail(null); onOrdenDelete(id); }}
        onStatusChange={handleStatusChange}
        onOpenLotDialog={(o) => { setSelectedOrdenForDetail(null); handleOpenLotDialog(o); }}
        onOpenRequisitosDialog={handleOpenRequisitosDialog}
        sedes={sedes}
        areas={areas}
        bodegas={bodegas}
        formulas={formulas}
      />
    </Card>
  );
}