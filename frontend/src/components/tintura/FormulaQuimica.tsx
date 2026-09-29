import React, { useState, useMemo, useRef } from 'react';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import {
  Plus,
  Pencil,
  Trash2,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
  Calculator,
  Search,
  CheckCircle2,
  Clock,
  X,
  Eye,
  Copy,
  FlaskConical,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { ProcesoTintoreria, Quimico } from '../../lib/types';
import { usePagination } from '../../hooks/usePagination';
import { CrearVarianteDialog, DerivarFormulaDatos } from './DialogosFormula';
import { FormulaDetalle } from './FormulaDetalle';

// --- Esquemas Zod de Validación para Producción ---
// Preprocesador para manejar inputs vacíos y números de forma segura
const NumberField = z.preprocess(
  (val) => (val === "" || val === null || val === undefined || Number.isNaN(Number(val)) ? undefined : Number(val)),
  z.number().min(0, "Debe ser >= 0").optional()
).optional();

const DetalleSchema = z.object({
  id: z.number().optional(),
  producto: z.number().min(1, "El insumo químico es obligatorio"),
  tipo_calculo: z.enum(['gr_l', 'pct']),
  concentracion_gr_l: NumberField,
  porcentaje: NumberField,
  orden_adicion: z.number().min(1, "Orden de adición requerido"),
  notas: z.string().optional(),
  _productoObj: z.any().optional()
}).superRefine((data, ctx) => {
  if (data.tipo_calculo === 'gr_l' && data.concentracion_gr_l === undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Valor gr/L es obligatorio y debe ser >= 0",
      path: ["concentracion_gr_l"]
    });
  }
  if (data.tipo_calculo === 'pct' && data.porcentaje === undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Valor % es obligatorio y debe ser >= 0",
      path: ["porcentaje"]
    });
  }
});

const FaseSchema = z.object({
  id: z.number().optional(),
  proceso: z.number().min(1, "Seleccione un proceso"),
  ciclo: NumberField,
  orden: z.number().min(1),
  temperatura: NumberField,
  tiempo: NumberField,
  observaciones: z.string().optional(),
  detalles: z.array(DetalleSchema).min(1, "La fase debe tener al menos un insumo químico")
});
const FormulaSchema = z.object({
  id: z.number().optional(),
  codigo: z.string().min(1, "El código es requerido"),
  nombre_color: z.string().min(1, "El color es requerido"),
  description: z.string().optional(),
  tipo_sustrato: z.string().optional(),
  estado: z.enum(['en_pruebas', 'aprobada']),
  observaciones: z.string().optional(),
  // D8: fórmula de ensayo de laboratorio, se filtra del listado por defecto
  es_laboratorio: z.boolean().optional(),
  fases: z.array(FaseSchema).min(1, "Debe agregar al menos una fase de tintura")
});

type FormulaFormValues = z.infer<typeof FormulaSchema>;
const ITEMS_PER_PAGE = 20;

// --- Helpers de Cálculo ---
// Spec 2026-09-24 (D3): los litros son el dato canónico que fija el ingeniero
// tintorero contra el peso de la carga; la relación de baño se deriva, no se pide.
// Esta calculadora es una vista previa en vivo sobre la fórmula que se está
// editando (aún sin guardar), por eso sigue en el cliente; la dosificación real
// de una orden de producción ya se calcula en el backend (D4), ver
// /ordenes-produccion/{id}/calcular-dosificacion/.
export function calcularCantidad(
  tipo_calculo: 'gr_l' | 'pct',
  concentracion_gr_l: number | null | undefined,
  porcentaje: number | null | undefined,
  peso: number,
  litros: number
): { kg: number; gr: number } | null {
  if (peso <= 0 || litros <= 0) return null;

  let cantidadKg = 0;
  if (tipo_calculo === 'gr_l') {
    cantidadKg = (litros * (concentracion_gr_l ?? 0)) / 1000;
  } else {
    cantidadKg = (peso * (porcentaje ?? 0)) / 100;
  }

  return { kg: cantidadKg, gr: cantidadKg * 1000 };
}

