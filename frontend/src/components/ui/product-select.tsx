"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { Producto } from "../../lib/types";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";
import { Input } from "./input";
import { cn } from "./utils";

interface ProductSelectProps {
  productos: Producto[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  showAllOption?: boolean;
  className?: string;
}

function normalizeText(text: string): string {
  return (text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function ProductSelect({
  productos,
  value,
  onValueChange,
  placeholder = "Selecciona un producto",
  showAllOption = false,
  className,
}: ProductSelectProps) {
  const [searchTerm, setSearchTerm] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Normalización defensiva de datos
  const safeProductos = React.useMemo(() => {
    return Array.isArray(productos)
      ? productos.filter((p) => p != null && p.id != null)
      : [];
  }, [productos]);

  const safeValue =
    value && value !== "all"
      ? String(value)
      : showAllOption && value === "all"
      ? "all"
      : undefined;

  // Filtrado reactivo en tiempo real por código o descripción (insensible a acentos/mayúsculas)
  const filteredProductos = React.useMemo(() => {
    if (!searchTerm.trim()) return safeProductos;
    const term = normalizeText(searchTerm);
    return safeProductos.filter((p) => {
      const cod = normalizeText(p.codigo || "");
      const desc = normalizeText(p.descripcion || "");
      const tipo = normalizeText(p.tipo || "");
      return cod.includes(term) || desc.includes(term) || tipo.includes(term);
    });
  }, [safeProductos, searchTerm]);

  // Texto para mostrar en el trigger cuando hay un producto seleccionado
  const selectedProduct = React.useMemo(() => {
    return safeProductos.find((p) => String(p.id) === String(value));
  }, [safeProductos, value]);

  const triggerLabel = selectedProduct
    ? selectedProduct.codigo
      ? `[${selectedProduct.codigo}] ${selectedProduct.descripcion || `Producto-${selectedProduct.id}`}`
      : selectedProduct.descripcion || `Producto-${selectedProduct.id}`
    : showAllOption && value === "all"
    ? "Todos los productos"
    : undefined;

  return (
    <Select
      key={value ? "filled" : "empty"}
      value={safeValue}
      onValueChange={(val) => {
        onValueChange(val);
        setSearchTerm("");
      }}
      onOpenChange={(open) => {
        if (!open) {
          setSearchTerm("");
        } else {
          // Enfocar el input de búsqueda al abrir
          setTimeout(() => {
            inputRef.current?.focus();
          }, 50);
        }
      }}
    >
      <SelectTrigger className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder}>
          {triggerLabel}
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="max-h-80 w-[var(--radix-select-trigger-width)] min-w-[18rem]">
        {/* Barra de búsqueda integrada sticky */}
        <div
          className="sticky top-0 z-20 bg-popover p-2 border-b"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative flex items-center">
            <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <Input
              ref={inputRef}
              type="text"
              placeholder="Buscar por código o descripción..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                e.stopPropagation();
                if (e.key === "Enter" && filteredProductos.length > 0) {
                  e.preventDefault();
                  onValueChange(String(filteredProductos[0].id));
                  setSearchTerm("");
                }
              }}
              className="h-8 pl-8 pr-7 text-xs bg-background"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setSearchTerm("");
                  inputRef.current?.focus();
                }}
                className="absolute right-2 text-muted-foreground hover:text-foreground"
                aria-label="Limpiar búsqueda"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
          {safeProductos.length > 0 && (
            <div className="flex items-center justify-between mt-1.5 px-1 text-[11px] text-muted-foreground">
              <span>
                {searchTerm
                  ? `${filteredProductos.length} de ${safeProductos.length} productos`
                  : `${safeProductos.length} productos disponibles`}
              </span>
              {searchTerm && (
                <span className="text-[10px] italic">Enter para seleccionar</span>
              )}
            </div>
          )}
        </div>

        {/* Lista de productos filtrados */}
        <div className="py-1">
          {showAllOption && !searchTerm && (
            <SelectItem value="all">Todos los productos</SelectItem>
          )}

          {filteredProductos.length > 0 ? (
            filteredProductos.map((producto) => {
              const prodDesc = producto.descripcion
                ? String(producto.descripcion)
                : `Producto-${producto.id}`;
              const prodCode = producto.codigo ? String(producto.codigo) : "";

              return (
                <SelectItem
                  key={`prod-${producto.id}`}
                  value={String(producto.id)}
                  className="cursor-pointer py-2"
                >
                  <div className="flex items-center justify-between gap-2 w-full text-left">
                    <div className="flex items-center gap-2 min-w-0">
                      {prodCode && (
                        <span
                          aria-hidden="true"
                          className="font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-muted text-foreground shrink-0"
                        >
                          {prodCode}
                        </span>
                      )}
                      <span className="truncate">{prodDesc}</span>
                    </div>
                    {producto.tipo && (
                      <span
                        aria-hidden="true"
                        className="text-[10px] text-muted-foreground capitalize shrink-0 ml-2 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border border-border/50"
                      >
                        {producto.tipo.replace("_", " ")}
                      </span>
                    )}
                  </div>
                </SelectItem>
              );
            })
          ) : (
            <div className="py-6 px-4 text-center text-xs text-muted-foreground">
              {searchTerm ? (
                <>
                  No se encontraron productos para{" "}
                  <span className="font-semibold text-foreground">
                    "{searchTerm}"
                  </span>
                  .
                </>
              ) : (
                "Cargando catálogo o sin resultados..."
              )}
            </div>
          )}
        </div>
      </SelectContent>
    </Select>
  );
}
