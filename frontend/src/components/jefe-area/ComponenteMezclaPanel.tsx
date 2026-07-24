import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import apiClient from '../../lib/axios'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../ui/select'
import { toast } from 'sonner'
import type { ComponenteMezclaOP, ProductoDetail, BodegaDetail } from '../../types/produccion'

interface Props {
  ordenId: number
  pesoNeto: number
  readonly?: boolean
}

const COLORS = [
  'hsl(210,70%,50%)', 'hsl(30,70%,50%)', 'hsl(120,50%,45%)',
  'hsl(280,60%,55%)', 'hsl(0,65%,50%)',
]

export function ComponenteMezclaPanel({ ordenId, pesoNeto, readonly = false }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ producto: '', bodega: '', porcentaje: '' })

  const { data: componentes = [] } = useQuery<ComponenteMezclaOP[]>({
    queryKey: ['componentes-mezcla', ordenId],
    queryFn: () =>
      apiClient.get(`/componentes-mezcla/?orden=${ordenId}`).then(
        (r) => r.data.results ?? r.data,
      ),
  })

  const { data: productos = [] } = useQuery<ProductoDetail[]>({
    queryKey: ['productos'],
    queryFn: () => apiClient.get('/productos/').then((r) => r.data.results ?? r.data),
  })

  const { data: bodegas = [] } = useQuery<BodegaDetail[]>({
    queryKey: ['bodegas'],
    queryFn: () => apiClient.get('/bodegas/').then((r) => r.data.results ?? r.data),
  })

  const addMutation = useMutation({
    mutationFn: (data: object) => apiClient.post('/componentes-mezcla/', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['componentes-mezcla', ordenId] })
      setForm({ producto: '', bodega: '', porcentaje: '' })
      toast.success('Componente agregado')
    },
    onError: (e: { response?: { data?: { non_field_errors?: string[] } } }) =>
      toast.error(
        e.response?.data?.non_field_errors?.[0] ?? 'Error al agregar componente',
      ),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      apiClient.delete(`/componentes-mezcla/${id}/`, {
        data: { justificacion: 'Eliminado por jefe de área' },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['componentes-mezcla', ordenId] })
      toast.success('Componente eliminado')
    },
    onError: () => toast.error('Error al eliminar'),
  })

  const totalPorcentaje = componentes.reduce(
    (sum, c) => sum + parseFloat(c.porcentaje),
    0,
  )
  const isValid = Math.abs(totalPorcentaje - 100) < 0.01

  return (
    <div className="space-y-4 border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">Receta de Mezcla</h4>
        <span
          className={`text-sm font-semibold ${isValid ? 'text-green-600' : 'text-destructive'}`}
        >
          Total: {totalPorcentaje.toFixed(1)}%{isValid ? ' ✓' : ' (debe ser 100%)'}
        </span>
      </div>

      {/* Barra visual */}
      {componentes.length > 0 && (
        <div className="h-4 rounded-full overflow-hidden flex">
          {componentes.map((c, i) => (
            <div
              key={c.id}
              style={{ width: `${c.porcentaje}%`, backgroundColor: COLORS[i % COLORS.length] }}
              title={`${c.producto_detail?.codigo ?? c.producto}: ${c.porcentaje}%`}
            />
          ))}
          {totalPorcentaje < 100 && (
            <div
              style={{ width: `${100 - totalPorcentaje}%` }}
              className="bg-muted"
            />
          )}
        </div>
      )}

      {/* Lista de componentes */}
      <div className="space-y-2">
        {componentes.map((c, i) => (
          <div
            key={c.id}
            className="flex items-center justify-between p-2 rounded bg-muted/50"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="text-sm font-medium">
                {c.producto_detail?.codigo ?? `Producto ${c.producto}`}
              </span>
              <span className="text-xs text-muted-foreground">
                desde {c.bodega_detail?.nombre ?? `Bodega ${c.bodega}`}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-semibold text-sm">{c.porcentaje}%</span>
              <span className="text-xs text-muted-foreground">
                ≈ {((parseFloat(c.porcentaje) * pesoNeto) / 100).toFixed(1)} kg
              </span>
              {!readonly && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                  onClick={() => deleteMutation.mutate(c.id)}
                  disabled={deleteMutation.isPending}
                >
                  ✕
                </Button>
              )}
            </div>
          </div>
        ))}
        {componentes.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-2">
            Sin componentes. Agrega al menos 2 para una mezcla.
          </p>
        )}
      </div>

      {/* Formulario agregar */}
      {!readonly && (
        <div className="grid grid-cols-3 gap-2 items-end border-t pt-3">
          <div className="space-y-1">
            <Label className="text-xs">Producto</Label>
            <Select
              value={form.producto}
              onValueChange={(v) => setForm((f) => ({ ...f, producto: v }))}
            >
              <SelectTrigger className="h-8">
                <SelectValue placeholder="Producto" />
              </SelectTrigger>
              <SelectContent>
                {productos.map((p) => (
                  <SelectItem key={p.id} value={p.id.toString()}>
                    {p.codigo}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Bodega</Label>
            <Select
              value={form.bodega}
              onValueChange={(v) => setForm((f) => ({ ...f, bodega: v }))}
            >
              <SelectTrigger className="h-8">
                <SelectValue placeholder="Bodega" />
              </SelectTrigger>
              <SelectContent>
                {bodegas.map((b) => (
                  <SelectItem key={b.id} value={b.id.toString()}>
                    {b.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">% Mezcla</Label>
            <div className="flex gap-1">
              <Input
                type="number"
                min="1"
                max="100"
                className="h-8"
                placeholder="50"
                value={form.porcentaje}
                onChange={(e) =>
                  setForm((f) => ({ ...f, porcentaje: e.target.value }))
                }
              />
              <Button
                size="sm"
                className="h-8 px-3"
                disabled={
                  !form.producto ||
                  !form.bodega ||
                  !form.porcentaje ||
                  addMutation.isPending
                }
                onClick={() =>
                  addMutation.mutate({
                    orden: ordenId,
                    producto: parseInt(form.producto),
                    bodega: parseInt(form.bodega),
                    porcentaje: form.porcentaje,
                  })
                }
              >
                +
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
