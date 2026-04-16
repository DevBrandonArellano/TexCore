import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Quimico } from '../../lib/types';
import { Beaker, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageQuimicosProps {
  quimicos: Quimico[];
  onChemicalCreate: (chemicalData: any) => Promise<boolean>;
  onChemicalUpdate: (chemicalId: number, chemicalData: any) => Promise<boolean>;
  onChemicalDelete: (chemicalId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 20;

export function ManageQuimicos({ quimicos, onChemicalCreate, onChemicalUpdate, onChemicalDelete, loading }: ManageQuimicosProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingQuimico, setEditingQuimico] = useState<Quimico | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    descripcion: '',
    unidad_medida: 'kg',
    presentacion: '',
    precio_base: '0',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const filteredQuimicos = useMemo(() => {
    return quimicos.filter(quimico =>
      (quimico as any).codigo?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (quimico as any).descripcion?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [quimicos, searchTerm]);

  const totalPages = Math.ceil(filteredQuimicos.length / ITEMS_PER_PAGE);
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

  const paginatedQuimicos = useMemo(() => {
    const startIndex = (safePage - 1) * ITEMS_PER_PAGE;
    return filteredQuimicos.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredQuimicos, safePage]);

  const resetForm = () => {
    setFormData({
      codigo: '',
      descripcion: '',
      unidad_medida: 'kg',
      presentacion: '',
      precio_base: '0',
    });
    setErrors({});
    setEditingQuimico(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
    if (!formData.descripcion.trim()) newErrors.descripcion = 'La descripción es requerida';
    if (!formData.unidad_medida.trim()) newErrors.unidad_medida = 'La unidad de medida es requerida';
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
      tipo: 'quimico',
      precio_base: parseFloat(formData.precio_base) || 0
    };

    let success = false;
    if (editingQuimico) {
      success = await onChemicalUpdate(editingQuimico.id, dataToSend);
    } else {
      success = await onChemicalCreate(dataToSend);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (quimico: any) => {
    setEditingQuimico(quimico);
    setFormData({
      codigo: quimico.codigo || '',
      descripcion: quimico.descripcion || '',
      unidad_medida: quimico.unidad_medida || 'kg',
      presentacion: quimico.presentacion || '',
      precio_base: quimico.precio_base?.toString() || '0',
    });
    setIsOpen(true);
  };

  return (
    <Card className="flex flex-col h-full min-h-0">
      <CardHeader className="flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Químicos</CardTitle>
            <CardDescription>Administra los químicos del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button onClick={() => resetForm()}>
                <Beaker className="w-4 h-4 mr-2" />
                Nuevo Químico
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingQuimico ? 'Editar Químico' : 'Nuevo Químico'}</DialogTitle>
                <DialogDescription>
                  {editingQuimico ? 'Modifica la información del químico' : 'Completa el formulario para crear un nuevo químico'}
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
                  <Label htmlFor="unidad_medida">Unidad de Medida <span className="text-destructive">*</span></Label>
                  <Select value={formData.unidad_medida} onValueChange={(v) => setFormData({ ...formData, unidad_medida: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona unidad" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="kg">Kilogramos (kg)</SelectItem>
                      <SelectItem value="gr">Gramos (gr)</SelectItem>
                      <SelectItem value="lb">Libras (lb)</SelectItem>
                      <SelectItem value="l">Litros (l)</SelectItem>
                      <SelectItem value="ml">Mililitros (ml)</SelectItem>
                      <SelectItem value="gl">Galones (gl)</SelectItem>
                      <SelectItem value="metros">Metros (m)</SelectItem>
                      <SelectItem value="unidades">Unidades (u)</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.unidad_medida && <p className="text-sm text-destructive">{errors.unidad_medida}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="presentacion">Presentación (Ej: Galón, Saco 25kg)</Label>
                  <Input id="presentacion" value={formData.presentacion} onChange={(e) => setFormData({ ...formData, presentacion: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="precio_base">Precio Base (Opcional)</Label>
                  <Input id="precio_base" type="number" value={formData.precio_base} onChange={(e) => setFormData({ ...formData, precio_base: e.target.value })} />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => { setIsOpen(false); resetForm(); }}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingQuimico ? 'Actualizar' : 'Crear'} Químico</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por código o nombre..."
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
      <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
        <div className="flex-1 overflow-auto rounded-md border relative">
          <Table className="min-w-max">
            <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>Presentación</TableHead>
                <TableHead>Unidad</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-40" /></TableCell>
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
                paginatedQuimicos.map((quimico: any) => (
                  <TableRow key={quimico.id}>
                    <TableCell className="font-mono text-xs">{quimico.codigo}</TableCell>
                    <TableCell>{quimico.descripcion}</TableCell>
                    <TableCell>{quimico.presentacion || '-'}</TableCell>
                    <TableCell>{quimico.unidad_medida}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(quimico)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onChemicalDelete(quimico.id)}
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
        <div className="flex items-center justify-between mt-4 flex-shrink-0">
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
