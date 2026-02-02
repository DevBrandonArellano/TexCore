import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Label } from '../ui/label';
import { Settings, Save, RefreshCw, Info } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { ConfiguracionSistema } from '../../lib/types';

export function ManageConfiguracion() {
  const [configs, setConfigs] = useState<ConfiguracionSistema[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/configuracion-sistema/');
      setConfigs(res.data);
      
      // if ZPL_TEMPLATE doesn't exist, we might want to suggest creating it, 
      // but usually the backend should have a seed.
    } catch (error) {
      toast.error('Error al cargar configuraciones');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleUpdate = async (id: number, valor: string) => {
    setSaving(true);
    try {
      await apiClient.patch(`/configuracion-sistema/${id}/`, { valor });
      toast.success('Configuración actualizada');
      fetchConfigs();
    } catch (error) {
      toast.error('Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const createDefaultZpl = async () => {
    try {
      await apiClient.post('/configuracion-sistema/', {
        clave: 'ZPL_TEMPLATE',
        valor: `^XA
^CF0,60
^FO50,50^FDPROYECTO: TEXCORE^FS
^CF0,40
^FO50,130^FDPRODUCTO: {{producto}}^FS
^FO50,180^FDLOTE: {{lote}}^FS
^FO50,230^FDPESO: {{peso}} KG^FS
^FO50,280^FDBULTO: {{bulto}}^FS
^FO50,330^FDFECHA: {{fecha}}^FS
^BY3,2,100
^FO50,380^BCN,100,Y,N,N^FD{{codigo}}^FS
^XZ`,
        descripcion: 'Plantilla base para etiquetas de despacho Zebra'
      });
      fetchConfigs();
    } catch (error) {
      toast.error('Error al crear plantilla por defecto');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-6 h-6" /> Ajustes del Sistema
        </h2>
        <Button variant="outline" size="sm" onClick={fetchConfigs}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} /> Actualizar
        </Button>
      </div>

      <div className="grid gap-6">
        {configs.length === 0 && !loading && (
          <Card className="border-dashed">
            <CardContent className="py-10 text-center">
              <p className="text-muted-foreground mb-4">No hay configuraciones registradas.</p>
              <Button onClick={createDefaultZpl}>Inicializar Plantilla ZPL</Button>
            </CardContent>
          </Card>
        )}

        {configs.map((config) => (
          <Card key={config.id}>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                {config.clave === 'ZPL_TEMPLATE' ? 'Plantilla de Etiqueta Zebra (ZPL)' : config.clave}
              </CardTitle>
              <CardDescription>{config.descripcion}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-blue-50 p-3 rounded-md text-xs text-blue-800 flex gap-2">
                <Info className="w-4 h-4 flex-shrink-0" />
                <div>
                  Usa etiquetas como <strong>{"{{producto}}"}</strong>, <strong>{"{{lote}}"}</strong>, <strong>{"{{peso}}"}</strong>, 
                  <strong>{"{{bulto}}"}</strong>, <strong>{"{{fecha}}"}</strong> y <strong>{"{{codigo}}"}</strong> en tu código ZPL.
                </div>
              </div>
              <Textarea 
                className="font-mono text-sm h-64 bg-slate-900 text-slate-100" 
                defaultValue={config.valor}
                id={`config-${config.id}`}
              />
              <div className="flex justify-end">
                <Button 
                  disabled={saving}
                  onClick={() => {
                    const val = (document.getElementById(`config-${config.id}`) as HTMLTextAreaElement).value;
                    handleUpdate(config.id, val);
                  }}
                >
                  <Save className="w-4 h-4 mr-2" /> {saving ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
