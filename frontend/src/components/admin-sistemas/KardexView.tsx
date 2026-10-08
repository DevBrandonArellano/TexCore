import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { Download, Edit2, ShieldCheck, PackageX, Trash2 } from 'lucide-react';
import { EditarMovimientoDialog } from '../bodeguero/EditarMovimientoDialog';
import { AuditoriaDialog } from '../bodeguero/AuditoriaDialog';
import { RegistrarMermaDialog } from '../bodeguero/RegistrarMermaDialog';
import { EliminarMovimientoDialog } from '../bodeguero/EliminarMovimientoDialog';
import type { Producto, Bodega, Proveedor, Movimiento } from '../../lib/types';
import { useKardex } from './useKardex';
import { ControlesPaginacion } from '../ui/controles-paginacion';

interface KardexViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  proveedores: Proveedor[];
  onDataRefresh?: () => void;
}

function KardexViewImpl({ productos, bodegas, onDataRefresh }: KardexViewProps) {
  const kardex = useKardex();

  const [editingMovimiento, setEditingMovimiento] = useState<Movimiento | null>(null);
  const [showAuditDialog, setShowAuditDialog] = useState(false);
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null);
  const [showMermaDialog, setShowMermaDialog] = useState(false);
  const [deletingMovimiento, setDeletingMovimiento] = useState<Movimiento | null>(null);

  const {
    selectedBodega, setSelectedBodega,
    selectedProducto, setSelectedProducto,
    tipoOperacion, setTipoOperacion,
    fechaInicio, setFechaInicio,
    fechaFin, setFechaFin,
    isLoading, mostrarSaldo,
    currentPage, setCurrentPage, totalPages, totalCount, paginatedData,
    handleFetchKardex, recargarPagina, handleClearFilters, exportarExcel, exportando,
  } = kardex;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Kardex de Inventario Profesional</CardTitle>
            <CardDescription>Filtros cruzados y seguimiento de saldos por bodega.</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleClearFilters}>Limpiar</Button>
            <Button onClick={handleFetchKardex} disabled={isLoading}>
              {isLoading ? 'Consultando...' : 'Consultar'}
            </Button>
            <Button variant="secondary" onClick={exportarExcel} disabled={exportando} className="gap-2">
              <Download className="w-4 h-4" /> {exportando ? 'Generando...' : 'Exportar Excel'}
            </Button>
            <Button variant="outline" className="gap-2" onClick={() => setShowMermaDialog(true)}>
              <PackageX className="w-4 h-4" /> Registrar Merma
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Panel de Filtros */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Bodega</Label>
            <Select value={selectedBodega} onValueChange={setSelectedBodega}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Todas las bodegas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las Bodegas</SelectItem>
                {bodegas.map((b) => (
                  <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Producto</Label>
            <ProductSelect
              productos={productos}
              value={selectedProducto}
              onValueChange={setSelectedProducto}
              showAllOption={true}
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Operación</Label>
            <Select value={tipoOperacion} onValueChange={setTipoOperacion}>
              <SelectTrigger className="bg-white">
                <SelectValue placeholder="Tipo de operación" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los movimientos</SelectItem>
                <SelectItem value="entrada">Entradas (Ingresos)</SelectItem>
                <SelectItem value="salida">Salidas (Egresos)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Desde</Label>
            <Input type="date" value={fechaInicio} onChange={(e) => setFechaInicio(e.target.value)} className="bg-white" />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-bold uppercase text-slate-500">Hasta</Label>
            <Input type="date" value={fechaFin} onChange={(e) => setFechaFin(e.target.value)} className="bg-white" />
          </div>
        </div>

        {/* Tabla de Resultados */}
        <div className="rounded-md border overflow-hidden">
          <Table>
            <TableHeader className="bg-slate-50">
              <TableRow>
                <TableHead className="w-[180px]">Fecha</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead className="text-right">Cantidad</TableHead>
                {mostrarSaldo && (
                  <TableHead className="text-right font-bold text-primary">Saldo</TableHead>
                )}
                <TableHead>Referencia</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.length > 0 ? (
                paginatedData.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="text-xs">
                      {new Date(row.fecha).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{row.producto}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {row.bodega_origen || 'Origen'} → {row.bodega_destino || 'Destino'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${row.esEntrada ? 'bg-green-100 text-green-700' :
                          row.esSalida ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                        {row.tipo_movimiento}
                      </span>
                    </TableCell>
                    <TableCell className={`text-right font-mono ${row.esEntrada ? 'text-green-600' : row.esSalida ? 'text-red-600' : ''}`}>
                      {row.esSalida ? `-${row.cantidad}` : `+${row.cantidad}`}
                    </TableCell>
                    {mostrarSaldo && (
                      <TableCell className="text-right font-bold font-mono text-primary">
                        {row.saldo_acumulado !== undefined ? Number(row.saldo_acumulado).toFixed(2) : '-'}
                      </TableCell>
                    )}
                    <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">
                      {row.documento_ref || '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => {
                            setSelectedAuditId(row.id);
                            setShowAuditDialog(true);
                          }}
                        >
                          <ShieldCheck className="w-4 h-4 text-slate-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setEditingMovimiento(row)}
                        >
                          <Edit2 className="w-4 h-4 text-slate-500" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setDeletingMovimiento(row)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={mostrarSaldo ? 7 : 6} className="text-center py-10 text-muted-foreground">
                    {isLoading ? 'Cargando movimientos...' : 'No se encontraron movimientos con los filtros seleccionados.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {totalCount > 0 && (
          <ControlesPaginacion
            currentPage={currentPage}
            totalPages={totalPages}
            setCurrentPage={setCurrentPage}
            total={totalCount}
            etiquetaTotal="movimientos"
            cargando={isLoading}
            className="mt-4"
          />
        )}
      </CardContent>

      {/* Diálogos de Integración */}
      {editingMovimiento && (
        <EditarMovimientoDialog
          open={true}
          movimiento={editingMovimiento}
          onClose={() => setEditingMovimiento(null)}
          onSuccess={() => {
            setEditingMovimiento(null);
            recargarPagina();
            if (onDataRefresh) onDataRefresh();
          }}
        />
      )}

      {showAuditDialog && selectedAuditId && (
        <AuditoriaDialog
          open={true}
          movimientoId={selectedAuditId}
          onClose={() => {
            setShowAuditDialog(false);
            setSelectedAuditId(null);
          }}
        />
      )}

      <RegistrarMermaDialog
        open={showMermaDialog}
        onOpenChange={setShowMermaDialog}
        productos={productos}
        bodegas={bodegas}
        onSuccess={() => {
          recargarPagina();
          if (onDataRefresh) onDataRefresh();
        }}
      />

      <EliminarMovimientoDialog
        movimiento={deletingMovimiento}
        open={!!deletingMovimiento}
        onClose={() => setDeletingMovimiento(null)}
        onSuccess={() => {
          recargarPagina();
          if (onDataRefresh) onDataRefresh();
        }}
      />
    </Card>
  );
}

export const KardexView = React.memo(KardexViewImpl);
