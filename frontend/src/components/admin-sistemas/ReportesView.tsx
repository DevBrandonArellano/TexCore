import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { ProductSelect } from '../ui/product-select';
import { History, Package, AlertCircle, PackageX, Download, Warehouse } from 'lucide-react';
import type { Producto, Bodega } from '../../lib/types';
import { useReportesExport } from './useReportesExport';

interface ReportesViewProps {
  bodegas: Bodega[];
  productos: Producto[];
  sedeId?: string;
}

function ReportesViewImpl({ bodegas, productos, sedeId }: ReportesViewProps) {
  const [rkFechaInicio, setRkFechaInicio] = useState('');
  const [rkFechaFin, setRkFechaFin] = useState('');
  const [rkProducto, setRkProducto] = useState('');
  const [rkBodega, setRkBodega] = useState('');
  const [agingDias, setAgingDias] = useState('30');

  const { loading, handleExport } = useReportesExport(rkBodega);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 pb-10">
      {/* Selector de Bodega Global para reportes */}
      <Card className="xl:col-span-2 bg-muted/30 border-dashed">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center gap-4">
            <div className="flex-1 w-full space-y-2">
              <Label className="text-primary font-bold">Bodega Principal para Reportes <span className="text-destructive">*</span></Label>
              <Select value={rkBodega} onValueChange={setRkBodega}>
                <SelectTrigger className="bg-background"><SelectValue placeholder="Selecciona una bodega para habilitar los reportes" /></SelectTrigger>
                <SelectContent>
                  {bodegas.map(b => <SelectItem key={b.id} value={b.id.toString()}>{b.nombre}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {sedeId && (
              <Badge variant="outline" className="h-10 px-4 gap-2">
                <Warehouse className="w-4 h-4" />
                Sede ID: {sedeId}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 1. Kardex de Bodega */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-100 rounded-lg dark:bg-blue-900/30">
              <History className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <CardTitle>Kardex de Movimientos</CardTitle>
              <CardDescription>Movimientos detallados con saldo progresivo.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Producto (Opcional)</Label>
              <ProductSelect productos={productos} value={rkProducto} onValueChange={setRkProducto} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Desde</Label>
              <Input type="date" value={rkFechaInicio} onChange={e => setRkFechaInicio(e.target.value)} size={30} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hasta</Label>
              <Input type="date" value={rkFechaFin} onChange={e => setRkFechaFin(e.target.value)} />
            </div>
            <Button
              className="mt-auto gap-2"
              onClick={() => handleExport('kardex', { producto_id: rkProducto, fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
              disabled={loading['kardex'] || !rkBodega}
            >
              <Download className="w-4 h-4" />
              {loading['kardex'] ? 'Generando...' : 'Exportar Kardex'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 2. Stock Actual */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-green-100 rounded-lg dark:bg-green-900/30">
              <Package className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <CardTitle>Snapshot de Stock Actual</CardTitle>
              <CardDescription>Resumen de existencias por lote en esta bodega.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="w-full gap-2 border-green-200 hover:bg-green-50 dark:border-green-800"
            onClick={() => handleExport('stock-actual')}
            disabled={loading['stock-actual'] || !rkBodega}
          >
            <Download className="w-4 h-4" />
            {loading['stock-actual'] ? 'Descargando...' : 'Descargar Stock Actual'}
          </Button>
        </CardContent>
      </Card>

      {/* 3. Aging */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-purple-100 rounded-lg dark:bg-purple-900/30">
              <AlertCircle className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <CardTitle>Antigüedad de Stock (Aging)</CardTitle>
              <CardDescription>Filtra por rango de días sin movimiento en la bodega (alineado con las categorías del reporte).</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <Label className="text-xs">Rango de antigüedad</Label>
              <Select value={agingDias} onValueChange={setAgingDias}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">Reciente: 0–30 días</SelectItem>
                  <SelectItem value="60">Medio: 31–90 días</SelectItem>
                  <SelectItem value="90">Lento: 91–180 días</SelectItem>
                  <SelectItem value="180">Crítico: más de 180 días o sin movimiento</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              className="mt-auto gap-2"
              variant="outline"
              onClick={() => handleExport('aging', { dias: agingDias })}
              disabled={loading['aging'] || !rkBodega}
            >
              <Download className="w-4 h-4" />
              {loading['aging'] ? 'Analizando...' : 'Exportar Aging'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Stock en Cero — junto a Aging */}
      <Card className={!rkBodega ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-red-100 rounded-lg dark:bg-red-900/30">
              <PackageX className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <CardTitle>Productos con Stock Cero</CardTitle>
              <CardDescription>Productos agotados o sin registro en esta bodega. Útil para planificar reposiciones.</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="w-full gap-2 border-red-200 hover:bg-red-50 dark:border-red-800"
            onClick={() => handleExport('stock-cero')}
            disabled={loading['stock-cero'] || !rkBodega}
          >
            <Download className="w-4 h-4" />
            {loading['stock-cero'] ? 'Descargando...' : 'Descargar Stock en Cero'}
          </Button>
        </CardContent>
      </Card>

      {/* 5. Rotación y Resumen */}
      <Card className={!rkBodega ? "opacity-60" : "xl:col-span-2"}>
        <CardHeader>
          <CardTitle>Análisis de Movimientos y Rotación</CardTitle>
          <CardDescription>Compara entradas vs salidas y mide la velocidad del inventario en un período.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Fecha Inicio (Requerido)</Label>
              <Input type="date" value={rkFechaInicio} onChange={e => setRkFechaInicio(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Fecha Fin (Requerido)</Label>
              <Input type="date" value={rkFechaFin} onChange={e => setRkFechaFin(e.target.value)} />
            </div>
            <div className="flex gap-2">
              <Button
                className="flex-1 gap-1"
                variant="secondary"
                onClick={() => handleExport('rotacion', { fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
                disabled={loading['rotacion'] || !rkBodega || !rkFechaInicio || !rkFechaFin}
              >
                <Download className="w-3 h-3" />
                Rotación
              </Button>
              <Button
                className="flex-1 gap-1"
                variant="secondary"
                onClick={() => handleExport('resumen-movimientos', { fecha_inicio: rkFechaInicio, fecha_fin: rkFechaFin })}
                disabled={loading['resumen-movimientos'] || !rkBodega || !rkFechaInicio || !rkFechaFin}
              >
                <Download className="w-3 h-3" />
                Resumen
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Catálogo de Productos */}
      <Card className="xl:col-span-2 border-primary/20 bg-primary/5">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div>
            <CardTitle className="text-base">Catálogo maestro de Productos</CardTitle>
            <CardDescription>Base de datos completa de productos y códigos.</CardDescription>
          </div>
          <Button variant="ghost" onClick={() => handleExport('productos')} disabled={loading['productos']} className="gap-2">
            <Download className="w-4 h-4" />
            {loading['productos'] ? 'Exportando...' : 'Descargar Catálogo'}
          </Button>
        </CardHeader>
      </Card>
    </div>
  );
}

export const ReportesView = React.memo(ReportesViewImpl);
