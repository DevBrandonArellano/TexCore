import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Sede } from '../../lib/types';
import { Building2, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';
// Removed AxiosError as it's no longer directly used for error handling

import { useSedes, useCreateSede, useUpdateSede, useDeleteSede } from '../../hooks/useSedes'; // Import custom hooks


export function ManageSedes() { // Removed props
  const [isOpen, setIsOpen] = useState(false);
  const [editingSede, setEditingSede] = useState<Sede | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    location: '',
    status: 'activo' as 'activo' | 'inactivo'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Use React Query hooks
  const { data: sedes, isLoading, isError, error } = useSedes();
  const createSedeMutation = useCreateSede();
  const updateSedeMutation = useUpdateSede();
  const deleteSedeMutation = useDeleteSede();

  useEffect(() => {
    if (isError) {
      toast.error('Error al cargar las sedes', { description: error?.message || 'Ocurrió un error inesperado.' });
    }
  }, [isError, error]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      location: '',
      status: 'activo'
    });
    setErrors({});
    setEditingSede(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es requerido';
    if (!formData.location.trim()) newErrors.location = 'La ubicación es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    try {
      if (editingSede) {
        await updateSedeMutation.mutateAsync({ ...editingSede, ...formData });
      } else {
        await createSedeMutation.mutateAsync(formData);
      }
      setIsOpen(false);
      resetForm();
    } catch (submitError: any) {
      // Error handling is already in the mutation hook, but we can add more specific here if needed
      console.error("Submit error in ManageSedes:", submitError);
    }
  };

  const handleEdit = (sede: Sede) => {
    setEditingSede(sede);
    setFormData({
      nombre: sede.nombre,
      location: sede.location,
      status: sede.status
    });
    setIsOpen(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteSedeMutation.mutateAsync(id);
    } catch (deleteError: any) {
      console.error("Delete error in ManageSedes:", deleteError);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Gestión de Sedes</CardTitle>
            <CardDescription>Administra las ubicaciones de la empresa</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <Building2 className="w-4 h-4 mr-2" />
                Nueva Sede
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {editingSede ? 'Editar Sede' : 'Nueva Sede'}
                </DialogTitle>
                <DialogDescription>
                  {editingSede ? 'Modifica la información de la sede' : 'Completa el formulario para crear una nueva sede'}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">
                    Nombre de la Sede <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    placeholder="ej: Sede Principal"
                    value={formData.nombre}
                    onChange={(e) => {
                      setFormData({ ...formData, nombre: e.target.value });
                      setErrors({ ...errors, nombre: '' });
                    }}
                    className={errors.nombre ? 'border-destructive' : ''}
                  />
                  {errors.nombre && (
                    <p className="text-sm text-destructive">{errors.nombre}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="location">
                    Ubicación <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="location"
                    placeholder="ej: Ciudad de México"
                    value={formData.location}
                    onChange={(e) => {
                      setFormData({ ...formData, location: e.target.value });
                      setErrors({ ...errors, location: '' });
                    }}
                    className={errors.location ? 'border-destructive' : ''}
                  />
                  {errors.location && (
                    <p className="text-sm text-destructive">{errors.location}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="status">Estado</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(value: 'activo' | 'inactivo') => {
                      setFormData({ ...formData, status: value });
                    }}
                  >
                    <SelectTrigger id="status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="activo">Activo</SelectItem>
                      <SelectItem value="inactivo">Inactivo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>
                  Cancelar
                </Button>
                <Button 
                  onClick={handleSubmit}
                  disabled={createSedeMutation.isPending || updateSedeMutation.isPending}
                >
                  {createSedeMutation.isPending || updateSedeMutation.isPending ? 'Guardando...' : editingSede ? 'Actualizar' : 'Crear'} Sede
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Ubicación</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
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
                sedes?.map((sede) => ( // Use optional chaining for sedes
                  <TableRow key={sede.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-muted-foreground" />
                        {sede.nombre}
                      </div>
                    </TableCell>
                    <TableCell>{sede.location}</TableCell>
                    <TableCell>
                      <Badge variant={sede.status === 'activo' ? 'default' : 'secondary'}>
                        {sede.status === 'activo' ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(sede)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDelete(sede.id)}
                          disabled={deleteSedeMutation.isPending}
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
      </CardContent>
    </Card>
  );
}