// --- Componente Buscador Optimizado ---
interface BuscadorQuimicoProps {
  quimicos: Quimico[];
  productoSeleccionado: Quimico | null | undefined;
  onSelect: (q: Quimico | null) => void;
  disabled?: boolean;
}

function BuscadorQuimico({ quimicos, productoSeleccionado, onSelect, disabled }: BuscadorQuimicoProps) {
  const [query, setQuery] = useState('');
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtrados = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return [];
    return quimicos.filter((qu) => 
      qu.descripcion?.toLowerCase().includes(q) || qu.codigo?.toLowerCase().includes(q)
    ).slice(0, 10);
  }, [query, quimicos]);

  if (productoSeleccionado) {
    return (
      <div className="flex items-center gap-2 text-[11px] bg-primary/5 px-2 py-1 rounded-md border border-primary/20 w-fit">
        <div className="flex flex-col flex-1 truncate">
          <span className="font-bold text-primary uppercase truncate">{productoSeleccionado.descripcion}</span>
          <span className="opacity-60 font-mono">{productoSeleccionado.codigo}</span>
        </div>
        {!disabled && (
          <button type="button" onClick={() => onSelect(null)} className="p-1 hover:text-destructive">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative w-full min-w-[200px]" ref={ref}>
      <div className="flex items-center gap-2 border rounded-md px-2 py-1 bg-background text-xs">
        <Search className="w-3 h-3 text-muted-foreground" />
        <input
          className="flex-1 bg-transparent outline-none w-full"
          placeholder="Buscar insumo..."
          value={query}
          onFocus={() => setAbierto(true)}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      {abierto && query && (
        <div className="absolute z-[100] top-full mt-1 w-72 bg-popover border rounded-md shadow-xl max-h-48 overflow-auto">
          {filtrados.length === 0 ? (
            <div className="p-2 text-xs text-muted-foreground text-center">No se encontraron resultados</div>
          ) : (
            filtrados.map((q) => (
              <div 
                key={q.id} 
                className="p-2 hover:bg-accent cursor-pointer text-[11px] border-b" 
                onMouseDown={(e) => { e.preventDefault(); onSelect(q); setAbierto(false); setQuery(''); }}
              >
                <div className="font-bold">{q.descripcion}</div>
                <div className="text-[10px] opacity-50 font-mono">{q.codigo}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function EstadoBadge({ estado }: { estado: string }) {
  if (estado === 'aprobada') {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1 hover:bg-emerald-100">
        <CheckCircle2 className="w-3 h-3" /> Aprobada
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1">
      <Clock className="w-3 h-3" /> En Pruebas
    </Badge>
  );
}

interface FormulaQuimicaProps {
  formulas: any[];
  quimicos: Quimico[];
  procesos?: ProcesoTintoreria[];
  loading?: boolean;
  canDelete?: boolean;
  incluirLaboratorio?: boolean;
  onToggleIncluirLaboratorio?: () => void;
  onFormulaCreate: (f: FormulaFormValues) => Promise<boolean>;
  onFormulaUpdate: (id: number, f: FormulaFormValues) => Promise<boolean>;
  onFormulaCrearVersion?: (id: number, observaciones: string) => Promise<boolean>;
  onFormulaMarcarOficial?: (id: number, numero: number) => Promise<boolean>;
  onFormulaDerivar?: (id: number, datos: DerivarFormulaDatos & { version_origen: number }) => Promise<boolean>;
  onFormulaDuplicate?: (id: number, datos: { codigo: string; nombre_color: string }) => Promise<boolean>;
  onFormulaDelete?: (id: number) => void;
  onExportDosificador?: (id: number) => void;
}

export function FormulaQuimica({
  formulas, quimicos, procesos = [], loading, incluirLaboratorio, onToggleIncluirLaboratorio,
  onFormulaCreate, onFormulaUpdate, onFormulaCrearVersion, onFormulaMarcarOficial, onFormulaDerivar,
  onFormulaDuplicate, onExportDosificador
}: FormulaQuimicaProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [vista, setVista] = useState<'lista' | 'editor' | 'detalle'>('lista');
  const [guardando, setGuardando] = useState(false);
  const [formulaVariante, setFormulaVariante] = useState<any | null>(null);
  const [formulaDetalle, setFormulaDetalle] = useState<any | null>(null);
  const procesosActivos = useMemo(() => procesos.filter((p) => p.activo), [procesos]);
  const nombreProceso = (id?: number) => procesos.find((p) => p.id === id)?.nombre ?? 'Sin proceso';
  const busqueda = searchParams.get('q') || '';

  const setBusqueda = (val: string) => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set('q', val);
    else next.delete('q');
    setSearchParams(next, { replace: true });
  };

  // Estado local para la calculadora puramente UI (vista previa en vivo, spec D3: litros es el dato canónico)
  const [calculadora, setCalculadora] = useState({ peso: '', litros: '' });
  const relacionCalculada = useMemo(() => {
    const peso = parseFloat(calculadora.peso) || 0;
    const litros = parseFloat(calculadora.litros) || 0;
    return peso > 0 && litros > 0 ? litros / peso : null;
  }, [calculadora.peso, calculadora.litros]);

  // --- Integración React Hook Form ---
  const form = useForm<FormulaFormValues>({
    resolver: zodResolver(FormulaSchema as any),
    mode: 'onChange',
    defaultValues: {
      codigo: '', nombre_color: '', description: '', tipo_sustrato: 'algodon', estado: 'en_pruebas', observaciones: '', es_laboratorio: false, fases: []
    }
  });

  const { fields: phaseFields, append: appendPhase, remove: removePhase } = useFieldArray({
    control: form.control,
    name: "fases"
  });

  // Watcher for reactive calculations
  const fasesWatcher = form.watch("fases");

  const abrirEditar = (formula: any) => {
    form.reset({
      id: formula.id,
      codigo: formula.codigo,
      nombre_color: formula.nombre_color,
      description: formula.description || '',
      tipo_sustrato: formula.tipo_sustrato || 'algodon',
      estado: formula.estado,
      observaciones: formula.observaciones || '',
      es_laboratorio: formula.es_laboratorio || false,
      fases: formula.fases?.map((f: any) => ({
        id: f.id,
        proceso: f.proceso,
        ciclo: f.ciclo ?? undefined,
        orden: f.orden,
        temperatura: f.temperatura,
        tiempo: f.tiempo,
        observaciones: f.observaciones || '',
        detalles: f.detalles.map((d: any) => ({
          id: d.id,
          producto: d.producto,
          tipo_calculo: d.tipo_calculo,
          concentracion_gr_l: d.concentracion_gr_l,
          porcentaje: d.porcentaje,
          orden_adicion: d.orden_adicion,
          notas: d.notas || '',
          _productoObj: quimicos.find((q) => q.id === d.producto)
        }))
      })) || []
    });
    setVista('editor');
  };

  // Proceso sugerido para una fase nueva: el primero del tipo pedido, si no el primero activo
  const procesoPorDefecto = (tipo: ProcesoTintoreria['tipo']) =>
    (procesosActivos.find((p) => p.tipo === tipo) ?? procesosActivos[0])?.id ?? 0;

  const faseVacia = (tipo: ProcesoTintoreria['tipo'], orden: number) => ({
    proceso: procesoPorDefecto(tipo), ciclo: undefined, orden, temperatura: undefined, tiempo: undefined, detalles: []
  });

  const abrirNuevo = () => {
    form.reset({
      codigo: '', nombre_color: '', description: '', tipo_sustrato: 'algodon', estado: 'en_pruebas', observaciones: '',
      es_laboratorio: false, fases: [faseVacia('pre_tratamiento', 1)]
    });
    setVista('editor');
  };

  const onSubmit = async (data: FormulaFormValues) => {
    try {
      setGuardando(true);

      // D7: editar la receta viva ya no versiona ni exige motivo; se congela como
      // ensayo aparte, desde la pestaña Versiones (ver crear_version/marcar_oficial).
      const dataToSubmit = {
        ...data,
        fases: data.fases.map((f, i) => ({
          ...f,
          orden: i + 1,
          detalles: f.detalles.map((d, j) => ({
            ...d,
            orden_adicion: j + 1
          }))
        }))
      };

      const exito = data.id 
        ? await onFormulaUpdate(data.id, dataToSubmit) 
        : await onFormulaCreate(dataToSubmit);
      
      if (exito) {
        setVista('lista');
      }
    } catch (err: any) {
      toast.error('Error al guardar la fórmula', { description: err.message });
    } finally {
      setGuardando(false);
    }
  };

  const onInvalid = (errors: any) => {
    toast.error('Error de validación', { description: 'Revisa los campos marcados en rojo' });
    console.log("Validation Errors:", errors);
  };

  const filteredFormulas = formulas.filter(
    (f) =>
      f.codigo.toLowerCase().includes(busqueda.toLowerCase()) ||
      f.nombre_color.toLowerCase().includes(busqueda.toLowerCase())
  );
  const {
    currentPage: safePage,
    setCurrentPage,
    totalPages,
    paginatedItems: paginatedFormulas,
  } = usePagination(filteredFormulas, ITEMS_PER_PAGE, { resetKey: busqueda });

  if (vista === 'detalle' && formulaDetalle) {
    return (
      <FormulaDetalle
        formula={formulaDetalle}
        procesos={procesos}
        onVolver={() => { setFormulaDetalle(null); setVista('lista'); }}
        onEditar={(f) => { setFormulaDetalle(null); abrirEditar(f); }}
        onCrearVersion={onFormulaCrearVersion || (async () => false)}
        onMarcarOficial={onFormulaMarcarOficial || (async () => false)}
        onDerivar={onFormulaDerivar || (async () => false)}
      />
    );
  }

  if (vista === 'lista') {
    return (
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Fórmulas Químicas</CardTitle>
            <Button onClick={abrirNuevo}>
              <Plus className="w-4 h-4 mr-2" /> Nueva Fórmula
            </Button>
          </div>
          <div className="flex items-center gap-4 flex-wrap">
            <Input
              placeholder="Buscar por código o color..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="max-w-sm"
            />
            {onToggleIncluirLaboratorio && (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input type="checkbox" checked={!!incluirLaboratorio} onChange={onToggleIncluirLaboratorio} />
                <FlaskConical className="w-3.5 h-3.5" /> Mostrar fórmulas de laboratorio
              </label>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow><TableHead>Código</TableHead><TableHead>Nombre</TableHead><TableHead>Estado</TableHead><TableHead>Versión oficial</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
            <TableBody>
              {paginatedFormulas.map((f: any) => (
                <TableRow key={f.id}>
                  <TableCell className="font-mono text-xs font-bold">{f.codigo}</TableCell>
                  <TableCell className="uppercase">{f.nombre_color}</TableCell>
                  <TableCell><EstadoBadge estado={f.estado} /></TableCell>
                  <TableCell className="font-mono text-xs">{f.version_oficial ? `v${f.version_oficial}` : '—'}</TableCell>
                  <TableCell className="text-right space-x-1 whitespace-nowrap">
                    <Button variant="outline" size="sm" aria-label="Editar" title="Editar" onClick={() => abrirEditar(f)}>
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" aria-label="Ver detalle" title="Ver detalle" onClick={() => { setFormulaDetalle(f); setVista('detalle'); }}>
                      <Eye className="w-4 h-4" />
                    </Button>
                    {onFormulaDuplicate && (
                      <Button variant="outline" size="sm" aria-label="Crear variante" title="Crear variante" onClick={() => setFormulaVariante(f)}>
                        <Copy className="w-4 h-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {filteredFormulas.length === 0 && !loading && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground py-8">No hay fórmulas registradas</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          {filteredFormulas.length > 0 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-sm text-muted-foreground">
                Página {safePage} de {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage((p) => p - 1)}
                  disabled={safePage === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  Anterior
                </Button>
                <span className="flex items-center gap-1 text-sm">
                  <span className="text-muted-foreground">Ir a</span>
                  <Input
                    type="number"
                    min={1}
                    max={totalPages}
                    defaultValue={safePage}
                    key={safePage}
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
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage((p) => p + 1)}
                  disabled={safePage === totalPages}
                >
                  Siguiente
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
        {onFormulaDuplicate && (
          <CrearVarianteDialog
            formula={formulaVariante}
            onOpenChange={(open) => !open && setFormulaVariante(null)}
            onConfirm={onFormulaDuplicate}
          />
        )}
      </Card>
    );
  }

  const isEditing = !!form.getValues('id');
  return (
    <div className="flex flex-col min-h-screen">
      <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground flex-shrink-0">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setVista('lista')}><ArrowLeft className="w-4 h-4 mr-2"/> Volver</Button>
          <ChevronRight className="w-4 h-4" />
          <span className="font-medium text-foreground">{isEditing ? 'Editando Fórmula' : 'Nueva Fórmula'}</span>
        </div>
        {isEditing && onExportDosificador && (
          <Button variant="outline" size="sm" className="bg-blue-50 text-blue-700 border-blue-200" onClick={() => onExportDosificador(form.getValues('id')!)}>
            <Calculator className="w-4 h-4 mr-2" /> Exportar Dosificador (Infotint)
          </Button>
        )}
      </div>

      <form onSubmit={form.handleSubmit(onSubmit as any, onInvalid)} className="flex flex-col flex-1 min-h-0">
        
        <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0 pb-4">
          
          {/* PANEL IZQUIERDO */}
          <div className="flex-1 flex flex-col space-y-4 overflow-y-auto pr-2">
            <Card className="flex-shrink-0">
              <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6">
                <div className="space-y-2">
                  <Label>Código <span className="text-red-500">*</span></Label>
                  <Input {...form.register('codigo')} placeholder="Ej: FQ-1002" />
                  {form.formState.errors.codigo && <span className="text-xs text-red-500">{form.formState.errors.codigo.message}</span>}
                </div>
                <div className="space-y-2">
                  <Label>Nombre del Color <span className="text-red-500">*</span></Label>
                  <Input {...form.register('nombre_color')} placeholder="ROJO INTENSO" className="uppercase" />
                  {form.formState.errors.nombre_color && <span className="text-xs text-red-500">{form.formState.errors.nombre_color.message}</span>}
                </div>
                <div className="space-y-2">
                  <Label>Estado</Label>
                  {/* El estado lo fija marcar_oficial (pestaña Versiones): aquí es de solo lectura */}
                  <div className="h-9 flex items-center"><EstadoBadge estado={form.getValues('estado')} /></div>
                </div>
                <div className="space-y-2 flex items-end">
                  <label className="flex items-center gap-2 text-sm h-9">
                    <Controller
                      control={form.control}
                      name="es_laboratorio"
                      render={({ field }) => (
                        <input type="checkbox" checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} />
                      )}
                    />
                    <FlaskConical className="w-3.5 h-3.5 text-muted-foreground" /> Fórmula de laboratorio
                  </label>
                </div>
              </CardContent>
            </Card>

            <div className="space-y-4">
              <div className="flex justify-between items-center px-1">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Clock className="w-5 h-5 text-primary" /> Fases del Proceso (Dyeing Tool)
                </h3>
                <Button 
                  type="button" 
                  size="sm" 
                  variant="outline" 
                  onClick={() => appendPhase(faseVacia('colorante', phaseFields.length + 1))}
                >
                  <Plus className="w-4 h-4 mr-1" /> Agregar Fase
                </Button>
              </div>

              {phaseFields.map((phase, pIndex) => (
                <Card key={phase.id} className="border-l-4 border-l-primary/50">
                  <CardHeader className="py-3 px-4 bg-muted/30 flex flex-row items-center justify-between gap-4">
                    <div className="flex flex-1 items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="h-6 w-6 flex items-center justify-center p-0 rounded-full">{pIndex + 1}</Badge>
                        <Controller
                          control={form.control}
                          name={`fases.${pIndex}.proceso`}
                          render={({ field }) => (
                            <div className="flex flex-col">
                              <Select value={field.value ? String(field.value) : ''} onValueChange={(v) => field.onChange(Number(v))}>
                                <SelectTrigger className="h-8 w-52" aria-label={`Proceso de la fase ${pIndex + 1}`}>
                                  <SelectValue placeholder={procesosActivos.length ? 'Seleccione proceso' : 'Sin procesos en el catálogo'} />
                                </SelectTrigger>
                                <SelectContent>
                                  {procesosActivos.map((p) => (
                                    <SelectItem key={p.id} value={String(p.id)}>{p.nombre}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {form.formState.errors.fases?.[pIndex]?.proceso && (
                                <span className="text-[10px] text-red-500 mt-0.5">{form.formState.errors.fases[pIndex]?.proceso?.message}</span>
                              )}
                            </div>
                          )}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Label className="text-[10px] uppercase opacity-60">Ciclo</Label>
                        <Input type="number" className="h-7 w-14 text-xs px-1" aria-label={`Ciclo de la fase ${pIndex + 1}`} {...form.register(`fases.${pIndex}.ciclo`, { valueAsNumber: true })} />
                        <Label className="text-[10px] uppercase opacity-60">Temp (°C)</Label>
                        <Input type="number" className="h-7 w-16 text-xs px-1" {...form.register(`fases.${pIndex}.temperatura`, { valueAsNumber: true })} />
                        <Label className="text-[10px] uppercase opacity-60">Tiempo (min)</Label>
                        <Input type="number" className="h-7 w-16 text-xs px-1" {...form.register(`fases.${pIndex}.tiempo`, { valueAsNumber: true })} />
                      </div>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removePhase(pIndex)} className="text-destructive hover:bg-destructive/10">
                      <Trash2 className="w-4 h-4"/>
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <InnerChemicalsList 
                      pIndex={pIndex} 
                      control={form.control} 
                      register={form.register} 
                      quimicos={quimicos}
                      setValue={form.setValue}
                      errors={form.formState.errors.fases?.[pIndex]?.detalles as any}
                      detallesWatcher={fasesWatcher[pIndex]?.detalles || []}
                    />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* PANEL DERECHO - CALCULADORA EN VIVO */}
          <div className="lg:w-80 flex-shrink-0 flex flex-col min-h-0">
            <Card className="bg-slate-50 border-slate-200 shadow-inner flex flex-col flex-1 min-h-0">
              <CardHeader className="py-3 px-4 bg-slate-100 border-b flex-shrink-0">
                <CardTitle className="text-sm uppercase flex items-center gap-2 text-slate-700">
                  <Calculator className="w-4 h-4 text-emerald-600"/> Pesaje en Laboratorio
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 p-4 flex flex-col flex-1 min-h-0">
                <div className="grid grid-cols-2 gap-3 flex-shrink-0 bg-white p-3 rounded-md border shadow-sm">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-slate-600">Peso (Kg)</Label>
                    <Input
                      className="h-8 text-right font-mono font-bold text-slate-700" type="number"
                      value={calculadora.peso} onChange={(e) => setCalculadora(p => ({...p, peso: e.target.value}))} placeholder="Ej: 100"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-slate-600">Litros de Baño</Label>
                    <Input
                      className="h-8 text-right font-mono font-bold text-slate-700" type="number"
                      value={calculadora.litros} onChange={(e) => setCalculadora(p => ({...p, litros: e.target.value}))} placeholder="Ej: 860"
                    />
                  </div>
                  {relacionCalculada !== null && (
                    <div className="col-span-2 text-[10px] text-slate-500 text-right">
                      Relación de baño: <span className="font-mono font-semibold text-slate-700">1:{relacionCalculada.toFixed(2)}</span>
                    </div>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                  {fasesWatcher.map((fase, fi) => (
                    <div key={fi} className="space-y-1">
                      <div className="text-[10px] uppercase font-bold text-slate-400 border-b pb-0.5 mb-1 flex justify-between">
                        <span>Fase {fi + 1}: {nombreProceso(fase.proceso)}</span>
                        <span>{fase.temperatura}°C / {fase.tiempo}'</span>
                      </div>
                      {fase.detalles.map((det, di) => {
                        if (!det.producto) return null;
                        const peso = parseFloat(calculadora.peso) || 0;
                        const litros = parseFloat(calculadora.litros) || 0;
                        const c_grl = det.tipo_calculo === 'gr_l' ? Number(det.concentracion_gr_l) : null;
                        const c_pct = det.tipo_calculo === 'pct' ? Number(det.porcentaje) : null;
                        const calc = calcularCantidad(det.tipo_calculo, c_grl, c_pct, peso, litros);
                        const valTexto = det.tipo_calculo === 'gr_l' ? `${c_grl || 0}g/l` : `${c_pct || 0}%`;

                        return (
                          <div key={di} className="flex justify-between items-center bg-white p-2 rounded border border-slate-100 shadow-sm gap-2">
                            <div className="flex flex-col flex-1 truncate">
                              <span className="text-xs font-bold truncate text-slate-700">
                                {det._productoObj?.descripcion || 'Insumo'}
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono">({valTexto})</span>
                            </div>
                            <div className="font-mono font-bold text-sm text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded flex-shrink-0">
                              {calc ? (calc.gr >= 1000 ? `${calc.kg.toFixed(3)}kg` : `${calc.gr.toFixed(2)}g`) : '0.00g'}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                  
                  {fasesWatcher.length === 0 && (
                    <div className="text-xs text-center text-slate-400 py-4">Sin insumos para pesar</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CONTROLES / FOOTER STICKY */}
        <div className="flex justify-end gap-3 pt-3 pb-2 border-t bg-background mt-auto flex-shrink-0">
          <Button type="button" variant="outline" onClick={() => setVista('lista')}>Cancelar</Button>
          <Button type="submit" disabled={guardando} className="bg-emerald-600 hover:bg-emerald-700 text-white min-w-[150px]">
            {guardando ? 'Guardando...' : (isEditing ? 'Actualizar Fórmula' : 'Crear Fórmula')}
          </Button>
        </div>

      </form>
    </div>
  );
}

// NUEVO COMPONENTE INTERNO PARA MANEJAR QUIMICOS POR FASE
function InnerChemicalsList({ pIndex, control, register, quimicos, setValue, errors, detallesWatcher }: any) {
  const { fields, append, remove, swap } = useFieldArray({
    control,
    name: `fases.${pIndex}.detalles`
  });

  return (
    <Table>
      <TableHeader className="bg-background/50">
        <TableRow>
          <TableHead className="w-8"></TableHead>
          <TableHead className="w-8">#</TableHead>
          <TableHead className="min-w-[200px]">Insumo (Infotint Sync)</TableHead>
          <TableHead className="w-24 text-center">Cálculo</TableHead>
          <TableHead className="w-32">Valor</TableHead>
          <TableHead className="w-[50px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {fields.map((field, index) => {
          const error = errors?.[index] as any;
          const watchTipoCalculo = detallesWatcher[index]?.tipo_calculo;

          return (
            <TableRow key={field.id} className={error ? "bg-red-50/50" : "group"}>
              <TableCell className="py-1">
                <div className="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100">
                  <button type="button" onClick={() => swap(index, index - 1)} disabled={index === 0} className="disabled:opacity-20 hover:text-primary"><Plus className="w-3 h-3 rotate-45" /></button>
                  <button type="button" onClick={() => swap(index, index + 1)} disabled={index === fields.length - 1} className="disabled:opacity-20 hover:text-primary"><Plus className="w-3 h-3 rotate-[135deg]" /></button>
                </div>
              </TableCell>
              <TableCell className="font-mono text-[10px] opacity-50 py-1">{index + 1}</TableCell>
              <TableCell className="py-1">
                <Controller
                  control={control}
                  name={`fases.${pIndex}.detalles.${index}.producto`}
                  render={({ field: controllerField }) => (
                    <div className="flex flex-col">
                      <BuscadorQuimico 
                        quimicos={quimicos}
                        productoSeleccionado={detallesWatcher[index]?._productoObj}
                        onSelect={(q) => {
                          controllerField.onChange(q?.id || 0);
                          setValue(`fases.${pIndex}.detalles.${index}._productoObj`, q);
                        }}
                      />
                      {error?.producto && <span className="text-[10px] text-red-500 mt-1">{error.producto.message}</span>}
                    </div>
                  )}
                />
              </TableCell>
              <TableCell className="py-1">
                <Controller
                  control={control}
                  name={`fases.${pIndex}.detalles.${index}.tipo_calculo`}
                  render={({ field: controllerField }) => (
                    <Select value={controllerField.value} onValueChange={(val) => {
                        controllerField.onChange(val);
                        if (val === 'gr_l') setValue(`fases.${pIndex}.detalles.${index}.porcentaje`, undefined);
                        else setValue(`fases.${pIndex}.detalles.${index}.concentracion_gr_l`, undefined);
                      }}>
                      <SelectTrigger className="h-7 text-[11px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gr_l">g/L</SelectItem>
                        <SelectItem value="pct">% (Agot.)</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </TableCell>
              <TableCell className="py-1">
                 <div className="flex flex-col">
                  {watchTipoCalculo === 'gr_l' ? (
                    <div className="relative">
                      <Input 
                        type="number" step="0.0001" className="h-7 text-xs pr-7"
                        {...register(`fases.${pIndex}.detalles.${index}.concentracion_gr_l`, { valueAsNumber: true })}
                      />
                      <span className="absolute right-1 top-1.5 text-[9px] opacity-40">g/L</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <Input 
                        type="number" step="0.0001" className="h-7 text-xs pr-7"
                        {...register(`fases.${pIndex}.detalles.${index}.porcentaje`, { valueAsNumber: true })}
                      />
                      <span className="absolute right-1 top-1.5 text-[9px] opacity-40">%</span>
                    </div>
                  )}
                  {error?.concentracion_gr_l && <span className="text-[10px] text-red-500 mt-0.5">{error.concentracion_gr_l.message}</span>}
                  {error?.porcentaje && <span className="text-[10px] text-red-500 mt-0.5">{error.porcentaje.message}</span>}
                 </div>
              </TableCell>
              <TableCell className="py-1 text-right">
                <button type="button" onClick={() => remove(index)} className="text-muted-foreground hover:text-red-500 p-1">
                  <Trash2 className="w-3.5 h-3.5"/>
                </button>
              </TableCell>
            </TableRow>
          );
        })}
        <TableRow className="bg-muted/5 hover:bg-muted/10">
          <TableCell colSpan={6} className="py-1 text-center">
            <Button 
              type="button" size="sm" variant="ghost" className="text-[10px] h-6 w-full text-primary"
              onClick={() => append({ producto: 0, tipo_calculo: 'gr_l', concentracion_gr_l: undefined, porcentaje: undefined, orden_adicion: fields.length + 1, notas: '' })}
            >
              <Plus className="w-3 h-3 mr-1" /> Insertar Químico / Colorante
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}