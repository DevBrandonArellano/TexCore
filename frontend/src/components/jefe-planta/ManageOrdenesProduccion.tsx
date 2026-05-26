import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area, Bodega } from '../../lib/types';
import { Factory, Pencil, Trash2, ChevronLeft, ChevronRight, MoreHorizontal, PlusCircle, Calendar, MessageSquare, Monitor, ClipboardList } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Textarea } from '../ui/textarea';
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

export function ManageOrdenesProduccion({
  ordenes,
  productos,
  formulas,
  sedes,
  maquinas,
  areas,
  bodegas,
  onOrdenCreate,
  onOrdenUpdate,
  onOrderStatusChange,
  onOrdenDelete,
  loading,
  onDataRefresh
}: ManageOrdenesProduccionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingOrden, setEditingOrden] = useState<OrdenProduccion | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    producto: '',
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
      producto: '',
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
    if (!formData.producto) newErrors.producto = 'El producto es requerido';
    if (!formData.peso_neto_requerido || parseFloat(formData.peso_neto_requerido) <= 0) newErrors.peso_neto_requerido = 'El peso es requerido y debe ser mayor a 0';
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
      producto: parseInt(formData.producto),
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
    setFormData({
      codigo: orden.codigo,
      producto: orden.producto.toString(),
      formula_color: orden.formula_color.toString(),
      peso_neto_requerido: orden.peso_neto_requerido.toString(),
      sede: orden.sede.toString(),
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
                <div className="space-y-2">
                  <Label htmlFor="producto">Producto <span className="text-destructive">*</span></Label>
                  <Select value={formData.producto} onValueChange={v => setFormData({ ...formData, producto: v })}>
                    <SelectTrigger><SelectValue placeholder={productos.length ? "Selecciona un producto" : "No hay productos disponibles"} /></SelectTrigger>
                    <SelectContent>
                      {productos.length > 0 ? (
                        productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)
                      ) : (
                        <div className="py-2 px-4 text-sm text-muted-foreground">Sin productos</div>
                      )}
                    </SelectContent>
                  </Select>
                </div>
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
                <TableRow key={orden.id}>
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
                  <TableCell className="text-right">
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
    </Card>
  );
}