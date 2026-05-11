import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Proveedor } from '../../lib/types';
import { Truck, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageProveedoresProps {
  proveedores: Proveedor[];
  onProveedorCreate: (proveedorData: any) => Promise<boolean>;
  onProveedorUpdate: (proveedorId: number, proveedorData: any) => Promise<boolean>;
  onProveedorDelete: (proveedorId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 20;

export function ManageProveedores({ proveedores, onProveedorCreate, onProveedorUpdate, onProveedorDelete, loading }: ManageProveedoresProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingProveedor, setEditingProveedor] = useState<Proveedor | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    sede: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const filteredProveedores = useMemo(() => {
    return proveedores.filter(proveedor =>
      proveedor.nombre.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [proveedores, searchTerm]);

  const totalPages = Math.ceil(filteredProveedores.length / ITEMS_PER_PAGE);
  const safeTotalPages = Math.max(1, totalPages);
  const safePage = Math.min(Math.max(1, currentPage), safeTotalPages);

  useEffect(() => {
    if (currentPage !== safePage) {
      setSearchParams(prev => {
        prev.set('page', String(safePage));
        return prev;
      }, { replace: true });
    }
  }, [currentPage, safePage, setSearchParams]);

  const paginatedProveedores = useMemo(() => {
    const startIndex = (safePage - 1) * ITEMS_PER_PAGE;
    return filteredProveedores.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredProveedores, safePage]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      sede: '',
    });
    setErrors({});
    setEditingProveedor(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es requerido';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    let success = false;
    if (editingProveedor) {
      success = await onProveedorUpdate(editingProveedor.id, formData);
    } else {
      success = await onProveedorCreate(formData);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (proveedor: Proveedor) => {
    setEditingProveedor(proveedor);
    setFormData({
      nombre: proveedor.nombre,
      sede: proveedor.sede?.toString() || '',
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Proveedores</CardTitle>
            <CardDescription>Administra los proveedores de materia prima</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button onClick={() => resetForm()}>
                <Truck className="w-4 h-4 mr-2" />
                Nuevo Proveedor
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingProveedor ? 'Editar Proveedor' : 'Nuevo Proveedor'}</DialogTitle>
                <DialogDescription>
                  {editingProveedor ? 'Modifica el nombre del proveedor' : 'Ingresa el nombre del nuevo proveedor'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre <span className="text-destructive">*</span></Label>
                  <Input id="nombre" value={formData.nombre} onChange={(e) => setFormData({ ...formData, nombre: e.target.value })} className={errors.nombre ? 'border-destructive' : ''} />
                  {errors.nombre && <p className="text-sm text-destructive">{errors.nombre}</p>}
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => { setIsOpen(false); resetForm(); }}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingProveedor ? 'Actualizar' : 'Crear'} Proveedor</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por nombre..."
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
            className="w-full"
          />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-60" /></TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Skeleton className="h-8 w-8" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                paginatedProveedores.map((proveedor) => (
                  <TableRow key={proveedor.id}>
                    <TableCell className="font-medium">{proveedor.nombre}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(proveedor)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onProveedorDelete(proveedor.id)}
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
            Página {safePage} de {safeTotalPages}
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSearchParams(prev => { prev.set('page', Math.max(1, safePage - 1).toString()); return prev; })}
              disabled={safePage === 1 || loading}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Anterior
            </Button>
            <span className="flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">Ir a</span>
              <Input
                type="number"
                min={1}
                max={safeTotalPages}
                defaultValue={safePage}
                key={safePage}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const v = parseInt((e.target as HTMLInputElement).value, 10);
                    if (!isNaN(v) && v >= 1 && v <= safeTotalPages) {
                      setSearchParams(prev => { prev.set('page', String(v)); return prev; });
                    }
                  }
                }}
                onBlur={(e) => {
                  const v = parseInt(e.target.value, 10);
                  if (!isNaN(v) && v >= 1 && v <= safeTotalPages) {
                    setSearchParams(prev => { prev.set('page', String(v)); return prev; });
                  }
                }}
                className="w-14 h-8 text-center py-0 px-1"
              />
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSearchParams(prev => { prev.set('page', Math.min(safeTotalPages, safePage + 1).toString()); return prev; })}
              disabled={safePage === safeTotalPages || loading}
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
