import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../../lib/axios'
import { Button } from '../ui/button'
import { Label } from '../ui/label'
import { Badge } from '../ui/badge'
import { toast } from 'sonner'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '../ui/alert-dialog'
import { Textarea } from '../ui/textarea'
import type { MaquinaConMerma } from '../../types/produccion'
import type { User } from '../../lib/types'
import { ProcesosMaquinaDialog } from './ProcesosMaquinaDialog'
import { MaquinaDialog } from './MaquinaDialog'

interface ManageMaquinasProps {
  areaId?: number
  /** Operarios del área: el formulario asigna los que controlan la máquina. */
  operarios: User[]
  /** Avisa al panel tras crear, editar o eliminar, para refrescar sus tarjetas. */
  onChange?: () => void
}

const ESTADO_BADGE: Record<string, 'default' | 'secondary' | 'destructive'> = {
  operativa: 'default',
  mantenimiento: 'secondary',
  inactiva: 'destructive',
}

export function ManageMaquinas({ areaId, operarios, onChange }: ManageMaquinasProps) {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MaquinaConMerma | null>(null)
  const [deleting, setDeleting] = useState<MaquinaConMerma | null>(null)
  const [conProcesos, setConProcesos] = useState<MaquinaConMerma | null>(null)
  const [justificacion, setJustificacion] = useState('')

  const { data: maquinas = [] } = useQuery<MaquinaConMerma[]>({
    queryKey: ['maquinas', areaId],
    queryFn: () =>
      apiClient.get(`/maquinas/${areaId ? `?area=${areaId}` : ''}`).then(
        (r) => r.data.results ?? r.data,
      ),
  })

  const deleteMutation = useMutation({
    mutationFn: ({ id, just }: { id: number; just: string }) =>
      apiClient.delete(`/maquinas/${id}/`, { data: { justificacion: just } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maquinas'] })
      setDeleteDialogOpen(false)
      toast.success('Máquina eliminada')
      onChange?.()
    },
    onError: () => toast.error('Error al eliminar'),
  })

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }

  const openEdit = (m: MaquinaConMerma) => {
    setEditing(m)
    setDialogOpen(true)
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
                  <Button size="sm" variant="outline" onClick={() => setConProcesos(m)}>
                    Procesos
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

      <ProcesosMaquinaDialog maquina={conProcesos} onClose={() => setConProcesos(null)} />

      <MaquinaDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        maquina={editing}
        operarios={operarios}
        areaId={areaId}
        onSaved={() => onChange?.()}
      />

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
