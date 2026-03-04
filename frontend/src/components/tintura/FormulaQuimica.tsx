import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Skeleton } from '../ui/skeleton';
import { toast } from 'sonner';
import {
  FlaskConical,
  Plus,
  Pencil,
  Copy,
  Trash2,
  ChevronRight,
  ArrowLeft,
  Calculator,
  Search,
  CheckCircle2,
  Clock,
  GripVertical,
  X,
} from 'lucide-react';
import { FormulaColor, DetalleFormula, Quimico } from '../../lib/types';

// ---------------------------------------------------------------------------
// Tipos locales
// ---------------------------------------------------------------------------

interface FormulaColorWrite {
  codigo: string;
  nombre_color: string;
  description: string;
  tipo_sustrato: string;
  estado: string;
  observaciones: string;
  detalles: DetalleWrite[];
}

interface DetalleWrite {
  id?: number;
  producto: number;
  gramos_por_kilo: number;
  tipo_calculo: 'gr_l' | 'pct';
  concentracion_gr_l?: number | null;
  porcentaje?: number | null;
  orden_adicion: number;
  notas: string;
  // Campos de UI (no se envian al backend)
  _productoObj?: Quimico;
}

interface CalculadoraState {
  kg_tela: string;
  relacion_bano: string;
}

// ---------------------------------------------------------------------------
// Helpers de calculo de dosificacion (ejecutados en el cliente)
// ---------------------------------------------------------------------------

function calcularCantidad(detalle: DetalleWrite, kgTela: number, relacionBano: number): { kg: number; gr: number } | null {
  if (kgTela <= 0 || relacionBano <= 0) return null;
  const volumenLitros = kgTela * relacionBano;
  let cantidadKg = 0;

  if (detalle.tipo_calculo === 'gr_l') {
    const conc = detalle.concentracion_gr_l ?? 0;
    cantidadKg = (volumenLitros * conc) / 1000;
  } else {
    const pct = detalle.porcentaje ?? 0;
    cantidadKg = (kgTela * pct) / 100;
  }

  return { kg: cantidadKg, gr: cantidadKg * 1000 };
}

// ---------------------------------------------------------------------------
// Subcomponente: Fila de busqueda de quimico con autocompletado
// ---------------------------------------------------------------------------

interface BuscadorQuimicoProps {
  quimicos: Quimico[];
  productoSeleccionado: Quimico | null;
  onSelect: (q: Quimico) => void;
  disabled?: boolean;
}

