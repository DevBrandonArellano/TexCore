import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Producto } from '../../lib/types';
import { PackagePlus, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageProductosProps {
  productos: Producto[];
  onProductCreate: (productData: any) => Promise<boolean>;
  onProductUpdate: (productId: number, productData: any) => Promise<boolean>;
  onProductDelete: (productId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageProductos({ productos, onProductCreate, onProductUpdate, onProductDelete, loading }: ManageProductosProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingProducto, setEditingProducto] = useState<Producto | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    descripcion: '',
    tipo: 'hilo' as 'hilo' | 'tela' | 'subproducto',
    unidad_medida: 'kg' as 'kg' | 'metros' | 'unidades',
    presentacion: '',
    pais_origen: '',
    calidad: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredProductos = useMemo(() => {
    return productos.filter(producto =>
      producto.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      producto.descripcion.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [productos, searchTerm]);

  const paginatedProductos = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredProductos.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredProductos, currentPage]);

  const totalPages = Math.ceil(filteredProductos.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      codigo: '',
      descripcion: '',
      tipo: 'hilo',
      unidad_medida: 'kg',
      presentacion: '',
      pais_origen: '',
      calidad: '',
    });
    setErrors({});
    setEditingProducto(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
    if (!formData.descripcion.trim()) newErrors.descripcion = 'La descripción es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    let success = false;
    if (editingProducto) {
      success = await onProductUpdate(editingProducto.id, formData);
    } else {
      success = await onProductCreate(formData);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (producto: Producto) => {
    setEditingProducto(producto);
    setFormData({
      codigo: producto.codigo,
      descripcion: producto.descripcion,
      tipo: producto.tipo,
      unidad_medida: producto.unidad_medida,
      presentacion: producto.presentacion || '',
      pais_origen: producto.pais_origen || '',
      calidad: producto.calidad || '',
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Productos</CardTitle>
            <CardDescription>Administra los productos del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <PackagePlus className="w-4 h-4 mr-2" />
                Nuevo Producto
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingProducto ? 'Editar Producto' : 'Nuevo Producto'}</DialogTitle>
                <DialogDescription>
                  {editingProducto ? 'Modifica la información del producto' : 'Completa el formulario para crear un nuevo producto'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
                  <Input id="codigo" value={formData.codigo} onChange={(e) => setFormData({ ...formData, codigo: e.target.value })} className={errors.codigo ? 'border-destructive' : ''} />
                  {errors.codigo && <p className="text-sm text-destructive">{errors.codigo}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="descripcion">Descripción <span className="text-destructive">*</span></Label>
                  <Input id="descripcion" value={formData.descripcion} onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })} className={errors.descripcion ? 'border-destructive' : ''} />
                  {errors.descripcion && <p className="text-sm text-destructive">{errors.descripcion}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tipo">Tipo</Label>
                  <Select value={formData.tipo} onValueChange={(value) => setFormData({ ...formData, tipo: value as any })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona un tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hilo">Hilo</SelectItem>
                      <SelectItem value="tela">Tela</SelectItem>
                      <SelectItem value="subproducto">Sub-producto</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unidad_medida">Unidad de Medida</Label>
                  <Select value={formData.unidad_medida} onValueChange={(value) => setFormData({ ...formData, unidad_medida: value as any })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona una unidad" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="kg">Kg</SelectItem>
                      <SelectItem value="metros">Metros</SelectItem>
                      <SelectItem value="unidades">Unidades</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="presentacion">Presentación</Label>
                  <Input
                    id="presentacion"
                    placeholder="Ej: Cono 1kg, Caja 20u"
                    value={formData.presentacion}
                    onChange={(e) => setFormData({ ...formData, presentacion: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pais_origen">País de Origen</Label>
                  <Input
                    id="pais_origen"
                    placeholder="Ej: Perú, China, India"
                    value={formData.pais_origen}
                    onChange={(e) => setFormData({ ...formData, pais_origen: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="calidad">Calidad</Label>
                  <Input
                    id="calidad"
                    placeholder="Ej: Primera, Segunda, Premium"
                    value={formData.calidad}
                    onChange={(e) => setFormData({ ...formData, calidad: e.target.value })}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingProducto ? 'Actualizar' : 'Crear'} Producto</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por código o descripción..."
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
                <TableHead>Descripción</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Presentación</TableHead>
                <TableHead>País</TableHead>
                <TableHead>Calidad</TableHead>
                <TableHead>Unidad de Medida</TableHead>
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
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Skeleton className="h-8 w-8" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                paginatedProductos.map((producto) => (
                  <TableRow key={producto.id}>
                    <TableCell className="font-mono text-xs">{producto.codigo}</TableCell>
                    <TableCell>{producto.descripcion}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{producto.tipo}</Badge>
                    </TableCell>
                    <TableCell>{producto.presentacion || '-'}</TableCell>
                    <TableCell>{producto.pais_origen || '-'}</TableCell>
                    <TableCell>{producto.calidad || '-'}</TableCell>
                    <TableCell>{producto.unidad_medida}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(producto)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onProductDelete(producto.id)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <div className="flex items-center justify-between mt-4">
          <span className="text-sm text-muted-foreground">
            Página {currentPage} de {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1 || loading}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Anterior
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages || loading}
            >
              Siguiente
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
