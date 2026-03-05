import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';

export function MovementApproval() {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Aprobación de Movimientos</CardTitle>
                <CardDescription>
                    Este módulo no está activo actualmente. Todos los movimientos se procesan de forma inmediata para agilizar la operación.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground text-sm">
                    La lógica de aprobación manual ha sido deshabilitada para evitar cuellos de botella operativos.
                </p>
            </CardContent>
        </Card>
    );
}