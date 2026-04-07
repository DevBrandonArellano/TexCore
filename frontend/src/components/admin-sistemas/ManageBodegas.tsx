import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Bodega, Sede, User } from '../../lib/types';
import { Warehouse, Pencil, Trash2, ChevronLeft, ChevronRight, Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { ScrollArea } from '../ui/scroll-area';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageBodegasProps {
  bodegas: Bodega[];
  sedes: Sede[];
  users: User[];
  selectedSedeId?: string;
  onBodegaCreate: (bodegaData: any) => Promise<boolean>;
  onBodegaUpdate: (bodegaId: number, bodegaData: any) => Promise<boolean>;
  onBodegaDelete: (bodegaId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 20;

export function ManageBodegas({ bodegas, sedes, users, selectedSedeId, onBodegaCreate, onBodegaUpdate, onBodegaDelete, loading }: ManageBodegasProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingBodega, setEditingBodega] = useState<Bodega | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    sede: '',
    usuarios_asignados: [] as number[],
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const getSedeName = useCallback((sedeId: number) => {
    return sedes.find(s => s.id === sedeId)?.nombre || 'N/A';
  }, [sedes]);

  const getAutoSedeId = (): string => {
    if (!sedes.length) return '';
    const sedeValida = selectedSedeId && sedes.some(s => s.id.toString() === selectedSedeId);
    return sedeValida ? String(selectedSedeId) : String(sedes[0].id);
  };

  useEffect(() => {
    if (!editingBodega && isOpen && !formData.sede && sedes.length > 0) {
      const auto = selectedSedeId && sedes.some(s => String(s.id) === String(selectedSedeId))
        ? String(selectedSedeId)
        : String(sedes[0].id);
      setFormData(prev => ({ ...prev, sede: auto }));
    }
  }, [editingBodega, isOpen, formData.sede, selectedSedeId, sedes]);

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

  const totalPages = Math.ceil(filteredBodegas.length / ITEMS_PER_PAGE);
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

  const paginatedBodegas = useMemo(() => {
    const startIndex = (safePage - 1) * ITEMS_PER_PAGE;
    return filteredBodegas.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredBodegas, safePage]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      sede: '',
      usuarios_asignados: [],
    });
    setErrors({});
    setEditingBodega(null);
  };

  const handleOpenNuevaBodega = () => {
    setEditingBodega(null);
    setErrors({});
    const autoSede = getAutoSedeId();
    setFormData({ nombre: '', sede: autoSede, usuarios_asignados: [] });
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.nombre.trim()) newErrors.nombre = 'El nombre es requerido';
    if (!editingBodega && !formData.sede) newErrors.sede = 'Selecciona una sede en el menú lateral';
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
              <Button onClick={handleOpenNuevaBodega}>
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
                  <Label htmlFor="sede">
                    Sede <span className="text-destructive">*</span>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="inline-block w-4 h-4 ml-1 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="max-w-xs">
                            {editingBodega
                              ? 'La sede de la bodega no se puede cambiar al editar.'
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
                  {errors.sede && <p className="text-sm text-destructive">{errors.sede}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nombre">Nombre <span className="text-destructive">*</span></Label>
                  <Input id="nombre" autoFocus value={formData.nombre} onChange={(e) => setFormData({ ...formData, nombre: e.target.value })} className={errors.nombre ? 'border-destructive' : ''} />
                  {errors.nombre && <p className="text-sm text-destructive">{errors.nombre}</p>}
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
                <Button variant="outline" onClick={() => { setIsOpen(false); resetForm(); }}>Cancelar</Button>
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
