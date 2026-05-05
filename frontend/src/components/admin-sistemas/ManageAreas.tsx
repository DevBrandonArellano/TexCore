import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Area, Sede } from '../../lib/types';
import { Layers, Pencil, Trash2, Info } from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageAreasProps {
  areas: Area[];
  sedes: Sede[];
  selectedSedeId?: string;
  onAreaCreate: (data: any) => Promise<boolean>;
  onAreaUpdate: (id: number, data: any) => Promise<boolean>;
  onAreaDelete: (id: number) => void;
  loading: boolean;
}

export function ManageAreas({ areas, sedes, selectedSedeId, onAreaCreate, onAreaUpdate, onAreaDelete, loading }: ManageAreasProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingArea, setEditingArea] = useState<Area | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    sede: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const getAutoSedeId = (): string => {
    if (!sedes.length) return '';
    const sedeValida = selectedSedeId && sedes.some(s => s.id.toString() === selectedSedeId);
    return sedeValida ? String(selectedSedeId) : String(sedes[0].id);
  };

  // Respaldo: si el diálogo abre para crear y sede está vacía, asignar
  useEffect(() => {
    if (!editingArea && isOpen && !formData.sede && sedes.length > 0) {
      const auto = selectedSedeId && sedes.some(s => String(s.id) === String(selectedSedeId))
        ? String(selectedSedeId)
        : String(sedes[0].id);
      setFormData(prev => ({ ...prev, sede: auto }));
    }
  }, [editingArea, isOpen, formData.sede, selectedSedeId, sedes]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      sede: ''
    });
    setErrors({});
    setEditingArea(null);
  };

  const handleOpenNuevaArea = () => {
    setEditingArea(null);
    setErrors({});
    const autoSede = getAutoSedeId();
    setFormData({ nombre: '', sede: autoSede });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es requerido';
    if (!editingArea && !formData.sede) newErrors.sede = 'Selecciona una sede en el menú lateral';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    const payload = {
        ...formData,
        sede: Number(formData.sede)
    };

    let success = false;
    if (editingArea) {
      success = await onAreaUpdate(editingArea.id, payload);
    } else {
      success = await onAreaCreate(payload);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (area: Area) => {
    setEditingArea(area);
    setFormData({
      nombre: area.nombre,
      sede: area.sede.toString()
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Gestión de Áreas</CardTitle>
            <CardDescription>Administra las áreas de producción de cada sede</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button onClick={handleOpenNuevaArea}>
                <Layers className="w-4 h-4 mr-2" />
                Nueva Área
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {editingArea ? 'Editar Área' : 'Nueva Área'}
                </DialogTitle>
                <DialogDescription>
                  {editingArea ? 'Modifica la información del área' : 'Completa el formulario para crear una nueva área'}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="sede">
                    Sede <span className="text-destructive">*</span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="inline-block w-4 h-4 ml-1 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            {editingArea
                              ? 'La sede del área no se puede cambiar al editar.'
                              : 'La sede se asigna automáticamente según la sede seleccionada en el menú lateral.'}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </Label>
                  <div
                    id="sede"
                    role="text"
                    aria-label="Sede asignada"
                    className={`flex h-9 w-full items-center rounded-md border px-3 py-1 text-base md:text-sm ${errors.sede ? 'border-destructive bg-muted' : 'border-input bg-muted'} text-foreground`}
                  >
                    {formData.sede
                      ? (sedes.find(s => s.id.toString() === formData.sede)?.nombre ?? formData.sede)
                      : 'Selecciona una sede en el menú lateral'}
                  </div>
                  {errors.sede && (
                    <p className="text-sm text-destructive">{errors.sede}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="name">
                    Nombre del Área <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="name"
                    autoFocus
                    placeholder="ej: Producción A"
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
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => { setIsOpen(false); resetForm(); }}>
                  Cancelar
                </Button>
                <Button onClick={handleSubmit}>
                  {editingArea ? 'Actualizar' : 'Crear'} Área
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
                <TableHead>Sede</TableHead>
                <TableHead>Ubicación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 4 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Skeleton className="h-8 w-8" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                areas.map((area) => {
                  const sede = sedes.find(s => s.id === area.sede);
                  return (
                    <TableRow key={area.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Layers className="w-4 h-4 text-muted-foreground" />
                          {area.nombre}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{sede?.nombre || 'N/A'}</Badge>
                      </TableCell>
                      <TableCell>{sede?.location || 'N/A'}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-2 justify-end">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleEdit(area)}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => onAreaDelete(area.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}