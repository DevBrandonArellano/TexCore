import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Badge } from '../ui/badge';
import { User, Sede, Area } from '../../lib/types';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { UserPlus, Pencil, Trash2, ChevronLeft, ChevronRight, Info } from 'lucide-react';
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
  // Sede seleccionada en el sidebar del AdminSistemasDashboard (para asignación automática)
  selectedSedeId?: string;
  onUserCreate: (userData: any) => Promise<boolean>;
  onUserUpdate: (userId: number, userData: any) => Promise<boolean>;
  onUserDelete: (userId: number) => void;
  loading: boolean;
}

const ITEMS_PER_PAGE = 20;

export function ManageUsers({ users, sedes, areas, groups, selectedSedeId, onUserCreate, onUserUpdate, onUserDelete, loading }: ManageUsersProps) {
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
  const [searchParams, setSearchParams] = useSearchParams();
  const searchTerm = searchParams.get('search') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);

  const roleLabels: Record<string, string> = {
    operario: 'Operario',
    jefe_area: 'Jefe de Área',
    jefe_planta: 'Jefe de Planta',
    admin_sede: 'Administrador de Sede',
    ejecutivo: 'Ejecutivo',
    admin_sistemas: 'Administrador de Sistemas',
    despacho: 'Despacho',
    bodeguero: 'Bodeguero',
    vendedor: 'Vendedor',
    empaquetado: 'Empaquetado'
  };

  const filteredUsers = useMemo(() => {
    return users.filter(user =>
      user.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [users, searchTerm]);

  const totalPages = Math.ceil(filteredUsers.length / ITEMS_PER_PAGE);
  const safeTotalPages = Math.max(1, totalPages);
  const safePage = Math.min(Math.max(1, currentPage), safeTotalPages);

  const getAutoSedeId = (): string => {
    if (!sedes.length) return '';
    const sedeValida = selectedSedeId && sedes.some(s => String(s.id) === String(selectedSedeId));
    return sedeValida ? String(selectedSedeId) : String(sedes[0].id);
  };

  // Asignación automática de sede al crear (cuando el rol la requiere)
  useEffect(() => {
    if (editingUser) return;
    if (!formData.groups[0]) return;
    const groupName = getGroupName(formData.groups[0]);
    if (!groupName || groupName === 'admin_sistemas') return;
    if (formData.sede) return;
    if (!sedes.length) return;
    setFormData(prev => ({ ...prev, sede: getAutoSedeId() }));
  }, [editingUser, formData.groups, formData.sede, sedes, selectedSedeId]);

  useEffect(() => {
    if (currentPage !== safePage) {
      setSearchParams(prev => {
        prev.set('page', String(safePage));
        return prev;
      }, { replace: true });
    }
  }, [currentPage, safePage, setSearchParams]);

  const paginatedUsers = useMemo(() => {
    const startIndex = (safePage - 1) * ITEMS_PER_PAGE;
    return filteredUsers.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [filteredUsers, safePage]);

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
    <Card className="flex flex-col h-full min-h-0">
      <CardHeader className="flex-shrink-0">
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
              <Button onClick={() => {
                setEditingUser(null);
                setErrors({});
                setFormData({
                  username: '', password: '', first_name: '', last_name: '', email: '',
                  groups: [], sede: getAutoSedeId(), area: ''
                });
              }}>
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
                    autoComplete="off"
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
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Info className="inline-block w-4 h-4 ml-1 text-muted-foreground cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-xs">
                                  La sede se asigna automáticamente según la selección del menú lateral. No se puede modificar.
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
                <Button variant="outline" onClick={() => { setIsOpen(false); resetForm(); }}>
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
          {/* Campos señuelo para evitar que el navegador autofille el buscador con emails recientes */}
          <div aria-hidden="true" className="hidden">
            <input type="text" name="fake-username" autoComplete="username" tabIndex={-1} />
            <input type="password" name="fake-password" autoComplete="new-password" tabIndex={-1} />
          </div>
          <Input
            type="search"
            placeholder="Buscar por nombre, usuario, email..."
            name="users-search-no-autofill"
            autoComplete="new-password"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
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
