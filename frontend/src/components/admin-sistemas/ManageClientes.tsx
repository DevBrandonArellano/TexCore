import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Cliente } from '../../lib/types';
import { Users, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface ManageClientesProps {
  clientes: Cliente[];
  onClienteCreate: (clienteData: any) => Promise<boolean>;
  onClienteUpdate: (clienteId: number, clienteData: any) => Promise<boolean>;
  onClienteDelete: (clienteId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageClientes({ clientes, onClienteCreate, onClienteUpdate, onClienteDelete, loading }: ManageClientesProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingCliente, setEditingCliente] = useState<Cliente | null>(null);
  const [formData, setFormData] = useState({
    ruc_cedula: '',
    nombre_razon_social: '',
    direccion_envio: '',
    nivel_precio: 'normal' as 'mayorista' | 'normal',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredClientes = useMemo(() => {
    return clientes.filter(cliente =>
      cliente.ruc_cedula.toLowerCase().includes(searchTerm.toLowerCase()) ||
      cliente.nombre_razon_social.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [clientes, searchTerm]);

  const paginatedClientes = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredClientes.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredClientes, currentPage]);

  const totalPages = Math.ceil(filteredClientes.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      ruc_cedula: '',
      nombre_razon_social: '',
      direccion_envio: '',
      nivel_precio: 'normal',
    });
    setErrors({});
    setEditingCliente(null);
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.ruc_cedula.trim()) newErrors.ruc_cedula = 'El RUC/Cédula es requerido';
    if (!formData.nombre_razon_social.trim()) newErrors.nombre_razon_social = 'El Nombre/Razón Social es requerido';
    if (!formData.direccion_envio.trim()) newErrors.direccion_envio = 'La dirección es requerida';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    let success = false;
    if (editingCliente) {
      success = await onClienteUpdate(editingCliente.id, formData);
    } else {
      success = await onClienteCreate(formData);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (cliente: Cliente) => {
    setEditingCliente(cliente);
    setFormData({
      ruc_cedula: cliente.ruc_cedula,
      nombre_razon_social: cliente.nombre_razon_social,
      direccion_envio: cliente.direccion_envio,
      nivel_precio: cliente.nivel_precio,
    });
    setIsOpen(true);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Clientes</CardTitle>
            <CardDescription>Administra los clientes del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <Users className="w-4 h-4 mr-2" />
                Nuevo Cliente
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingCliente ? 'Editar Cliente' : 'Nuevo Cliente'}</DialogTitle>
                <DialogDescription>
                  {editingCliente ? 'Modifica la información del cliente' : 'Completa el formulario para crear un nuevo cliente'}
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="ruc_cedula">RUC/Cédula <span className="text-destructive">*</span></Label>
                  <Input id="ruc_cedula" value={formData.ruc_cedula} onChange={(e) => setFormData({ ...formData, ruc_cedula: e.target.value })} className={errors.ruc_cedula ? 'border-destructive' : ''} />
                  {errors.ruc_cedula && <p className="text-sm text-destructive">{errors.ruc_cedula}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nombre_razon_social">Nombre / Razón Social <span className="text-destructive">*</span></Label>
                  <Input id="nombre_razon_social" value={formData.nombre_razon_social} onChange={(e) => setFormData({ ...formData, nombre_razon_social: e.target.value })} className={errors.nombre_razon_social ? 'border-destructive' : ''} />
                  {errors.nombre_razon_social && <p className="text-sm text-destructive">{errors.nombre_razon_social}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="direccion_envio">Dirección de Envío <span className="text-destructive">*</span></Label>
                  <Input id="direccion_envio" value={formData.direccion_envio} onChange={(e) => setFormData({ ...formData, direccion_envio: e.target.value })} className={errors.direccion_envio ? 'border-destructive' : ''} />
                  {errors.direccion_envio && <p className="text-sm text-destructive">{errors.direccion_envio}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="nivel_precio">Nivel de Precio</Label>
                  <Select value={formData.nivel_precio} onValueChange={(value) => setFormData({ ...formData, nivel_precio: value as any })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona un nivel" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="normal">Normal</SelectItem>
                      <SelectItem value="mayorista">Mayorista</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>Cancelar</Button>
                <Button onClick={handleSubmit}>{editingCliente ? 'Actualizar' : 'Crear'} Cliente</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por RUC/Cédula o nombre..."
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
                <TableHead>RUC/Cédula</TableHead>
                <TableHead>Nombre / Razón Social</TableHead>
                <TableHead>Dirección</TableHead>
                <TableHead>Nivel de Precio</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-40" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-48" /></TableCell>
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
                paginatedClientes.map((cliente) => (
                  <TableRow key={cliente.id}>
                    <TableCell>{cliente.ruc_cedula}</TableCell>
                    <TableCell>{cliente.nombre_razon_social}</TableCell>
                    <TableCell>{cliente.direccion_envio}</TableCell>
                    <TableCell>{cliente.nivel_precio}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(cliente)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onClienteDelete(cliente.id)}
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
