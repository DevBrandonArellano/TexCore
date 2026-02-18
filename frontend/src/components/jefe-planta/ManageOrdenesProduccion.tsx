import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area } from '../../lib/types';
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
  onOrdenCreate: (data: any) => Promise<boolean>;
  onOrdenUpdate: (id: number, data: any) => Promise<boolean>;
  onOrdenDelete: (id: number) => void;
  loading: boolean;
  onDataRefresh: () => void;
}

const ITEMS_PER_PAGE = 10;

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
  onOrdenCreate,
  onOrdenUpdate,
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
    estado: 'pendiente',
    fecha_inicio_planificada: '',
    fecha_fin_planificada: '',
    maquina_asignada: '',
    observaciones: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
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
    return ordenes.filter(o =>
      o.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.producto_nombre?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [ordenes, searchTerm]);

  const paginatedOrdenes = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredOrdenes.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredOrdenes, currentPage]);

  const totalPages = Math.ceil(filteredOrdenes.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      codigo: '',
      producto: '',
      formula_color: '',
      peso_neto_requerido: '',
      sede: '',
      area: '',
      estado: 'pendiente',
      fecha_inicio_planificada: '',
      fecha_fin_planificada: '',
      maquina_asignada: '',
      observaciones: ''
    });
    setErrors({});
    setEditingOrden(null);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
    if (!formData.producto) newErrors.producto = 'El producto es requerido';
    if (!formData.formula_color) newErrors.formula_color = 'La fórmula es requerida';
    if (!formData.peso_neto_requerido || parseFloat(formData.peso_neto_requerido) <= 0) newErrors.peso_neto_requerido = 'El peso es requerido y debe ser mayor a 0';
    if (!formData.sede) newErrors.sede = 'La sede es requerida';
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
      formula_color: parseInt(formData.formula_color),
      sede: parseInt(formData.sede),
      area: formData.area ? parseInt(formData.area) : null,
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
      estado: orden.estado,
      fecha_inicio_planificada: orden.fecha_inicio_planificada || '',
      fecha_fin_planificada: orden.fecha_fin_planificada || '',
      maquina_asignada: orden.maquina_asignada?.toString() || '',
      observaciones: orden.observaciones || ''
    });
    setIsOpen(true);
  };

  const handleStatusChange = (id: number, newStatus: 'en_proceso' | 'finalizada') => {
    onOrdenUpdate(id, { estado: newStatus });
  };

  return (
    <Card>
      <CardHeader>
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
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>{editingOrden ? 'Editar Orden de Producción' : 'Nueva Orden de Producción'}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
                  <Input id="codigo" value={formData.codigo} onChange={e => setFormData({ ...formData, codigo: e.target.value })} className={errors.codigo ? 'border-destructive' : ''} />
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
                  <Label htmlFor="formula_color">Fórmula de Color <span className="text-destructive">*</span></Label>
                  <Select value={formData.formula_color} onValueChange={v => setFormData({ ...formData, formula_color: v })}>
                    <SelectTrigger><SelectValue placeholder={formulas.length ? "Selecciona una fórmula" : "No hay fórmulas disponibles"} /></SelectTrigger>
                    <SelectContent>
                      {formulas.length > 0 ? (
                        formulas.map(f => <SelectItem key={f.id} value={f.id.toString()}>{f.nombre_color}</SelectItem>)
                      ) : (
                        <div className="py-2 px-4 text-sm text-muted-foreground">Sin fórmulas</div>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="peso_neto_requerido">Peso Neto Requerido (Kg) <span className="text-destructive">*</span></Label>
                  <Input id="peso_neto_requerido" type="number" value={formData.peso_neto_requerido} onChange={e => setFormData({ ...formData, peso_neto_requerido: e.target.value })} className={errors.peso_neto_requerido ? 'border-destructive' : ''} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sede">Sede <span className="text-destructive">*</span></Label>
                  <Select value={formData.sede} onValueChange={v => setFormData({ ...formData, sede: v })}>
                    <SelectTrigger><SelectValue placeholder={sedes.length ? "Selecciona una sede" : "No hay sedes disponibles"} /></SelectTrigger>
                    <SelectContent>
                      {sedes.length > 0 ? (
                        sedes.map(s => <SelectItem key={s.id} value={s.id.toString()}>{s.nombre}</SelectItem>)
                      ) : (
                        <div className="py-2 px-4 text-sm text-muted-foreground">Sin sedes</div>
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
                {/* Campos de Planificación */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="fecha_inicio_planificada">Fecha Inicio</Label>
                    <Input id="fecha_inicio_planificada" type="date" value={formData.fecha_inicio_planificada} onChange={e => setFormData({ ...formData, fecha_inicio_planificada: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="fecha_fin_planificada">Fecha Fin</Label>
                    <Input id="fecha_fin_planificada" type="date" value={formData.fecha_fin_planificada} onChange={e => setFormData({ ...formData, fecha_fin_planificada: e.target.value })} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maquina_asignada">Máquina Asignada</Label>
                  <Select value={formData.maquina_asignada} onValueChange={v => setFormData({ ...formData, maquina_asignada: v })}>
                    <SelectTrigger><SelectValue placeholder="Selecciona una máquina" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Sin asignar</SelectItem>
                      {maquinas.map(m => (
                        <SelectItem key={m.id} value={m.id.toString()}>{m.nombre} ({m.area_nombre})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
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
        <div className="mb-4">
          <Input
            placeholder="Buscar por código, producto..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            className="w-full"
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Fórmula</TableHead>
                <TableHead>Peso Req.</TableHead>
                <TableHead>Sede</TableHead>
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
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell className="text-right"><Skeleton className="h-8 w-8" /></TableCell>
                  </TableRow>
                ))
              ) : paginatedOrdenes.map(orden => (
                <TableRow key={orden.id}>
                  <TableCell className="font-mono">{orden.codigo}</TableCell>
                  <TableCell>{orden.producto_nombre}</TableCell>
                  <TableCell>{orden.formula_color_nombre}</TableCell>
                  <TableCell>{orden.peso_neto_requerido} Kg</TableCell>
                  <TableCell>{orden.sede_nombre}</TableCell>
                  <TableCell><Badge variant={orden.estado === 'finalizada' ? 'default' : 'secondary'}>{orden.estado}</Badge></TableCell>
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
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-muted-foreground">
            Página {currentPage} de {totalPages}
          </span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1 || loading}>
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </Button>
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages || loading}>
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