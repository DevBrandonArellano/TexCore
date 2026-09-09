import React, { useState, useMemo } from 'react';

import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Users, Building2, Layers, Package, Beaker, Warehouse, Palette, Truck } from 'lucide-react';
import type { Area } from '../../lib/types';
import { ManageUsers } from './ManageUsers';
import { ManageSedes } from './ManageSedes';
import { ManageAreas } from './ManageAreas';
import { ManageProductos } from './ManageProductos';
import { ManageQuimicos } from './ManageQuimicos';
import { ManageFormulas } from './ManageFormulas';
import { ManageBodegas } from './ManageBodegas';
import { ManageClientes } from './ManageClientes';
import { ManageProveedores } from './ManageProveedores';
import { InventoryDashboard } from './InventoryDashboard';
import { AuditLogViewer } from '../shared/AuditLogViewer';
import { ErrorBoundary } from '../shared/ErrorBoundary';
import { useSedesYGrupos } from './useSedesYGrupos';
import { useSedeSpecificData } from './useSedeSpecificData';
import { useProductionPagination } from './useProductionPagination';
import { SedesSidebar } from './SedesSidebar';
import { OverviewTab } from './OverviewTab';
import { ProduccionTab } from './ProduccionTab';
import { RolesPanel } from './RolesPanel';

