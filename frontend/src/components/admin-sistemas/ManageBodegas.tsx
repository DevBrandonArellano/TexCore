import React, { useState, useMemo, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Bodega, Sede, User } from '../../lib/types';
import { Warehouse, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageBodegasProps {
  bodegas: Bodega[];
  sedes: Sede[];
  users: User[];
  onBodegaCreate: (bodegaData: any) => Promise<boolean>;
  onBodegaUpdate: (bodegaId: number, bodegaData: any) => Promise<boolean>;
  onBodegaDelete: (bodegaId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageBodegas({ bodegas, sedes, users, onBodegaCreate, onBodegaUpdate, onBodegaDelete, loading }: ManageBodegasProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingBodega, setEditingBodega] = useState<Bodega | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    sede: '',
    usuarios_asignados: [] as number[],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const getSedeName = useCallback((sedeId: number) => {
    return sedes.find(s => s.id === sedeId)?.nombre || 'N/A';
  }, [sedes]);

  // Filtrar usuarios based on selected sede
  const availableUsers = useMemo(() => {
    if (!formData.sede) return [];
    const sedeId = parseInt(formData.sede, 10);
    // Filtrar usuarios que pertenecen a esa sede
    return users.filter(user => user.sede === sedeId);
  }, [users, formData.sede]);

  const filteredBodegas = useMemo(() => {
    return bodegas.filter(bodega =>
      bodega.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      getSedeName(bodega.sede).toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [bodegas, searchTerm, getSedeName]);

  const paginatedBodegas = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredBodegas.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredBodegas, currentPage]);

  const totalPages = Math.ceil(filteredBodegas.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      nombre: '',
      sede: '',
      usuarios_asignados: [],
    });
    setErrors({});
    setEditingBodega(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es requerido';
    if (!formData.sede) newErrors.sede = 'La sede es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    const bodegaDataToSend = {
      nombre: formData.nombre,
      sede: parseInt(formData.sede, 10),
      usuarios_asignados: formData.usuarios_asignados
    };

    let success = false;
    if (editingBodega) {
      success = await onBodegaUpdate(editingBodega.id, bodegaDataToSend);
    } else {
      success = await onBodegaCreate(bodegaDataToSend);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (bodega: Bodega) => {
    setEditingBodega(bodega);
    setFormData({
      nombre: bodega.nombre,
      sede: bodega.sede.toString(),
      usuarios_asignados: bodega.usuarios_asignados || [],
    });
    setIsOpen(true);
  };

  const handleUserToggle = (userId: number) => {
    setFormData(prev => {
      const current = prev.usuarios_asignados;
      if (current.includes(userId)) {
        return { ...prev, usuarios_asignados: current.filter(id => id !== userId) };
      } else {
        return { ...prev, usuarios_asignados: [...current, userId] };
      }
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Bodegas</CardTitle>
            <CardDescription>Administra las bodegas del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <Warehouse className="w-4 h-4 mr-2" />
                Nueva Bodega
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>{editingBodega ? 'Editar Bodega' : 'Nueva Bodega'}</DialogTitle>
                <DialogDescription>
                  {editingBodega ? 'Modifica la información de la bodega' : 'Completa el formulario para crear una nueva bodega'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre <span className="text-destructive">*</span></Label>
                  <Input id="nombre" value={formData.nombre} onChange={(e) => setFormData({ ...formData, nombre: e.target.value })} className={errors.nombre ? 'border-destructive' : ''} />
                  {errors.nombre && <p className="text-sm text-destructive">{errors.nombre}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sede">Sede <span className="text-destructive">*</span></Label>
                  <Select value={formData.sede} onValueChange={(value) => setFormData({ ...formData, sede: value, usuarios_asignados: [] })}>
                    <SelectTrigger className={errors.sede ? 'border-destructive' : ''}>
                      <SelectValue placeholder="Selecciona una sede" />
                    </SelectTrigger>
                    <SelectContent>
                      {sedes.map(sede => (
                        <SelectItem key={sede.id} value={sede.id.toString()}>
                          {sede.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.sede && <p className="text-sm text-destructive">{errors.sede}</p>}
                </div>

                {formData.sede && (
                  <div className="space-y-2">
                    <Label>Asignar Bodegueros (de la sede seleccionada)</Label>
                    <ScrollArea className="h-40 border rounded-md p-2">
                      {availableUsers.length > 0 ? (
                        availableUsers.map(user => (
                          <div key={user.id} className="flex items-center gap-2 py-1">
                            <Checkbox
                              id={`user-${user.id}`}
                              checked={formData.usuarios_asignados.includes(user.id)}
                              onCheckedChange={() => handleUserToggle(user.id)}
                            />
                            <Label htmlFor={`user-${user.id}`} className="cursor-pointer font-normal">
                              {user.first_name} {user.last_name} ({user.username})
                            </Label>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-muted-foreground p-2">No hay usuarios en esta sede.</p>
                      )}
                    </ScrollArea>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingBodega ? 'Actualizar' : 'Crear'} Bodega</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por nombre o sede..."
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
                <TableHead>Nombre</TableHead>
                <TableHead>Sede</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Skeleton className="h-8 w-8" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                paginatedBodegas.map((bodega) => (
                  <TableRow key={bodega.id}>
                    <TableCell>{bodega.nombre}</TableCell>
                    <TableCell>{getSedeName(bodega.sede)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(bodega)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onBodegaDelete(bodega.id)}
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
