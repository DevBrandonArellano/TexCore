import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { OrdenProduccion, Producto, FormulaColor, Sede, Maquina, Area, Bodega } from '../../lib/types';
import { Pencil, Trash2, ChevronLeft, ChevronRight, MoreHorizontal, PlusCircle, ClipboardList } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';
import apiClient from '../../lib/axios';
import { createLogger } from '../../lib/logger';
import { usePagination } from '../../hooks/usePagination';
import { RequisitosMaterialesDialog } from './RequisitosMaterialesDialog';
import { RegistrarLoteDialog } from './RegistrarLoteDialog';
import { OrdenDetalleSheet } from './OrdenDetalleSheet';
import { OrdenFormDialog } from './OrdenFormDialog';
import {
  type OrdenFormData,
  EMPTY_ORDEN_FORM_DATA,
  getOrdenVencimientoStatus,
  estadoBadge,
  prioridadBadge,
  buildOrdenPayload,
  validateOrdenForm,
} from './ordenUtils';

// RFC 5424 — logger del módulo (relay a /api/logs/ para WARNING+).
const logger = createLogger('ManageOrdenesProduccion');

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
        // Si falla, se conservan las áreas del prop (degradación elegante);
        // se deja rastro para diagnóstico sin interrumpir al usuario.
        logger.warning('No se pudieron refrescar las áreas; se usan las del prop', {
          operacion: 'fetchAreas',
        });
      });
    }
  }, [isOpen]);
  const [editingOrden, setEditingOrden] = useState<OrdenProduccion | null>(null);
  const [formData, setFormData] = useState<OrdenFormData>({ ...EMPTY_ORDEN_FORM_DATA });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const statusFilter = searchParams.get('status') || 'all';
  const machineFilter = searchParams.get('maquina') || 'all';
  // Saneo del parámetro de URL: NaN o valores < 1 → página 1. Evita que
  // ?page=NaN/-5 deje ambos botones de paginación habilitados y desincronice
  // el estado. El límite superior lo cubre el botón "Siguiente" (currentPage >= totalPages).
  const currentPage = Math.max(1, parseInt(searchParams.get('page') || '1', 10) || 1);
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

  const { totalPages, paginatedItems: paginatedOrdenes, setCurrentPage } = usePagination(filteredOrdenes, ITEMS_PER_PAGE, {
    page: currentPage,
    onPageChange: (p) => setSearchParams(prev => { prev.set('page', String(p)); return prev; }),
  });

  const resetForm = () => {
    setFormData({ ...EMPTY_ORDEN_FORM_DATA });
    setErrors({});
    setEditingOrden(null);
  };

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const newErrors = validateOrdenForm(formData, !!editingOrden);
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    const dataToSend = buildOrdenPayload(formData);

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
          <OrdenFormDialog
            isOpen={isOpen}
            onDialogOpenChange={(open) => { setIsOpen(open); if (!open) resetForm(); }}
            onCancel={() => setIsOpen(false)}
            editingOrden={editingOrden}
            formData={formData}
            setFormData={setFormData}
            errors={errors}
            productos={productos}
            bodegas={bodegas}
            areas={areas}
            loading={loading}
            isSubmitting={isSubmitting}
            onSubmit={handleSubmit}
          />
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
                const { isOverdue, isToday } = getOrdenVencimientoStatus(orden);

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
                    {prioridadBadge(orden.prioridad)}
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
                        {estadoBadge(orden.estado)}
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
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1 || loading}>
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
                      setCurrentPage(v);
                    }
                  }
                }}
                onBlur={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!isNaN(v) && v >= 1 && v <= totalPages) {
                    setCurrentPage(v);
                  }
                }}
                className="w-14 h-8 text-center py-0 px-1"
              />
            </span>
            <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages || loading}>
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
