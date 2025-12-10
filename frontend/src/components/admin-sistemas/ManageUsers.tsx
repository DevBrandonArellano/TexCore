import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { User, Sede, Area } from '../../lib/types';
import { UserPlus, Pencil, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '../ui/skeleton';

interface Group {
  id: number;
  name: string;
}

interface ManageUsersProps {
  users: User[];
  sedes: Sede[];
  areas: Area[];
  groups: Group[];
  onUserCreate: (userData: any) => Promise<boolean>;
  onUserUpdate: (userId: number, userData: any) => Promise<boolean>;
  onUserDelete: (userId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 10;

export function ManageUsers({ users, sedes, areas, groups, onUserCreate, onUserUpdate, onUserDelete, loading }: ManageUsersProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: '',
    groups: [] as number[],
    sede: '',
    area: ''
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const roleLabels: Record<string, string> = {
    operario: 'Operario',
    jefe_area: 'Jefe de Área',
    jefe_planta: 'Jefe de Planta',
    admin_sede: 'Administrador de Sede',
    ejecutivo: 'Ejecutivo',
    admin_sistemas: 'Administrador de Sistemas'
  };

  const filteredUsers = useMemo(() => {
    return users.filter(user =>
      user.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [users, searchTerm]);

  const paginatedUsers = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredUsers.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredUsers, currentPage]);

  const totalPages = Math.ceil(filteredUsers.length / ITEMS_PER_PAGE);

  const resetForm = () => {
    setFormData({
      username: '',
      password: '',
      first_name: '',
      last_name: '',
      email: '',
      groups: [],
      sede: '',
      area: ''
    });
    setErrors({});
    setEditingUser(null);
  };

  const getGroupName = (groupId: number): string | undefined => {
    return groups.find(g => g.id === groupId)?.name;
  }

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) newErrors.username = 'El usuario es requerido';
    if (!editingUser && !formData.password.trim()) newErrors.password = 'La contraseña es requerida';
    if (!formData.first_name.trim()) newErrors.first_name = 'El nombre es requerido';
    if (!formData.last_name.trim()) newErrors.last_name = 'El apellido es requerido';
    // Email es opcional, pero si se provee, debe ser válido
    if (formData.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'El email no es válido';
    }
    if (formData.groups.length === 0) newErrors.groups = 'El rol es requerido';

    const groupName = getGroupName(formData.groups[0]);
    if (groupName && groupName !== 'admin_sistemas') {
      if (!formData.sede) newErrors.sede = 'La sede es requerida para este rol';
    }
    if (groupName && ['operario', 'jefe_area'].includes(groupName)) {
      if (!formData.area) newErrors.area = 'El área es requerida para este rol';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) {
      toast.error('Por favor completa todos los campos requeridos');
      return;
    }

    const userDataToSend = {
      ...formData,
      sede: formData.sede ? parseInt(formData.sede, 10) : null,
      area: formData.area ? parseInt(formData.area, 10) : null,
      password: formData.password || undefined,
    };

    let success = false;
    if (editingUser) {
      success = await onUserUpdate(editingUser.id, userDataToSend);
    } else {
      success = await onUserCreate(userDataToSend);
    }

    if (success) {
      setIsOpen(false);
      resetForm();
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: '',
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
      groups: user.groups.map(g => typeof g === 'number' ? g : parseInt(g)),
      sede: user.sede?.toString() || '',
      area: user.area?.toString() || ''
    });
    setIsOpen(true);
  };

  const handleDelete = (userId: number) => {
    onUserDelete(userId);
  };

  const filteredAreas = formData.sede
    ? areas.filter(a => a.sede.toString() === formData.sede)
    : areas;
    
  const getGroupDisplayName = (user: User) => {
      if (!user.groups || user.groups.length === 0) return 'N/A';
      const groupId = typeof user.groups[0] === 'string' ? parseInt(user.groups[0]) : user.groups[0];
      const groupName = getGroupName(groupId);
      if (!groupName) return 'Rol Desconocido';
      return roleLabels[groupName] || groupName;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle>Gestión de Usuarios</CardTitle>
            <CardDescription>Administra los usuarios del sistema</CardDescription>
          </div>
          <Dialog open={isOpen} onOpenChange={(open) => {
            setIsOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="w-4 h-4 mr-2" />
                Nuevo Usuario
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
                </DialogTitle>
                <DialogDescription>
                  {editingUser ? 'Modifica la información del usuario' : 'Completa el formulario para crear un nuevo usuario'}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">
                      Usuario <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="username"
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className={errors.username ? 'border-destructive' : ''}
                    />
                    {errors.username && <p className="text-sm text-destructive">{errors.username}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">
                      {editingUser ? 'Nueva Contraseña (dejar vacío para no cambiar)' : 'Contraseña'} 
                      {!editingUser && <span className="text-destructive"> *</span>}
                    </Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      className={errors.password ? 'border-destructive' : ''}
                    />
                    {errors.password && <p className="text-sm text-destructive">{errors.password}</p>}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">
                      Nombre <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="first_name"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      className={errors.first_name ? 'border-destructive' : ''}
                    />
                    {errors.first_name && <p className="text-sm text-destructive">{errors.first_name}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="last_name">
                      Apellido <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="last_name"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      className={errors.last_name ? 'border-destructive' : ''}
                    />
                    {errors.last_name && <p className="text-sm text-destructive">{errors.last_name}</p>}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">
                    Email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className={errors.email ? 'border-destructive' : ''}
                  />
                  {errors.email && <p className="text-sm text-destructive">{errors.email}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="role">
                    Rol <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={formData.groups[0]?.toString() || ''}
                    onValueChange={(value) => setFormData({ ...formData, groups: [parseInt(value)] })}
                  >
                    <SelectTrigger id="role" className={errors.groups ? 'border-destructive' : ''}>
                      <SelectValue placeholder="Selecciona un rol" />
                    </SelectTrigger>
                    <SelectContent>
                      {groups.map(group => (
                        <SelectItem key={group.id} value={group.id.toString()}>
                          {roleLabels[group.name] || group.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.groups && <p className="text-sm text-destructive">{errors.groups}</p>}
                </div>

                {(() => {
                  const groupName = getGroupName(formData.groups[0]);
                  if (groupName && groupName !== 'admin_sistemas') {
                    return (
                      <div className="space-y-2">
                        <Label htmlFor="sede">
                          Sede <span className="text-destructive">*</span>
                        </Label>
                        <Select
                          value={formData.sede}
                          onValueChange={(value) => setFormData({ ...formData, sede: value, area: '' })}
                        >
                          <SelectTrigger id="sede" className={errors.sede ? 'border-destructive' : ''}>
                            <SelectValue placeholder="Selecciona una sede" />
                          </SelectTrigger>
                          <SelectContent>
                            {sedes.map(sede => (
                              <SelectItem key={sede.id} value={sede.id.toString()}>
                                {sede.nombre} - {sede.location}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.sede && <p className="text-sm text-destructive">{errors.sede}</p>}
                      </div>
                    );
                  }
                  return null;
                })()}

                {(() => {
                  const groupName = getGroupName(formData.groups[0]);
                  if (groupName && ['operario', 'jefe_area'].includes(groupName)) {
                    return (
                      <div className="space-y-2">
                        <Label htmlFor="area">
                          Área <span className="text-destructive">*</span>
                        </Label>
                        <Select
                          value={formData.area}
                          onValueChange={(value) => setFormData({ ...formData, area: value })}
                          disabled={!formData.sede}
                        >
                          <SelectTrigger id="area" className={errors.area ? 'border-destructive' : ''}>
                            <SelectValue placeholder={formData.sede ? "Selecciona un área" : "Primero selecciona una sede"} />
                          </SelectTrigger>
                          <SelectContent>
                            {filteredAreas.map(area => (
                              <SelectItem key={area.id} value={area.id.toString()}>
                                {area.nombre}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.area && <p className="text-sm text-destructive">{errors.area}</p>}
                      </div>
                    );
                  }
                  return null;
                })()}
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setIsOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleSubmit}>
                  {editingUser ? 'Actualizar' : 'Crear'} Usuario
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="mb-4">
          <Input
            placeholder="Buscar por nombre, usuario, email..."
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
                <TableHead>Usuario</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Rol</TableHead>
                <TableHead>Sede</TableHead>
                <TableHead>Área</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-5 w-20" /></TableCell>
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
                paginatedUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.first_name} {user.last_name}</TableCell>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{getGroupDisplayName(user)}</Badge>
                    </TableCell>
                    <TableCell>
                      {user.sede ? sedes.find(s => s.id === user.sede)?.nombre : '-'}
                    </TableCell>
                    <TableCell>
                      {user.area ? areas.find(a => a.id === user.area)?.nombre : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEdit(user)}
                        >
                          <Pencil className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDelete(user.id)}
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
