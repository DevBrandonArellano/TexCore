"use client"

import * as React from "react"
import { Producto } from "../../lib/types"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select"

interface ProductSelectProps {
    productos: Producto[]
    value: string
    onValueChange: (value: string) => void
    placeholder?: string
    showAllOption?: boolean
}

export function ProductSelect({
    productos,
    value,
    onValueChange,
    placeholder = "Selecciona un producto",
    showAllOption = false,
}: ProductSelectProps) {
    // Si value viene de afuera como un string vacío o algo que no coincide,
    // el `<Select>` de Shadcn/Radix prefiere un `undefined` para mantener su placeholder en lugar de romper con un valor vacío "".
    const safeValue = value && value !== "all" ? String(value) : (showAllOption && value === "all" ? "all" : undefined);

    // Filtramos defensivamente para asegurar que NINGÚN producto tenga ID undefined o nulo, 
    // lo que causó el Error de WSOD (Pantalla Blanca en 192.168.5.x).
    const safeProductos = Array.isArray(productos)
        ? productos.filter(p => p != null && p.id != null)
        : [];

    return (
        <Select key={value ? 'filled' : 'empty'} value={safeValue} onValueChange={onValueChange}>
            <SelectTrigger className="w-full">
                <SelectValue placeholder={placeholder} />
            </SelectTrigger>
            <SelectContent>
                {showAllOption && (
                    <SelectItem value="all">Todos los productos</SelectItem>
                )}
                {safeProductos.length > 0 ? (
                    safeProductos.map((producto) => {
                        const prodDesc = producto.descripcion
                            ? String(producto.descripcion)
                            : `Producto-${producto.id}`;

                        return (
                            <SelectItem key={`prod-${producto.id}`} value={String(producto.id)}>
                                {prodDesc}
                            </SelectItem>
                        )
                    })
                ) : (
                    <div className="relative flex w-full cursor-default select-none items-center rounded-sm py-2 px-2 text-sm outline-none text-muted-foreground justify-center">
                        Cargando catálogo o sin resultados...
                    </div>
                )}
            </SelectContent>
        </Select>
    )
}
