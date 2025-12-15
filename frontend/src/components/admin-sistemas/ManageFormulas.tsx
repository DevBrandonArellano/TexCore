import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { FormulaColor } from '../../lib/types';
import { Palette, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageFormulasProps {
  formulas: FormulaColor[];
  onFormulaCreate: (formulaData: any) => Promise<boolean>;
  onFormulaUpdate: (formulaId: number, formulaData: any) => Promise<boolean>;
  onFormulaDelete: (formulaId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageFormulas({ formulas, onFormulaCreate, onFormulaUpdate, onFormulaDelete, loading }: ManageFormulasProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingFormula, setEditingFormula] = useState<FormulaColor | null>(null);
  const [formData, setFormData] = useState({
    codigo: '',
    nombre_color: '',
    description: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredFormulas = useMemo(() => {
    return formulas.filter(formula =>
      formula.codigo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      formula.nombre_color.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [formulas, searchTerm]);

  const paginatedFormulas = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredFormulas.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredFormulas, currentPage]);

  const totalPages = Math.ceil(filteredFormulas.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      codigo: '',
      nombre_color: '',
      description: '',
    });
    setErrors({});
    setEditingFormula(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.codigo.trim()) newErrors.codigo = 'El código es requerido';
    if (!formData.nombre_color.trim()) newErrors.nombre_color = 'El nombre del color es requerido';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    // The backend expects 'chemicals' to be an array of numbers.
    // For now, we'll send an empty array or the existing one if editing.
    const formulaDataToSend = {
      ...formData,
      chemicals: editingFormula ? editingFormula.chemicals : [],
    };

    let success = false;
    if (editingFormula) {
      success = await onFormulaUpdate(editingFormula.id, formulaDataToSend);
    } else {
      success = await onFormulaCreate(formulaDataToSend);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (formula: FormulaColor) => {
    setEditingFormula(formula);
    setFormData({
      codigo: formula.codigo,
      nombre_color: formula.nombre_color,
      description: formula.description,
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Fórmulas</CardTitle>
            <CardDescription>Administra las fórmulas de color del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <Palette className="w-4 h-4 mr-2" />
                Nueva Fórmula
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingFormula ? 'Editar Fórmula' : 'Nueva Fórmula'}</DialogTitle>
                <DialogDescription>
                  {editingFormula ? 'Modifica la información de la fórmula' : 'Completa el formulario para crear una nueva fórmula'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="codigo">Código <span className="text-destructive">*</span></Label>
                  <Input id="codigo" value={formData.codigo} onChange={(e) => setFormData({ ...formData, codigo: e.target.value })} className={errors.codigo ? 'border-destructive' : ''} />
                  {errors.codigo && <p className="text-sm text-destructive">{errors.codigo}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nombre_color">Nombre del Color <span className="text-destructive">*</span></Label>
                  <Input id="nombre_color" value={formData.nombre_color} onChange={(e) => setFormData({ ...formData, nombre_color: e.target.value })} className={errors.nombre_color ? 'border-destructive' : ''} />
                  {errors.nombre_color && <p className="text-sm text-destructive">{errors.nombre_color}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Descripción</Label>
                  <Input id="description" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingFormula ? 'Actualizar' : 'Crear'} Fórmula</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por código o nombre de color..."
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
                <TableHead>Nombre del Color</TableHead>
                <TableHead>Descripción</TableHead>
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
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Skeleton className="h-8 w-8" />
                        <Skeleton className="h-8 w-8" />
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                paginatedFormulas.map((formula) => (
                  <TableRow key={formula.id}>
                    <TableCell className="font-mono text-xs">{formula.codigo}</TableCell>
                    <TableCell>{formula.nombre_color}</TableCell>
                    <TableCell>{formula.description}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(formula)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onFormulaDelete(formula.id)}
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
