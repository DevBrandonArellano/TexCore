"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";
import { Input } from "./input";
import { cn } from "./utils";

export interface SearchableSelectItem {
  value: string;
  label: string;
}

interface SearchableSelectProps {
  // Lista plana de strings (país, calidad, etc.) o items {value,label}
  // (cuando el value real, ej. un id, difiere del texto mostrado/buscado).
  options?: string[];
  items?: SearchableSelectItem[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  className?: string;
  id?: string;
}

function normalizeText(text: string): string {
  return (text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

// Select con búsqueda integrada para listas planas (países, proveedores,
// etc.) — mismo patrón que ProductSelect pero sin depender del shape de
// Producto. Acepta `options` (strings) o `items` ({value,label}, para
// cuando el value es un id numérico distinto del texto buscable).
export function SearchableSelect({
  options,
  items,
  value,
  onValueChange,
  placeholder = "Selecciona una opción",
  searchPlaceholder = "Buscar...",
  emptyLabel = "Sin resultados",
  className,
  id,
}: SearchableSelectProps) {
  const [searchTerm, setSearchTerm] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  const allItems: SearchableSelectItem[] = React.useMemo(() => {
    if (items) return items;
    return (options ?? []).map((opt) => ({ value: opt, label: opt }));
  }, [items, options]);

  const filteredItems = React.useMemo(() => {
    if (!searchTerm.trim()) return allItems;
    const term = normalizeText(searchTerm);
    return allItems.filter((item) => normalizeText(item.label).includes(term));
  }, [allItems, searchTerm]);

  return (
    <Select
      value={value || undefined}
      onValueChange={(val) => {
        onValueChange(val);
        setSearchTerm("");
      }}
      onOpenChange={(open) => {
        if (!open) {
          setSearchTerm("");
        } else {
          setTimeout(() => inputRef.current?.focus(), 50);
        }
      }}
    >
      <SelectTrigger id={id} className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent className="max-h-80 w-[var(--radix-select-trigger-width)] min-w-[14rem]">
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
              placeholder={searchPlaceholder}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                e.stopPropagation();
                if (e.key === "Enter" && filteredItems.length > 0) {
                  e.preventDefault();
                  onValueChange(filteredItems[0].value);
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
        </div>

        <div className="py-1">
          {filteredItems.length > 0 ? (
            filteredItems.map((item) => (
              <SelectItem key={item.value} value={item.value} className="cursor-pointer py-2">
                {item.label}
              </SelectItem>
            ))
          ) : (
            <div className="py-6 px-4 text-center text-xs text-muted-foreground">
              {searchTerm ? (
                <>
                  {emptyLabel} para{" "}
                  <span className="font-semibold text-foreground">"{searchTerm}"</span>.
                </>
              ) : (
                emptyLabel
              )}
            </div>
          )}
        </div>
      </SelectContent>
    </Select>
  );
}