export function AdminSistemasDashboard() {
  const [areas, setAreas] = useState<Area[]>([]);

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedSedeId = searchParams.get('sede') || '';
  const managementTab = searchParams.get('management_tab') || 'users';

  const {
    sedes, groups, sedesFetchDone,
    handleSedeCreate, handleSedeUpdate, handleSedeDelete,
    handleAreaCreate, handleAreaUpdate, handleAreaDelete,
  } = useSedesYGrupos({ selectedSedeId, setSearchParams, setAreas });

  const {
    users, productos, quimicos, bodegas,
    ordenesProduccion, lotesProduccion, formulasColor, pedidosVenta, clientes, proveedores,
    loading, fetchSedeSpecificData,
    handleUserCreate, handleUserUpdate, handleUserDelete,
    handleClienteCreate, handleClienteUpdate, handleClienteDelete,
    handleBodegaCreate, handleBodegaUpdate, handleBodegaDelete,
    handleFormulaCreate, handleFormulaUpdate, handleFormulaDelete,
    handleChemicalCreate, handleChemicalUpdate, handleChemicalDelete,
    handleProductCreate, handleProductUpdate, handleProductDelete,
    handleProveedorCreate, handleProveedorUpdate, handleProveedorDelete,
  } = useSedeSpecificData(selectedSedeId, sedes.length, setAreas);

  const selectedSedeData = useMemo(() =>
    sedes.find(s => s.id.toString() === selectedSedeId),
    [sedes, selectedSedeId]
  );

  // Filtrar datos por sede seleccionada (asegurar arrays por si la API devuelve formato paginado)
  const _sedes = Array.isArray(sedes) ? sedes : [];
  const selectedSede = _sedes.find(s => s.id.toString() === selectedSedeId);

  const _areas = Array.isArray(areas) ? areas : [];
  const _users = Array.isArray(users) ? users : [];
  const _bodegas = Array.isArray(bodegas) ? bodegas : [];
  const _ordenes = Array.isArray(ordenesProduccion) ? ordenesProduccion : [];
  const _pedidos = Array.isArray(pedidosVenta) ? pedidosVenta : [];
  const _productos = Array.isArray(productos) ? productos : [];
  const _clientes = Array.isArray(clientes) ? clientes : [];
  const _proveedores = Array.isArray(proveedores) ? proveedores : [];
  const _quimicos = Array.isArray(quimicos) ? quimicos : [];
  const _formulas = Array.isArray(formulasColor) ? formulasColor : [];

  const sedeAreas = selectedSedeId
    ? _areas.filter(a => a.sede?.toString() === selectedSedeId)
    : _areas;

  const sedeUsers = selectedSedeId
    ? _users.filter(u => u.sede?.toString() === selectedSedeId)
    : _users;

  const sedeBodegas = selectedSedeId
    ? _bodegas.filter(b => b.sede?.toString() === selectedSedeId)
    : _bodegas;

  const sedeOrdenes = selectedSedeId
    ? _ordenes.filter(o => o.sede?.toString() === selectedSedeId)
    : _ordenes;

  const { currentPage: currentProductionPage, setCurrentPage: setCurrentProductionPage, totalPages: totalProductionPages, paginatedSedeOrdenes } =
    useProductionPagination(sedeOrdenes, selectedSedeId);

  return (
    <div className="flex h-full gap-6 p-4">
      <SedesSidebar
        sedes={_sedes}
        selectedSedeId={selectedSedeId}
        onSelectSede={(sedeId) => {
          setSearchParams(prev => {
            prev.set('sede', sedeId);
            prev.set('page', '1');
            return prev;
          }, { replace: true });
        }}
        areas={_areas}
        users={_users}
        bodegas={_bodegas}
        ordenes={_ordenes}
        pedidos={_pedidos}
      />

      {/* Contenido Principal */}
      <div className="flex-1 overflow-y-auto min-w-0 pr-4 space-y-6">
        <div>
          <h1>Panel de Administración</h1>
          <p className="text-muted-foreground">
            {selectedSede ? `Gestión de ${selectedSede.nombre}` : 'Selecciona una sede'}
          </p>
        </div>

        <Tabs
          defaultValue="overview"
          onValueChange={(v) => {
            if (v === 'management' || v === 'inventory' || v === 'audit') {
              setSearchParams(prev => {
                prev.set('page', '1');
                return prev;
              }, { replace: true });
            }
          }}
          className="space-y-4"
        >
          <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="production">Producción</TabsTrigger>
            <TabsTrigger value="inventory">Inventario</TabsTrigger>
            <TabsTrigger value="management">Gestión</TabsTrigger>
            <TabsTrigger value="audit">Auditoría</TabsTrigger>
          </TabsList>

          <OverviewTab
            selectedSedeData={selectedSedeData}
            sedeAreas={sedeAreas}
            bodegas={bodegas}
          />

          <ProduccionTab
            selectedSede={selectedSede}
            sedeOrdenes={sedeOrdenes}
            paginatedSedeOrdenes={paginatedSedeOrdenes}
            productos={productos}
            currentPage={currentProductionPage}
            setCurrentPage={setCurrentProductionPage}
            totalPages={totalProductionPages}
            formulas={_formulas}
            lotesProduccion={lotesProduccion}
          />

          {/* Tab: Inventario */}
          <TabsContent value="inventory" className="space-y-4">
            <InventoryDashboard
              sedeId={selectedSedeId || undefined}
              productos={selectedSedeId ? _productos.filter(p => p.sede?.toString() === selectedSedeId) : _productos}
              bodegas={sedeBodegas}
              lotesProduccion={lotesProduccion}
              proveedores={proveedores}
              onDataRefresh={fetchSedeSpecificData}
            />          </TabsContent>

          {/* Tab: Gestión */}
          <TabsContent value="management" className="space-y-4">
            <Tabs
              value={managementTab}
              onValueChange={(tab) => {
                setSearchParams(prev => {
                  const next = new URLSearchParams();
                  const sede = prev.get('sede');
                  if (sede) next.set('sede', sede);
                  next.set('management_tab', tab);
                  next.set('page', '1');
                  // Al cambiar de apartado en Gestión, iniciar limpio.
                  next.delete('search');
                  return next;
                }, { replace: true });
              }}
              className="space-y-4"
            >
              <TabsList className="grid w-full grid-cols-3 lg:grid-cols-9">
                <TabsTrigger value="users" className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Usuarios
                </TabsTrigger>
                <TabsTrigger value="sedes" className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  Sedes
                </TabsTrigger>
                <TabsTrigger value="areas" className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Áreas
                </TabsTrigger>
                <TabsTrigger value="productos" className="flex items-center gap-2">
                  <Package className="w-4 h-4" />
                  Productos
                </TabsTrigger>
                <TabsTrigger value="quimicos" className="flex items-center gap-2">
                  <Beaker className="w-4 h-4" />
                  Químicos
                </TabsTrigger>
                <TabsTrigger value="formulas" className="flex items-center gap-2">
                  <Palette className="w-4 h-4" />
                  Fórmulas
                </TabsTrigger>
                <TabsTrigger value="bodegas" className="flex items-center gap-2">
                  <Warehouse className="w-4 h-4" />
                  Bodegas
                </TabsTrigger>
                <TabsTrigger value="clientes" className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  Clientes
                </TabsTrigger>
                <TabsTrigger value="proveedores" className="flex items-center gap-2">
                  <Truck className="w-4 h-4" />
                  Proveedores
                </TabsTrigger>
                <TabsTrigger value="roles" className="flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Roles
                </TabsTrigger>
              </TabsList>

              <TabsContent value="users">
                <ManageUsers
                  users={sedeUsers}
                  sedes={sedes}
                  areas={sedeAreas}
                  groups={groups}
                  selectedSedeId={selectedSedeId || undefined}
                  onUserCreate={handleUserCreate}
                  onUserUpdate={handleUserUpdate}
                  onUserDelete={handleUserDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="sedes">
                <ManageSedes
                  sedes={sedes}
                  sedesLoading={!sedesFetchDone}
                  onSedeCreate={handleSedeCreate}
                  onSedeUpdate={handleSedeUpdate}
                  onSedeDelete={handleSedeDelete}
                />
              </TabsContent>

              <TabsContent value="areas">
                <ManageAreas
                  areas={sedeAreas}
                  sedes={sedes}
                  selectedSedeId={selectedSedeId ?? undefined}
                  onAreaCreate={handleAreaCreate}
                  onAreaUpdate={handleAreaUpdate}
                  onAreaDelete={handleAreaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="productos">
                <ManageProductos
                  productos={selectedSedeId
                    ? _productos.filter(p => !p.sede || p.sede.toString() === selectedSedeId)
                    : _productos
                  }
                  onProductCreate={handleProductCreate}
                  onProductUpdate={handleProductUpdate}
                  onProductDelete={handleProductDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="quimicos">
                <ManageQuimicos
                  quimicos={_quimicos}
                  onChemicalCreate={handleChemicalCreate}
                  onChemicalUpdate={handleChemicalUpdate}
                  onChemicalDelete={handleChemicalDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="formulas">
                <ManageFormulas
                  formulas={_formulas}
                  onFormulaCreate={handleFormulaCreate}
                  onFormulaUpdate={handleFormulaUpdate}
                  onFormulaDelete={handleFormulaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="bodegas">
                <ManageBodegas
                  bodegas={sedeBodegas}
                  sedes={sedes}
                  users={sedeUsers}
                  selectedSedeId={selectedSedeId || undefined}
                  onBodegaCreate={handleBodegaCreate}
                  onBodegaUpdate={handleBodegaUpdate}
                  onBodegaDelete={handleBodegaDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="clientes">
                <ManageClientes
                  clientes={selectedSedeId ? _clientes.filter(c => c.sede?.toString() === selectedSedeId) : _clientes}
                  onClienteCreate={handleClienteCreate}
                  onClienteUpdate={handleClienteUpdate}
                  onClienteDelete={handleClienteDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="proveedores">
                <ManageProveedores
                  proveedores={selectedSedeId
                    ? _proveedores.filter(p => !p.sede || p.sede.toString() === selectedSedeId)
                    : _proveedores
                  }
                  onProveedorCreate={handleProveedorCreate}
                  onProveedorUpdate={handleProveedorUpdate}
                  onProveedorDelete={handleProveedorDelete}
                  loading={loading}
                />
              </TabsContent>

              <TabsContent value="roles">
                <RolesPanel groups={groups} sedeUsers={sedeUsers} />
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="audit" className="space-y-4">
            <ErrorBoundary>
              <AuditLogViewer sedeId={selectedSedeId || undefined} />
            </ErrorBoundary>
          </TabsContent>
        </Tabs>
      </div>

    </div>
  );
}
