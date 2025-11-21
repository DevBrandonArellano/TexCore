import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Quimico } from '../../lib/types';
import { Beaker, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageQuimicosProps {
  quimicos: Quimico[];
  onChemicalCreate: (chemicalData: any) => Promise<boolean>;
  onChemicalUpdate: (chemicalId: number, chemicalData: any) => Promise<boolean>;
  onChemicalDelete: (chemicalId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageQuimicos({ quimicos, onChemicalCreate, onChemicalUpdate, onChemicalDelete, loading }: ManageQuimicosProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingQuimico, setEditingQuimico] = useState<Quimico | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    unit_of_measure: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredQuimicos = useMemo(() => {
    return quimicos.filter(quimico =>
      quimico.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      quimico.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [quimicos, searchTerm]);

  const paginatedQuimicos = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredQuimicos.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredQuimicos, currentPage]);

  const totalPages = Math.ceil(filteredQuimicos.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      code: '',
      name: '',
      description: '',
      unit_of_measure: '',
    });
    setErrors({});
    setEditingQuimico(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.code.trim()) newErrors.code = 'El código es requerido';
    if (!formData.name.trim()) newErrors.name = 'El nombre es requerido';
    if (!formData.unit_of_measure.trim()) newErrors.unit_of_measure = 'La unidad de medida es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    let success = false;
    if (editingQuimico) {
      success = await onChemicalUpdate(editingQuimico.id, formData);
    } else {
      success = await onChemicalCreate(formData);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (quimico: Quimico) => {
    setEditingQuimico(quimico);
    setFormData({
      code: quimico.code,
      name: quimico.name,
      description: quimico.description,
      unit_of_measure: quimico.unit_of_measure,
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
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
              <Button>
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
                  <Label htmlFor="code">Código <span className="text-destructive">*</span></Label>
                  <Input id="code" value={formData.code} onChange={(e) => setFormData({ ...formData, code: e.target.value })} className={errors.code ? 'border-destructive' : ''} />
                  {errors.code && <p className="text-sm text-destructive">{errors.code}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Nombre <span className="text-destructive">*</span></Label>
                  <Input id="name" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className={errors.name ? 'border-destructive' : ''} />
                  {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Descripción</Label>
                  <Input id="description" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit_of_measure">Unidad de Medida <span className="text-destructive">*</span></Label>
                  <Input id="unit_of_measure" value={formData.unit_of_measure} onChange={(e) => setFormData({ ...formData, unit_of_measure: e.target.value })} className={errors.unit_of_measure ? 'border-destructive' : ''} />
                  {errors.unit_of_measure && <p className="text-sm text-destructive">{errors.unit_of_measure}</p>}
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
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
                <TableHead>Nombre</TableHead>
                <TableHead>Descripción</TableHead>
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
                paginatedQuimicos.map((quimico) => (
                  <TableRow key={quimico.id}>
                    <TableCell className="font-mono text-xs">{quimico.code}</TableCell>
                    <TableCell>{quimico.name}</TableCell>
                    <TableCell>{quimico.description}</TableCell>
                    <TableCell>{quimico.unit_of_measure}</TableCell>
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
