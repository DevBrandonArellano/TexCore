import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { OrdenProduccion, Producto, FormulaColor, Sede } from '../../lib/types';
import { Factory, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageOrdenesProduccionProps {
  ordenes: OrdenProduccion[];
  productos: Producto[];
  formulas: FormulaColor[];
  sedes: Sede[];
  onOrdenCreate: (data: any) => Promise<boolean>;
  onOrdenUpdate: (id: number, data: any) => Promise<boolean>;
  onOrdenDelete: (id: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageOrdenesProduccion({
  ordenes,
  productos,
  formulas,
  sedes,
  onOrdenCreate,
  onOrdenUpdate,
  onOrdenDelete,
  loading
}: ManageOrdenesProduccionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingOrden, setEditingOrden] = useState<OrdenProduccion | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    producto: '',
    formula_color: '',
    peso_neto_requerido: '',
    sede: '',
    estado: 'pendiente'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredOrdenes = useMemo(() => {
    return ordenes.filter(o =>
      o.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (o as any).producto_nombre?.toLowerCase().includes(searchTerm.toLowerCase())
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
      estado: 'pendiente'
    });
    setErrors({});
    setEditingOrden(null);
  };

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
    };

    let success = false;
    if (editingOrden) {
      success = await onOrdenUpdate(editingOrden.id, dataToSend);
    } else {
      success = await onOrdenCreate(dataToSend);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
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
      estado: orden.estado
    });
    setIsOpen(true);
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
              <Button>
                <Factory className="w-4 h-4 mr-2" />
                Nueva Orden
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>{editingOrden ? 'Editar Orden de Producción' : 'Nueva Orden de Producción'}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
                  <Input id="codigo" value={formData.codigo} onChange={e => setFormData({...formData, codigo: e.target.value})} className={errors.codigo ? 'border-destructive' : ''} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="producto">Producto <span className="text-destructive">*</span></Label>
                  <Select value={formData.producto} onValueChange={v => setFormData({...formData, producto: v})}>
                    <SelectTrigger><SelectValue placeholder="Selecciona un producto" /></SelectTrigger>
                    <SelectContent>
                      {productos.map(p => <SelectItem key={p.id} value={p.id.toString()}>{p.descripcion}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="formula_color">Fórmula de Color <span className="text-destructive">*</span></Label>
                  <Select value={formData.formula_color} onValueChange={v => setFormData({...formData, formula_color: v})}>
                    <SelectTrigger><SelectValue placeholder="Selecciona una fórmula" /></SelectTrigger>
                    <SelectContent>
                      {formulas.map(f => <SelectItem key={f.id} value={f.id.toString()}>{f.nombre_color}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="peso_neto_requerido">Peso Neto Requerido (Kg) <span className="text-destructive">*</span></Label>
                  <Input id="peso_neto_requerido" type="number" value={formData.peso_neto_requerido} onChange={e => setFormData({...formData, peso_neto_requerido: e.target.value})} className={errors.peso_neto_requerido ? 'border-destructive' : ''} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sede">Sede <span className="text-destructive">*</span></Label>
                  <Select value={formData.sede} onValueChange={v => setFormData({...formData, sede: v})}>
                    <SelectTrigger><SelectValue placeholder="Selecciona una sede" /></SelectTrigger>
                    <SelectContent>
                      {sedes.map(s => <SelectItem key={s.id} value={s.id.toString()}>{s.nombre}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingOrden ? 'Actualizar' : 'Crear'}</Button>
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
                  <TableCell>{(orden as any).producto_nombre}</TableCell>
                  <TableCell>{(orden as any).formula_color_nombre}</TableCell>
                  <TableCell>{orden.peso_neto_requerido} Kg</TableCell>
                  <TableCell>{(orden as any).sede_nombre}</TableCell>
                  <TableCell><Badge variant={orden.estado === 'finalizada' ? 'default' : 'secondary'}>{orden.estado}</Badge></TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="outline" onClick={() => handleEdit(orden)}><Pencil className="w-4 h-4" /></Button>
                    <Button size="sm" variant="destructive" className="ml-2" onClick={() => onOrdenDelete(orden.id)}><Trash2 className="w-4 h-4" /></Button>
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
    </Card>
  );
}
