^XA
^PW800
^LL400
^FO50,30^ADN,36,20^FD{{ empresa | default('TexCore Industrial', true) }}^FS
^FO50,75^ADN,18,10^FDProducto: {{ producto_desc }}^FS
^FO50,110^ADN,18,10^FDLote: {{ lote_codigo }}^FS
^FO50,145^ADN,26,15^FDPeso Neto: {{ peso_neto }} {{ unidad | default('kg', true) }}^FS
{% if tara is defined and tara > 0 %}^FO50,180^ADN,18,10^FDPeso Bruto: {{ peso_bruto }} {{ unidad | default('kg', true) }} | Tara: {{ tara }} {{ unidad | default('kg', true) }}^FS{% endif %}
{% if cantidad_metros is defined and cantidad_metros %}^FO50,210^ADN,18,10^FDMetros: {{ cantidad_metros }}^FS{% endif %}
{% if tipo_evento == 'REIMPRESION' %}^FO500,145^ADN,22,12^FDREIMPRESION v{{ version }}^FS{% elif tipo_evento == 'REETIQUETADO' %}^FO500,145^ADN,22,12^FDREETIQUETADO v{{ version }}^FS{% endif %}
^FO50,240^BY3
^BCN,90,Y,N,N
^FD{{ lote_codigo }}^FS
^FO550,50^BQN,2,5
^FDQA,{{ qr_data }}^FS
^XZ
