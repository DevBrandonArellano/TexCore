import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { ProductSelect } from '../ui/product-select';
import { ChevronLeft, ChevronRight, Download, Edit2, ShieldCheck, PackageX, Trash2 } from 'lucide-react';
import { EditarMovimientoDialog } from '../bodeguero/EditarMovimientoDialog';
import { AuditoriaDialog } from '../bodeguero/AuditoriaDialog';
import { RegistrarMermaDialog } from '../bodeguero/RegistrarMermaDialog';
import { EliminarMovimientoDialog } from '../bodeguero/EliminarMovimientoDialog';
import type { Producto, Bodega, Proveedor, Movimiento } from '../../lib/types';
import { useKardex } from './useKardex';

interface KardexViewProps {
  productos: Producto[];
  bodegas: Bodega[];
  proveedores: Proveedor[];
  onDataRefresh?: () => void;
}

function KardexViewImpl({ productos, bodegas, proveedores, onDataRefresh }: KardexViewProps) {
  const kardex = useKardex(bodegas);

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
    kardexData, isLoading,
    currentPage, setCurrentPage, totalPages, paginatedData,
    handleFetchKardex, handleClearFilters, exportToCSV,
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
            <Button variant="secondary" onClick={exportToCSV} className="gap-2">
              <Download className="w-4 h-4" /> Exportar CSV
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
                {selectedProducto !== 'all' && selectedBodega !== 'all' && (
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
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${(row as any).esEntrada ? 'bg-green-100 text-green-700' :
                          (row as any).esSalida ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                        {row.tipo_movimiento}
                      </span>
                    </TableCell>
                    <TableCell className={`text-right font-mono ${(row as any).esEntrada ? 'text-green-600' : (row as any).esSalida ? 'text-red-600' : ''}`}>
                      {(row as any).esSalida ? `-${row.cantidad}` : `+${row.cantidad}`}
                    </TableCell>
                    {selectedProducto !== 'all' && selectedBodega !== 'all' && (
                      <TableCell className="text-right font-bold font-mono text-primary">
                        {(row as any).saldo_acumulado !== undefined ? Number((row as any).saldo_acumulado).toFixed(2) : '-'}
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
                  <TableCell colSpan={selectedProducto !== 'all' && selectedBodega !== 'all' ? 7 : 6} className="text-center py-10 text-muted-foreground">
                    {isLoading ? 'Cargando movimientos...' : 'No se encontraron movimientos con los filtros seleccionados.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {kardexData.length > 0 && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-muted-foreground">Página {currentPage} de {totalPages}</span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1 || isLoading}><ChevronLeft className="w-4 h-4 mr-1" />Anterior</Button>
              <span className="flex items-center gap-1 text-sm">
                <span className="text-muted-foreground">Ir a</span>
                <Input
                  type="number"
                  min={1}
                  max={totalPages}
                  defaultValue={currentPage}
                  key={currentPage}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const v = parseInt((e.target as HTMLInputElement).value, 10);
                      if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                    }
                  }}
                  onBlur={(e) => {
                    const v = parseInt(e.target.value, 10);
                    if (!isNaN(v) && v >= 1 && v <= totalPages) setCurrentPage(v);
                  }}
                  className="w-14 h-8 text-center py-0 px-1"
                />
              </span>
              <Button size="sm" variant="outline" onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages || isLoading}>Siguiente<ChevronRight className="w-4 h-4 ml-1" /></Button>
            </div>
          </div>
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
            handleFetchKardex();
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
          handleFetchKardex();
          if (onDataRefresh) onDataRefresh();
        }}
      />

      <EliminarMovimientoDialog
        movimiento={deletingMovimiento}
        open={!!deletingMovimiento}
        onClose={() => setDeletingMovimiento(null)}
        onSuccess={() => {
          handleFetchKardex();
          if (onDataRefresh) onDataRefresh();
        }}
      />
    </Card>
  );
}

export const KardexView = React.memo(KardexViewImpl);
