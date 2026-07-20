import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../../lib/axios'
import { Button } from '../ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog'
import { Label } from '../ui/label'
import { Input } from '../ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select'
import { Badge } from '../ui/badge'
import { toast } from 'sonner'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../ui/alert-dialog'
import { Checkbox } from '../ui/checkbox'
import { ScrollArea } from '../ui/scroll-area'
import type { LineaProduccion, Maquina } from '../../lib/types'

interface ManageLineasProps {
  areaId?: number
  onChange?: () => void
}

const ESTADO_BADGE: Record<string, 'default' | 'secondary' | 'destructive'> = {
  activa: 'default',
  inactiva: 'destructive',
}

export function ManageLineas({ areaId, onChange }: ManageLineasProps) {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<LineaProduccion | null>(null)
  const [deleting, setDeleting] = useState<LineaProduccion | null>(null)
  const [form, setForm] = useState({
    nombre: '',
    descripcion: '',
    estado: 'activa',
    maquinas: [] as number[],
  })

  const { data: lineas = [] } = useQuery<LineaProduccion[]>({
    queryKey: ['lineas-produccion', areaId],
    queryFn: () =>
      apiClient
        .get(`/lineas-produccion/${areaId ? `?area=${areaId}` : ''}`)
        .then((r) => r.data.results ?? r.data),
  })

  const { data: maquinas = [] } = useQuery<Maquina[]>({
    queryKey: ['maquinas', areaId],
    queryFn: () =>
      apiClient
        .get(`/maquinas/${areaId ? `?area=${areaId}` : ''}`)
        .then((r) => r.data.results ?? r.data),
  })

  const saveMutation = useMutation({
    mutationFn: (data: object) =>
      editing
        ? apiClient.patch(`/lineas-produccion/${editing.id}/`, data)
        : apiClient.post('/lineas-produccion/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lineas-produccion'] })
      setDialogOpen(false)
      toast.success(editing ? 'Línea actualizada' : 'Línea creada')
      onChange?.()
    },
    onError: () => toast.error('Error al guardar la línea'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/lineas-produccion/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lineas-produccion'] })
      setDeleteDialogOpen(false)
      toast.success('Línea eliminada')
      onChange?.()
    },
    onError: () => toast.error('Error al eliminar'),
  })

  const openCreate = () => {
    setEditing(null)
    setForm({ nombre: '', descripcion: '', estado: 'activa', maquinas: [] })
    setDialogOpen(true)
  }

  const openEdit = (l: LineaProduccion) => {
    setEditing(l)
    setForm({
      nombre: l.nombre,
      descripcion: l.descripcion ?? '',
      estado: l.estado,
      maquinas: [...l.maquinas],
    })
    setDialogOpen(true)
  }

  const toggleMaquina = (id: number) => {
    setForm((f) => ({
      ...f,
      maquinas: f.maquinas.includes(id)
        ? f.maquinas.filter((mid) => mid !== id)
        : [...f.maquinas, id],
    }))
  }

  const handleSubmit = () => {
    saveMutation.mutate({
      nombre: form.nombre,
      descripcion: form.descripcion || null,
      estado: form.estado,
      maquinas: form.maquinas,
      ...(areaId ? { area: areaId } : {}),
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Líneas</h3>
        <Button onClick={openCreate}>+ Nueva Línea</Button>
      </div>

      <div className="border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="p-3 text-left">Nombre</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3 text-left">Máquinas</th>
              <th className="p-3 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {lineas.length === 0 && (
              <tr>
                <td colSpan={4} className="p-6 text-center text-muted-foreground">
                  No hay líneas de producción registradas
                </td>
              </tr>
            )}
            {lineas.map((l) => (
              <tr key={l.id} className="border-t hover:bg-muted/40 transition-colors">
                <td className="p-3 font-medium">{l.nombre}</td>
                <td className="p-3">
                  <Badge variant={ESTADO_BADGE[l.estado] ?? 'default'}>{l.estado}</Badge>
                </td>
                <td className="p-3">
                  <div className="flex flex-wrap gap-1">
                    {(l.maquinas_detail ?? []).map((d) => (
                      <Badge key={d.id} variant="outline" className="text-xs">
                        {d.nombre}
                      </Badge>
                    ))}
                    {(l.maquinas_detail ?? []).length === 0 && (
                      <span className="text-muted-foreground text-xs">Sin máquinas</span>
                    )}
                  </div>
                </td>
                <td className="p-3 space-x-2">
                  <Button size="sm" variant="outline" onClick={() => openEdit(l)}>
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => {
                      setDeleting(l)
                      setDeleteDialogOpen(true)
                    }}
                  >
                    Eliminar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Dialog Crear / Editar */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? 'Editar Línea' : 'Nueva Línea de Producción'}</DialogTitle>
            <DialogDescription>
              Agrupa máquinas del área en una célula de manufactura flexible.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input
                value={form.nombre}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                placeholder="Ej: Línea de Tintura A"
              />
            </div>

            <div className="space-y-2">
              <Label>Descripción (opcional)</Label>
              <Input
                value={form.descripcion}
                onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
                placeholder="Descripción breve..."
              />
            </div>

            <div className="space-y-2">
              <Label>Estado</Label>
              <Select
                value={form.estado}
                onValueChange={(v) => setForm((f) => ({ ...f, estado: v }))}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="activa">Activa</SelectItem>
                  <SelectItem value="inactiva">Inactiva</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Máquinas asignadas</Label>
              <ScrollArea className="h-32 border rounded-md p-2 bg-slate-50">
                <div className="space-y-2">
                  {maquinas.map((m) => (
                    <div key={m.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`m-${m.id}`}
                        checked={form.maquinas.includes(m.id)}
                        onCheckedChange={() => toggleMaquina(m.id)}
                      />
                      <Label htmlFor={`m-${m.id}`} className="text-sm font-normal cursor-pointer">
                        {m.nombre}
                      </Label>
                    </div>
                  ))}
                  {maquinas.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-4">
                      No hay máquinas en esta área.
                    </p>
                  )}
                </div>
              </ScrollArea>
            </div>

            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!form.nombre || saveMutation.isPending}
            >
              {saveMutation.isPending ? 'Guardando...' : 'Guardar'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* AlertDialog Eliminar */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Eliminar Línea</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará "{deleting?.nombre}" permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteMutation.isPending}
              onClick={() => deleting && deleteMutation.mutate(deleting.id)}
            >
              {deleteMutation.isPending ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
