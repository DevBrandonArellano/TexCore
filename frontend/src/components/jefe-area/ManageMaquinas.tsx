import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../../lib/axios'
import { Button } from '../ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
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
import { Textarea } from '../ui/textarea'
import type { MaquinaConMerma, ProductoDetail, BodegaDetail } from '../../types/produccion'

interface ManageMaquinasProps {
  areaId?: number
}

const ESTADO_BADGE: Record<string, 'default' | 'secondary' | 'destructive'> = {
  operativa: 'default',
  mantenimiento: 'secondary',
  inactiva: 'destructive',
}

export function ManageMaquinas({ areaId }: ManageMaquinasProps) {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MaquinaConMerma | null>(null)
  const [deleting, setDeleting] = useState<MaquinaConMerma | null>(null)
  const [justificacion, setJustificacion] = useState('')
  const [form, setForm] = useState({
    nombre: '',
    estado: 'operativa',
    capacidad_maxima: '',
    eficiencia_ideal: '0.85',
    producto_merma: '',
    bodega_merma: '',
  })

  const { data: maquinas = [] } = useQuery<MaquinaConMerma[]>({
    queryKey: ['maquinas', areaId],
    queryFn: () =>
      apiClient.get(`/maquinas/${areaId ? `?area=${areaId}` : ''}`).then(
        (r) => r.data.results ?? r.data,
      ),
  })

  const { data: productosMerma = [] } = useQuery<ProductoDetail[]>({
    queryKey: ['productos-merma'],
    queryFn: () =>
      apiClient.get('/productos/?tipo=merma').then((r) => r.data.results ?? r.data),
  })

  const { data: bodegas = [] } = useQuery<BodegaDetail[]>({
    queryKey: ['bodegas'],
    queryFn: () => apiClient.get('/bodegas/').then((r) => r.data.results ?? r.data),
  })

  const saveMutation = useMutation({
    mutationFn: (data: object) =>
      editing
        ? apiClient.patch(`/maquinas/${editing.id}/`, data)
        : apiClient.post('/maquinas/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maquinas'] })
      setDialogOpen(false)
      toast.success(editing ? 'Máquina actualizada' : 'Máquina creada')
    },
    onError: () => toast.error('Error al guardar la máquina'),
  })

  const deleteMutation = useMutation({
    mutationFn: ({ id, just }: { id: number; just: string }) =>
      apiClient.delete(`/maquinas/${id}/`, { data: { justificacion: just } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maquinas'] })
      setDeleteDialogOpen(false)
      toast.success('Máquina eliminada')
    },
    onError: () => toast.error('Error al eliminar'),
  })

  const openCreate = () => {
    setEditing(null)
    setForm({
      nombre: '', estado: 'operativa', capacidad_maxima: '',
      eficiencia_ideal: '0.85', producto_merma: '', bodega_merma: '',
    })
    setDialogOpen(true)
  }

  const openEdit = (m: MaquinaConMerma) => {
    setEditing(m)
    setForm({
      nombre: m.nombre,
      estado: m.estado,
      capacidad_maxima: m.capacidad_maxima,
      eficiencia_ideal: m.eficiencia_ideal,
      producto_merma: m.producto_merma?.toString() ?? '',
      bodega_merma: m.bodega_merma?.toString() ?? '',
    })
    setDialogOpen(true)
  }

  const handleSubmit = () => {
    saveMutation.mutate({
      nombre: form.nombre,
      estado: form.estado,
      capacidad_maxima: form.capacidad_maxima,
      eficiencia_ideal: form.eficiencia_ideal,
      producto_merma: form.producto_merma || null,
      bodega_merma: form.bodega_merma || null,
      ...(areaId ? { area: areaId } : {}),
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Máquinas</h3>
        <Button onClick={openCreate}>+ Nueva Máquina</Button>
      </div>

      <div className="border rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="p-3 text-left">Nombre</th>
              <th className="p-3 text-left">Estado</th>
              <th className="p-3 text-left">Cap. máx (kg/turno)</th>
              <th className="p-3 text-left">Producto Merma</th>
              <th className="p-3 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {maquinas.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-muted-foreground">
                  No hay máquinas registradas
                </td>
              </tr>
            )}
            {maquinas.map((m) => (
              <tr key={m.id} className="border-t hover:bg-muted/40 transition-colors">
                <td className="p-3 font-medium">{m.nombre}</td>
                <td className="p-3">
                  <Badge variant={ESTADO_BADGE[m.estado] ?? 'default'}>{m.estado}</Badge>
                </td>
                <td className="p-3">{m.capacidad_maxima} kg</td>
                <td className="p-3">
                  {m.producto_merma_detail ? (
                    <span className="text-green-700 font-medium">
                      {m.producto_merma_detail.codigo}
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-xs">Sin configurar</span>
                  )}
                </td>
                <td className="p-3 space-x-2">
                  <Button size="sm" variant="outline" onClick={() => openEdit(m)}>
                    Editar
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => {
                      setDeleting(m)
                      setJustificacion('')
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
            <DialogTitle>{editing ? 'Editar Máquina' : 'Nueva Máquina'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Nombre</Label>
              <Input
                value={form.nombre}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                placeholder="Ej: Máquina de Hilado 01"
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
                  <SelectItem value="operativa">Operativa</SelectItem>
                  <SelectItem value="mantenimiento">En Mantenimiento</SelectItem>
                  <SelectItem value="inactiva">Inactiva</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Capacidad máx. (kg/turno)</Label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.capacidad_maxima}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, capacidad_maxima: e.target.value }))
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Eficiencia ideal (0–1)</Label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={form.eficiencia_ideal}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, eficiencia_ideal: e.target.value }))
                  }
                />
              </div>
            </div>

            {/* Sección Merma Vendible */}
            <div className="border-t pt-4 space-y-3">
              <p className="text-sm font-medium text-muted-foreground">
                Configuración de Merma Vendible
              </p>

              <div className="space-y-2">
                <Label>Producto de Merma</Label>
                <Select
                  value={form.producto_merma}
                  onValueChange={(v) => setForm((f) => ({ ...f, producto_merma: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sin merma vendible" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Sin merma vendible</SelectItem>
                    {productosMerma.map((p) => (
                      <SelectItem key={p.id} value={p.id.toString()}>
                        {p.codigo} — {p.descripcion}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Bodega de Merma</Label>
                <Select
                  value={form.bodega_merma}
                  onValueChange={(v) => setForm((f) => ({ ...f, bodega_merma: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar bodega" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Sin bodega asignada</SelectItem>
                    {bodegas.map((b) => (
                      <SelectItem key={b.id} value={b.id.toString()}>
                        {b.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
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
            <AlertDialogTitle>Eliminar Máquina</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará "{deleting?.nombre}" permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-2 space-y-2">
            <Label>Justificación (mínimo 10 caracteres)</Label>
            <Textarea
              value={justificacion}
              onChange={(e) => setJustificacion(e.target.value)}
              placeholder="Ingrese el motivo de la eliminación..."
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={justificacion.length < 10 || deleteMutation.isPending}
              onClick={() =>
                deleting &&
                deleteMutation.mutate({ id: deleting.id, just: justificacion })
              }
            >
              {deleteMutation.isPending ? 'Eliminando...' : 'Eliminar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
