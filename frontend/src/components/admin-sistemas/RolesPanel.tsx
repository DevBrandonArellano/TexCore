import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { User } from '../../lib/types';
import type { Group } from './sedeUtils';

interface RolesPanelProps {
  groups: Group[];
  sedeUsers: User[];
}

function RolesPanelImpl({ groups, sedeUsers }: RolesPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Roles del Sistema</CardTitle>
        <CardDescription>Lista de grupos y roles configurados en la base de datos.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(Array.isArray(groups) ? groups : []).map(group => (
            <div key={group.id} className="p-4 rounded-lg bg-accent border flex items-center justify-between">
              <div>
                <p className="font-bold text-primary">{group.name.replace('_', ' ').toUpperCase()}</p>
                <p className="text-xs text-muted-foreground italic">Internal ID: {group.id}</p>
              </div>
              <Badge variant="secondary">
                {sedeUsers.filter(u => Array.isArray(u.groups) && u.groups.includes(group.id)).length} Usuarios
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export const RolesPanel = React.memo(RolesPanelImpl);