function BuscadorQuimico({ quimicos, productoSeleccionado, onSelect, disabled }: BuscadorQuimicoProps) {
  const [query, setQuery] = useState('');
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtrados = useMemo(() => {
    if (!query.trim()) return quimicos.slice(0, 12);
    const q = query.toLowerCase();
    return quimicos.filter(
      (qu) =>
        qu.descripcion.toLowerCase().includes(q) ||
        qu.codigo.toLowerCase().includes(q)
    ).slice(0, 12);
  }, [query, quimicos]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setAbierto(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (productoSeleccionado) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium">{productoSeleccionado.descripcion}</span>
        <span className="text-muted-foreground font-mono text-xs">({productoSeleccionado.codigo})</span>
        {!disabled && (
          <button
            type="button"
            className="text-muted-foreground hover:text-destructive transition-colors"
            onClick={() => setQuery('')}
            title="Cambiar insumo"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative" ref={ref}>
      <div className="flex items-center gap-1 border rounded-md px-2 py-1 bg-background">
        <Search className="w-3 h-3 text-muted-foreground flex-shrink-0" />
        <input
          className="flex-1 text-sm bg-transparent outline-none placeholder:text-muted-foreground"
          placeholder="Buscar quimico..."
          value={query}
          onFocus={() => setAbierto(true)}
          onChange={(e) => { setQuery(e.target.value); setAbierto(true); }}
          disabled={disabled}
        />
      </div>
      {abierto && filtrados.length > 0 && (
        <ul className="absolute z-50 top-full mt-1 left-0 right-0 bg-popover border rounded-md shadow-lg max-h-52 overflow-y-auto">
          {filtrados.map((q) => (
            <li
              key={q.id}
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-accent transition-colors"
              onMouseDown={(e) => {
                e.preventDefault();
                onSelect(q);
                setAbierto(false);
                setQuery('');
              }}
            >
              <span className="font-mono text-xs text-muted-foreground w-20 flex-shrink-0">{q.codigo}</span>
              <span className="truncate">{q.descripcion}</span>
            </li>
          ))}
        </ul>
      )}
      {abierto && filtrados.length === 0 && (
        <div className="absolute z-50 top-full mt-1 left-0 right-0 bg-popover border rounded-md shadow-lg px-3 py-2 text-sm text-muted-foreground">
          Sin resultados para "{query}"
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props del componente principal
// ---------------------------------------------------------------------------

interface FormulaQuimicaProps {
  formulas: FormulaColor[];
  quimicos: Quimico[];
  loading: boolean;
  canDelete?: boolean;
  onFormulaCreate: (data: FormulaColorWrite) => Promise<boolean>;
  onFormulaUpdate: (id: number, data: FormulaColorWrite) => Promise<boolean>;
  onFormulaDuplicate: (id: number) => Promise<boolean>;
  onFormulaDelete: (id: number) => void;
}

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------

const TIPO_SUSTRATO_LABELS: Record<string, string> = {
  algodon: 'Algodon',
  poliester: 'Poliester',
  nylon: 'Nylon',
  mixto: 'Mixto',
  otro: 'Otro',
};

function formulaVacia(): FormulaColorWrite {
  return {
    codigo: '',
    nombre_color: '',
    description: '',
    tipo_sustrato: 'algodon',
    estado: 'en_pruebas',
    observaciones: '',
    detalles: [],
  };
}

export function FormulaQuimica({
  formulas,
  quimicos,
  loading,
  canDelete = true,
  onFormulaCreate,
  onFormulaUpdate,
  onFormulaDuplicate,
  onFormulaDelete,
}: FormulaQuimicaProps) {
  // --- Estado de vistas ---
  const [vista, setVista] = useState<'lista' | 'editor'>('lista');
  const [formulaEditor, setFormulaEditor] = useState<FormulaColorWrite>(formulaVacia());
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [guardando, setGuardando] = useState(false);

  // --- Estado de busqueda en lista ---
  const [busqueda, setBusqueda] = useState('');

  // --- Estado de calculadora ---
  const [calculadora, setCalculadora] = useState<CalculadoraState>({ kg_tela: '', relacion_bano: '10' });

  // --- Estado de confirmacion de eliminacion ---
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // ---------------------------------------------------------------------------
  // Calculo de dosificacion en tiempo real
  // ---------------------------------------------------------------------------

  const kgTela = parseFloat(calculadora.kg_tela) || 0;
  const relacionBano = parseFloat(calculadora.relacion_bano) || 0;
  const volumenLitros = kgTela * relacionBano;

  const cantidadesPorDetalle = useMemo<Map<number, { kg: number; gr: number } | null>>(() => {
    const map = new Map<number, { kg: number; gr: number } | null>();
    formulaEditor.detalles.forEach((d, idx) => {
      map.set(idx, calcularCantidad(d, kgTela, relacionBano));
    });
    return map;
  }, [formulaEditor.detalles, kgTela, relacionBano]);

  // ---------------------------------------------------------------------------
  // Lista filtrada
  // ---------------------------------------------------------------------------

  const formulasFiltradas = useMemo(() => {
    if (!busqueda.trim()) return formulas;
    const q = busqueda.toLowerCase();
    return formulas.filter(
      (f) =>
        f.codigo.toLowerCase().includes(q) ||
        f.nombre_color.toLowerCase().includes(q) ||
        (f.description || '').toLowerCase().includes(q)
    );
  }, [formulas, busqueda]);

  // ---------------------------------------------------------------------------
  // Handlers de editor de formula
  // ---------------------------------------------------------------------------

  function abrirCrear() {
    setEditandoId(null);
    setFormulaEditor(formulaVacia());
    setCalculadora({ kg_tela: '', relacion_bano: '10' });
    setVista('editor');
  }

  function abrirEditar(formula: FormulaColor) {
    setEditandoId(formula.id);
    const detallesWrite: DetalleWrite[] = (formula.detalles || []).map((d) => {
      const productoObj = quimicos.find((q) => q.id === d.producto) || null;
      return {
        id: d.id,
        producto: d.producto,
        gramos_por_kilo: d.gramos_por_kilo,
        tipo_calculo: d.tipo_calculo,
        concentracion_gr_l: d.concentracion_gr_l ?? null,
        porcentaje: d.porcentaje ?? null,
        orden_adicion: d.orden_adicion,
        notas: d.notas || '',
        _productoObj: productoObj ?? undefined,
      };
    });
    setFormulaEditor({
      codigo: formula.codigo,
      nombre_color: formula.nombre_color,
      description: formula.description || '',
      tipo_sustrato: formula.tipo_sustrato,
      estado: formula.estado,
      observaciones: formula.observaciones || '',
      detalles: detallesWrite,
    });
    setCalculadora({ kg_tela: '', relacion_bano: '10' });
    setVista('editor');
  }

  function agregarDetalle() {
    setFormulaEditor((prev) => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        {
          producto: 0,
          gramos_por_kilo: 0,
          tipo_calculo: 'gr_l',
          concentracion_gr_l: null,
          porcentaje: null,
          orden_adicion: prev.detalles.length + 1,
          notas: '',
        },
      ],
    }));
  }

  function actualizarDetalle(idx: number, cambios: Partial<DetalleWrite>) {
    setFormulaEditor((prev) => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[idx] = { ...nuevosDetalles[idx], ...cambios };
      return { ...prev, detalles: nuevosDetalles };
    });
  }

  function seleccionarQuimico(idx: number, quimico: Quimico) {
    // Verificar duplicados
    const yaExiste = formulaEditor.detalles.some(
      (d, i) => i !== idx && d.producto === quimico.id
    );
    if (yaExiste) {
      toast.error(`"${quimico.descripcion}" ya esta en esta formula. No se permiten insumos duplicados.`);
      return;
    }
    actualizarDetalle(idx, { producto: quimico.id, _productoObj: quimico });
  }

  function eliminarDetalle(idx: number) {
    setFormulaEditor((prev) => {
      const nuevos = prev.detalles.filter((_, i) => i !== idx).map((d, i) => ({
        ...d,
        orden_adicion: i + 1,
      }));
      return { ...prev, detalles: nuevos };
    });
  }

  function validar(): boolean {
    if (!formulaEditor.codigo.trim()) {
      toast.error('El codigo de formula es requerido.');
      return false;
    }
    if (!formulaEditor.nombre_color.trim()) {
      toast.error('El nombre de color es requerido.');
      return false;
    }
    for (let i = 0; i < formulaEditor.detalles.length; i++) {
      const d = formulaEditor.detalles[i];
      if (!d.producto) {
        toast.error(`La fila ${i + 1} no tiene un insumo seleccionado.`);
        return false;
      }
      if (d.tipo_calculo === 'gr_l' && (!d.concentracion_gr_l || d.concentracion_gr_l <= 0)) {
        toast.error(`La fila ${i + 1}: concentracion gr/L debe ser mayor a 0.`);
        return false;
      }
      if (d.tipo_calculo === 'pct' && (!d.porcentaje || d.porcentaje <= 0)) {
        toast.error(`La fila ${i + 1}: el porcentaje debe ser mayor a 0.`);
        return false;
      }
    }
    // Verificar duplicados a nivel global (por si acaso el usuario penso el control)
    const ids = formulaEditor.detalles.map((d) => d.producto).filter(Boolean);
    if (new Set(ids).size !== ids.length) {
      toast.error('Hay insumos duplicados en la formula.');
      return false;
    }
    return true;
  }

  async function guardar() {
    if (!validar()) return;
    setGuardando(true);

    const payload: FormulaColorWrite = {
      ...formulaEditor,
      detalles: formulaEditor.detalles.map(({ _productoObj, ...rest }) => rest),
    };

    let exito = false;
    if (editandoId) {
      exito = await onFormulaUpdate(editandoId, payload);
    } else {
      exito = await onFormulaCreate(payload);
    }

    setGuardando(false);
    if (exito) {
      setVista('lista');
    }
  }

  async function duplicar(id: number) {
    const exito = await onFormulaDuplicate(id);
    if (exito) {
      toast.success('Nueva version de la formula creada en estado "En Pruebas".');
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers de UI
  // ---------------------------------------------------------------------------

  function EstadoBadge({ estado }: { estado: string }) {
    if (estado === 'aprobada') {
      return (
        <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1">
          <CheckCircle2 className="w-3 h-3" />
          Aprobada
        </Badge>
      );
    }
    return (
      <Badge variant="secondary" className="gap-1">
        <Clock className="w-3 h-3" />
        En Pruebas
      </Badge>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Lista de formulas
  // ---------------------------------------------------------------------------

  if (vista === 'lista') {
    return (
      <Card className="flex flex-col h-full min-h-0">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FlaskConical className="w-5 h-5 text-primary" />
                Formulas Quimicas
              </CardTitle>
              <CardDescription>Gestion de recetas de tintoreria y acabados</CardDescription>
            </div>
            <Button onClick={abrirCrear} id="btn-nueva-formula">
              <Plus className="w-4 h-4 mr-2" />
              Nueva Formula
            </Button>
          </div>
          <Input
            id="busqueda-formulas"
            placeholder="Buscar por codigo, nombre de color..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </CardHeader>
        <CardContent className="flex-1 min-h-0 flex flex-col pt-0">
          <div className="flex-1 overflow-auto rounded-md border relative">
            <Table className="min-w-max">
              <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
                <TableRow>
                  <TableHead>Codigo</TableHead>
                  <TableHead>Nombre de Color</TableHead>
                  <TableHead>Sustrato</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Insumos</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  Array.from({ length: 4 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 7 }).map((__, j) => (
                        <TableCell key={j}><Skeleton className="h-5 w-full" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : formulasFiltradas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      {busqueda ? 'Sin resultados para la busqueda.' : 'No hay formulas registradas.'}
                    </TableCell>
                  </TableRow>
                ) : (
                  formulasFiltradas.map((formula) => (
                    <TableRow key={formula.id}>
                      <TableCell className="font-mono text-xs font-semibold">{formula.codigo}</TableCell>
                      <TableCell className="font-medium">{formula.nombre_color}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{TIPO_SUSTRATO_LABELS[formula.tipo_sustrato] ?? formula.tipo_sustrato}</Badge>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">v{formula.version}</span>
                      </TableCell>
                      <TableCell><EstadoBadge estado={formula.estado} /></TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {formula.detalles?.length ?? 0} insumo{(formula.detalles?.length ?? 0) !== 1 ? 's' : ''}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-1 justify-end">
                          <Button
                            size="sm" variant="outline"
                            onClick={() => abrirEditar(formula)}
                            title="Ver / Editar"
                            id={`btn-editar-formula-${formula.id}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm" variant="outline"
                            onClick={() => duplicar(formula.id)}
                            title="Duplicar (nueva version)"
                            id={`btn-duplicar-formula-${formula.id}`}
                          >
                            <Copy className="w-4 h-4" />
                          </Button>
                          {canDelete && (
                            <Button
                              size="sm" variant="destructive"
                              onClick={() => setConfirmDeleteId(formula.id)}
                              title="Eliminar formula"
                              id={`btn-eliminar-formula-${formula.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>

        {/* Dialog de confirmacion de eliminacion */}
        <Dialog open={confirmDeleteId !== null} onOpenChange={() => setConfirmDeleteId(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Confirmar eliminacion</DialogTitle>
              <DialogDescription>
                Esta accion es irreversible. La formula y todos sus detalles seran eliminados permanentemente.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirmDeleteId(null)}>Cancelar</Button>
              <Button variant="destructive" onClick={() => {
                if (confirmDeleteId) onFormulaDelete(confirmDeleteId);
                setConfirmDeleteId(null);
              }}>Eliminar</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Card>
    );
  }

  // ---------------------------------------------------------------------------
  // RENDER: Editor de formula
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Cabecera del editor */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => setVista('lista')} id="btn-volver-lista">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Formulas
        </Button>
        <ChevronRight className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium">
          {editandoId ? `Editando: ${formulaEditor.nombre_color}` : 'Nueva Formula'}
        </span>
      </div>

      <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4">
        {/* Panel izquierdo: Datos de cabecera + tabla de insumos */}
        <div className="lg:flex-1 flex flex-col min-w-0 space-y-4">

          {/* Datos de cabecera */}
          <Card className="flex-shrink-0">
            <CardHeader>
              <CardTitle className="text-base">Datos de la Formula</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ec-codigo">Codigo <span className="text-destructive">*</span></Label>
                  <Input
                    id="ec-codigo"
                    placeholder="Ej: FC-001"
                    value={formulaEditor.codigo}
                    onChange={(e) => setFormulaEditor((p) => ({ ...p, codigo: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ec-nombre">Nombre de Color <span className="text-destructive">*</span></Label>
                  <Input
                    id="ec-nombre"
                    placeholder="Ej: Azul Marino Intenso"
                    value={formulaEditor.nombre_color}
                    onChange={(e) => setFormulaEditor((p) => ({ ...p, nombre_color: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ec-sustrato">Tipo de Sustrato</Label>
                  <Select
                    value={formulaEditor.tipo_sustrato}
                    onValueChange={(v) => setFormulaEditor((p) => ({ ...p, tipo_sustrato: v }))}
                  >
                    <SelectTrigger id="ec-sustrato">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TIPO_SUSTRATO_LABELS).map(([val, label]) => (
                        <SelectItem key={val} value={val}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ec-estado">Estado</Label>
                  <Select
                    value={formulaEditor.estado}
                    onValueChange={(v) => setFormulaEditor((p) => ({ ...p, estado: v }))}
                  >
                    <SelectTrigger id="ec-estado">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en_pruebas">En Pruebas</SelectItem>
                      <SelectItem value="aprobada">Aprobada</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="ec-descripcion">Descripcion</Label>
                  <Input
                    id="ec-descripcion"
                    placeholder="Descripcion general de la formula..."
                    value={formulaEditor.description}
                    onChange={(e) => setFormulaEditor((p) => ({ ...p, description: e.target.value }))}
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="ec-observaciones">Observaciones</Label>
                  <Input
                    id="ec-observaciones"
                    placeholder="Notas adicionales, condiciones de proceso, etc."
                    value={formulaEditor.observaciones}
                    onChange={(e) => setFormulaEditor((p) => ({ ...p, observaciones: e.target.value }))}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tabla dinamica de insumos */}
          <Card className="flex-1 flex flex-col min-h-0">
            <CardHeader className="flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Insumos Quimicos</CardTitle>
                <Button size="sm" variant="outline" onClick={agregarDetalle} id="btn-agregar-insumo">
                  <Plus className="w-4 h-4 mr-1" />
                  Agregar Insumo
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {formulaEditor.detalles.length === 0 ? (
                <div className="text-center text-muted-foreground py-10 border-2 border-dashed rounded-lg">
                  <FlaskConical className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">Sin insumos. Haz clic en "Agregar Insumo" para comenzar.</p>
                </div>
              ) : (
                <div className="flex-1 overflow-auto rounded-md border relative">
                  <Table className="min-w-max">
                    <TableHeader className="sticky top-0 z-10 bg-slate-50 shadow-sm border-b">
                      <TableRow>
                        <TableHead className="w-6"></TableHead>
                        <TableHead>Insumo Quimico</TableHead>
                        <TableHead className="w-32">Tipo de Calculo</TableHead>
                        <TableHead className="w-32">Valor</TableHead>
                        <TableHead className="w-20">Orden</TableHead>
                        <TableHead>Notas</TableHead>
                        <TableHead className="w-10"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {formulaEditor.detalles.map((det, idx) => {
                        const calc = cantidadesPorDetalle.get(idx);
                        return (
                          <TableRow key={idx}>
                            {/* Handle de orden */}
                            <TableCell>
                              <GripVertical className="w-4 h-4 text-muted-foreground" />
                            </TableCell>

                            {/* Autocompletado de quimico */}
                            <TableCell className="min-w-[220px]">
                              <BuscadorQuimico
                                quimicos={quimicos}
                                productoSeleccionado={det._productoObj ?? null}
                                onSelect={(q) => seleccionarQuimico(idx, q)}
                              />
                              {calc && (
                                <div className="mt-1 text-xs text-emerald-600 font-mono">
                                  {calc.gr.toFixed(2)} gr &nbsp;/&nbsp; {calc.kg.toFixed(4)} kg
                                </div>
                              )}
                            </TableCell>

                            {/* Tipo de calculo */}
                            <TableCell>
                              <Select
                                value={det.tipo_calculo}
                                onValueChange={(v) =>
                                  actualizarDetalle(idx, {
                                    tipo_calculo: v as 'gr_l' | 'pct',
                                    concentracion_gr_l: null,
                                    porcentaje: null,
                                  })
                                }
                              >
                                <SelectTrigger className="h-8 text-xs">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="gr_l">gr/L</SelectItem>
                                  <SelectItem value="pct">% Agot.</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>

                            {/* Valor segun tipo de calculo */}
                            <TableCell>
                              {det.tipo_calculo === 'gr_l' ? (
                                <Input
                                  className="h-8 text-xs"
                                  type="number"
                                  min="0"
                                  step="0.001"
                                  placeholder="gr/L"
                                  value={det.concentracion_gr_l ?? ''}
                                  onChange={(e) =>
                                    actualizarDetalle(idx, {
                                      concentracion_gr_l: e.target.value ? Number(e.target.value) : null,
                                      gramos_por_kilo: e.target.value ? Number(e.target.value) : 0,
                                    })
                                  }
                                />
                              ) : (
                                <Input
                                  className="h-8 text-xs"
                                  type="number"
                                  min="0"
                                  max="100"
                                  step="0.001"
                                  placeholder="%"
                                  value={det.porcentaje ?? ''}
                                  onChange={(e) =>
                                    actualizarDetalle(idx, {
                                      porcentaje: e.target.value ? Number(e.target.value) : null,
                                      gramos_por_kilo: e.target.value ? Number(e.target.value) : 0,
                                    })
                                  }
                                />
                              )}
                            </TableCell>

                            {/* Orden de adicion */}
                            <TableCell>
                              <Input
                                className="h-8 text-xs w-16"
                                type="number"
                                min="1"
                                value={det.orden_adicion}
                                onChange={(e) =>
                                  actualizarDetalle(idx, { orden_adicion: Number(e.target.value) })
                                }
                              />
                            </TableCell>

                            {/* Notas */}
                            <TableCell>
                              <Input
                                className="h-8 text-xs"
                                placeholder="Observaciones..."
                                value={det.notas}
                                onChange={(e) => actualizarDetalle(idx, { notas: e.target.value })}
                              />
                            </TableCell>

                            {/* Eliminar fila */}
                            <TableCell>
                              <button
                                type="button"
                                className="text-muted-foreground hover:text-destructive transition-colors"
                                onClick={() => eliminarDetalle(idx)}
                                title="Eliminar este insumo"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Botones de guardado */}
          <div className="flex justify-end gap-2 flex-shrink-0 pb-2">
            <Button variant="outline" onClick={() => setVista('lista')} disabled={guardando}>
              Cancelar
            </Button>
            <Button onClick={guardar} disabled={guardando} id="btn-guardar-formula">
              {guardando ? 'Guardando...' : editandoId ? 'Actualizar Formula' : 'Crear Formula'}
            </Button>
          </div>
        </div>

        {/* Panel derecho: Calculadora de pesaje */}
        <div className="lg:w-80 flex-shrink-0">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Calculator className="w-4 h-4 text-primary" />
                Calculadora de Pesaje
              </CardTitle>
              <CardDescription>Calcula cantidades en tiempo real segun el bano de tintura</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="calc-kg-tela" className="text-xs">Kg de Tela</Label>
                  <Input
                    id="calc-kg-tela"
                    type="number"
                    min="0"
                    step="0.5"
                    placeholder="100"
                    value={calculadora.kg_tela}
                    onChange={(e) => setCalculadora((p) => ({ ...p, kg_tela: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="calc-relacion" className="text-xs">Relacion de Bano</Label>
                  <Input
                    id="calc-relacion"
                    type="number"
                    min="1"
                    step="1"
                    placeholder="10"
                    value={calculadora.relacion_bano}
                    onChange={(e) => setCalculadora((p) => ({ ...p, relacion_bano: e.target.value }))}
                  />
                </div>
              </div>

              {kgTela > 0 && relacionBano > 0 && (
                <div className="rounded-md bg-muted/60 border text-sm px-3 py-2">
                  <span className="text-muted-foreground text-xs">Volumen de bano:</span>
                  <span className="font-mono font-semibold ml-2">{volumenLitros.toFixed(1)} L</span>
                </div>
              )}

              {formulaEditor.detalles.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Agrega insumos a la formula para ver el calculo aqui.
                </p>
              ) : (
                <div className="space-y-2">
                  {formulaEditor.detalles.map((det, idx) => {
                    const calc = cantidadesPorDetalle.get(idx);
                    const nombre = det._productoObj?.descripcion ?? `Insumo ${idx + 1}`;
                    return (
                      <div key={idx} className="rounded-md border bg-card p-2.5">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium truncate">{nombre}</p>
                            <p className="text-xs text-muted-foreground">
                              {det.tipo_calculo === 'gr_l'
                                ? `${det.concentracion_gr_l ?? 0} gr/L`
                                : `${det.porcentaje ?? 0}%`}
                              {' '}&middot; Orden {det.orden_adicion}
                            </p>
                          </div>
                          {calc ? (
                            <div className="text-right flex-shrink-0">
                              <p className="text-sm font-mono font-semibold text-emerald-600">
                                {calc.gr.toFixed(2)} gr
                              </p>
                              <p className="text-xs text-muted-foreground font-mono">
                                {calc.kg.toFixed(4)} kg
                              </p>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground italic">—</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
