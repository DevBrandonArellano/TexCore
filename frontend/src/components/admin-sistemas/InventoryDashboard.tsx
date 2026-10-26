import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Package, LogIn, Send, Share2, History, FileText, Layers } from 'lucide-react';
import type { Producto, Bodega, Proveedor } from '../../lib/types';
import { TransformationView } from './TransformationView';
import { StockView } from './StockView';
import { RegistrarEntradaView } from './RegistrarEntradaView';
import { TransferView } from './TransferView';
import { KardexView } from './KardexView';
import { MateriaPrimaView } from './MateriaPrimaView';
import { StockAFechaView } from './StockAFechaView';
import { ReportesView } from './ReportesView';

interface InventoryDashboardProps {
  sedeId?: string;
  productos: Producto[];
  bodegas: Bodega[];
  proveedores: Proveedor[];
  onDataRefresh: () => void;
}

export function InventoryDashboard({ sedeId, productos, bodegas, onDataRefresh, proveedores }: InventoryDashboardProps) {
  // Cada vista pide su stock al servidor (paginado, o por producto y bodega) al montarse:
  // las pestañas inactivas se desmontan, así que volver a «Stock» ya trae datos frescos.
  const [, setSearchParams] = useSearchParams();

  return (
    <Tabs
      defaultValue="stock"
      onValueChange={() => {
        setSearchParams(prev => {
          prev.set('page', '1');
          return prev;
        }, { replace: true });
      }}
      className="space-y-4"
    >
      <TabsList className="flex h-auto w-full flex-wrap gap-1">
        <TabsTrigger value="stock"><Package className="w-4 h-4 mr-2" />Stock</TabsTrigger>
        <TabsTrigger value="entrada"><LogIn className="w-4 h-4 mr-2" />Recepción</TabsTrigger>
        <TabsTrigger value="materia-prima"><Layers className="w-4 h-4 mr-2" />Materia prima</TabsTrigger>
        <TabsTrigger value="transfer"><Send className="w-4 h-4 mr-2" />Transfer</TabsTrigger>
        <TabsTrigger value="transform"><Share2 className="w-4 h-4 mr-2" />Transform</TabsTrigger>
        <TabsTrigger value="kardex"><History className="w-4 h-4 mr-2" />Kardex</TabsTrigger>
        <TabsTrigger value="reportes"><FileText className="w-4 h-4 mr-2" />Reportes</TabsTrigger>
      </TabsList>
      <TabsContent value="stock"><StockView sedeId={sedeId} /></TabsContent>
      <TabsContent value="entrada"><RegistrarEntradaView productos={productos} bodegas={bodegas} proveedores={proveedores} /></TabsContent>
      <TabsContent value="materia-prima"><MateriaPrimaView proveedores={proveedores} /></TabsContent>
      <TabsContent value="transfer"><TransferView productos={productos} bodegas={bodegas} /></TabsContent>
      <TabsContent value="transform"><TransformationView productos={productos} bodegas={bodegas} /></TabsContent>
      <TabsContent value="kardex" className="space-y-4">
        <KardexView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={onDataRefresh} />
        <StockAFechaView productos={productos} bodegas={bodegas} />
      </TabsContent>
      <TabsContent value="reportes"><ReportesView bodegas={bodegas} productos={productos} sedeId={sedeId} /></TabsContent>
    </Tabs>
  );
}
