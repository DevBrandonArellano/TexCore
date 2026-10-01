import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { EstadoCarga } from '../lotes/paneles/EstadoCarga';
import { useCargaRemota } from '../../hooks/useCargaRemota';
import { indicadoresApi } from '../../lib/api/indicadoresApi';

const kg = (valor: number | string) => Number(valor).toFixed(3);

/** Desempeño de un operario: producción de hoy y sus últimos lotes. */
function DesempenoOperarioDialog({ operario, onClose }: {
  operario: { id: number; username: string } | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={operario !== null} onOpenChange={(abierto) => { if (!abierto) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Desempeño de {operario?.username}</DialogTitle>
          <DialogDescription>Producción de hoy y últimos lotes registrados.</DialogDescription>
        </DialogHeader>
        {operario && <DesempenoContenido operarioId={operario.id} />}
      </DialogContent>
    </Dialog>
  );
}

function DesempenoContenido({ operarioId }: { operarioId: number }) {
  const { datos, cargando, error } = useCargaRemota(() => indicadoresApi.desempenoOperario(operarioId), operarioId);
  return (
    <EstadoCarga cargando={cargando} error={error}>
      {datos && (
        <div className="space-y-3">
          <p className="text-sm">
            Hoy: <strong className="font-mono">{kg(datos.produccion_hoy_kg)} kg</strong> en {datos.lotes_hoy} lotes.
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Lote</TableHead>
                <TableHead>Máquina</TableHead>
                <TableHead>Turno</TableHead>
                <TableHead className="text-right">Peso (kg)</TableHead>
                <TableHead>Fin</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {datos.ultimos_lotes.map((l) => (
                <TableRow key={l.id}>
                  <TableCell className="font-mono">{l.codigo_lote}</TableCell>
                  <TableCell>{l.maquina_nombre ?? '—'}</TableCell>
                  <TableCell>{l.turno}</TableCell>
                  <TableCell className="text-right font-mono">{l.peso_neto_producido}</TableCell>
                  <TableCell>{l.hora_final ? new Date(l.hora_final).toLocaleString('es-EC') : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </EstadoCarga>
  );
}

/**
 * Reporte de eficiencia del día del área: producción y eficiencia por máquina,
 * y productividad por operario. Al elegir un operario se abre su desempeño.
 */
export function ReporteEficienciaArea({ areaId }: { areaId: number }) {
  const { datos, cargando, error, recargar } = useCargaRemota(
    () => indicadoresApi.reporteEficienciaArea(areaId), areaId);
  const [operario, setOperario] = useState<{ id: number; username: string } | null>(null);
  const sinProduccion = !!datos && datos.maquinas.length === 0 && datos.operarios.length === 0;

  return (
    <Card className="flex-shrink-0">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle>Eficiencia del día</CardTitle>
          <CardDescription>
            {datos
              ? `${datos.area_nombre}: ${kg(datos.produccion_total_area)} kg · eficiencia promedio ${datos.eficiencia_promedio_area} %`
              : 'Producción y eficiencia por máquina y por operario.'}
          </CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={recargar} disabled={cargando}>Actualizar</Button>
      </CardHeader>
      <CardContent>
        <EstadoCarga cargando={cargando} error={error} vacio={sinProduccion}
          mensajeVacio="Sin producción registrada hoy en el área.">
          {datos && (
            <div className="grid gap-6 lg:grid-cols-2">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Máquina</TableHead>
                    <TableHead className="text-right">Producción (kg)</TableHead>
                    <TableHead className="text-right">Eficiencia</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {datos.maquinas.map((m) => (
                    <TableRow key={m.maquina_id}>
                      <TableCell>{m.maquina_nombre}</TableCell>
                      <TableCell className="text-right font-mono">{kg(m.produccion_total)}</TableCell>
                      <TableCell className="text-right font-mono">{m.eficiencia} %</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Operario</TableHead>
                    <TableHead className="text-right">Lotes</TableHead>
                    <TableHead className="text-right">Producción (kg)</TableHead>
                    <TableHead className="text-right">Productividad</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {datos.operarios.map((o) => (
                    <TableRow key={o.operario_id}>
                      <TableCell>
                        <Button variant="link" className="h-auto p-0"
                          onClick={() => setOperario({ id: o.operario_id, username: o.username })}>
                          {o.username}
                        </Button>
                      </TableCell>
                      <TableCell className="text-right">{o.total_lotes}</TableCell>
                      <TableCell className="text-right font-mono">{kg(o.produccion_total_kg)}</TableCell>
                      <TableCell className="text-right font-mono">{o.productividad_kg_hora} kg/h</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </EstadoCarga>
      </CardContent>
      <DesempenoOperarioDialog operario={operario} onClose={() => setOperario(null)} />
    </Card>
  );
}
