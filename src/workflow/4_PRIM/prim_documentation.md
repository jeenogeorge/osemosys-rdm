# Configuración del Módulo PRIM

**Objetivo**: Establecer los pasos y artefactos necesarios para reproducir la ejecución del PRIM (inputs en Excel, scripts de Python y archivos YAML).

## Flujo del Pipeline/Workflow

### Orden de ejecución para replicar el PRIM:

1. **Preparación de datos de entrada**
   - Completar `prim_structure.xlsx` (hojas Sequences y Outcomes)
   - Llenar archivo `Population.xlsx` con datos demográficos
   - Configurar `prim_files_creator_cntrl.xlsx` con parámetros de control
   - Configurar `Units.xlsx` con unidades de medida para drivers

2. **Configuración YAML**
   - Verificar y ajustar `PRIM_t3f2.yaml` según necesidades del proyecto

3. **Ejecución de scripts Python (en orden)**
   - `t3f1_prim_structure.py` - Procesa la estructura PRIM y genera `prim_files_creator.pickle`
   - `t3f2_prim_files_creator.py` - Crea archivos PRIM usando datos de experimentos
   - `t3f3_prim_manager.py` - Ejecuta el análisis PRIM y genera resultados
   - `t3f4_range_finder_mapping.py` - Mapea rangos predominantes de drivers

## Entradas Requeridas

- `t3b_sdiscovery/Analysis_1/prim_structure.xlsx` (hojas Sequences y Outcomes)
- `Population.xlsx` (población histórica/proyectada)
- `prim_files_creator_cntrl.xlsx` (control de ejecución)
- Archivo YAML de configuración: `PRIM_t3f2.yaml`
- `t3b_sdiscovery/Units.xlsx` (definición de unidades por driver)
- Scripts de Python del pipeline PRIM

## Notas Importantes

- **Mantener nombres de columnas exactamente como aparecen en los machotes**
- Las hojas no utilizadas en `prim_structure.xlsx` son: Indications, Qs_and_Notes, Command_Desc, Set_Matching_4_Param_Mult (2)

---

# Machotes de Llenado

---

## 1. prim_structure.xlsx

### Hoja: Sequences

Esta hoja define la estructura completa del análisis PRIM con drivers y outcomes.

**IMPORTANTE**: Cuando el formato requiera separación por punto y coma, usar siempre: espacio + punto y coma + espacio (ejemplo: "valor1 ; valor2 ; valor3")

#### Columnas de Identificación

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| **Table_ID** | Identificador único de la tabla PRIM | Entero positivo | Secuencial comenzando en 1 | 1 |
| **Level** | Nivel jerárquico del análisis | Entero | 1, 2, 3 | 1 |
| **Block_ID** | Identificador del bloque temático | Mismo valor de columna "Table_ID" | Entero positivo | 1 |
| Apply | Indicador para aplicar esta configuración | Texto | YES/NO | YES |

#### Columnas de Driver

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| **Outcome_ID_as_Driver** | ID cuando un outcome actúa como driver, solo se cuando el valor de la columna "Driver_Type" es "Metric of interest" o "Intermediary", de lo contrario queda vacío | Valor de la columna "Outcome_ID" de la hoja "Outcomes", con mismo nombre | Entero o vacío | 2 |
| **Driver_U_ID** | Identificador único del driver para evitar duplicación, solo se cuando el valor de la columna "Driver_Type" es "Uncertainty", de lo contrario queda vacío | Entero o vacío | Entero único o vacío | 1 |
| **Driver_ID** | Identificador secuencial del driver | Entero secuencial | Entero positivo secuencial comenzando en 1 | 1 |
| Driver_Formula_Last | Especifica qué valor del período usar | Texto | AVG: average de un periodo, END: valor final de un periodo, START: valor inicial de un periodo | AVG |
| **Driver_Type** | Clasificación del tipo de driver | Texto | Uncertainty: incertidumbre de experimento RDM, Metric of interest: métrica de interés de salidas, Intermediary: Dirver del cual tiene dependencia la métrica de interés | Intermediary |
| Driver | Nombre del driver con sufijo que indica tipo de análisis. Debe coincidir exactamente con los nombres generados en la hoja "Outcomes" y en el caso de incertidumbres con los nombres de las incertidumbre del experimento RDM | Texto descriptivo | N/A | Benefit AFOLU |
| **Driver_Actor** | Actor o entidad asociada al driver | Texto | Country, Region, Sector | Country |
| Driver_Source | Origen de los datos del driver | Texto | OSeMOSYS-ModelName inputs, OSeMOSYS-ModelName outputs, TEM output, Experiment data | OSeMOSYS-ModelName outputs |
| **Driver_Formula_Numerator** | Fórmula del numerador | Texto | Revisar tabla "Formula Numerator" | sum_across |
| **Driver_Formula_Denominator** | Fórmula del denominador | Texto | none, Den_GDP: denominador con valor GDP, tracost_at2019: costo de transporte al año 2019, totcost_at2019: costo total al año 2019 | none |
| Driver_Involved_Sets | Tecnologías o combustibles involucrados según el valor de la columna "Driver_Exact_Parameters_Involved" | Lista con formato: espacio ; espacio | Lista de tecnologías/combustibles | TRAUTDSL ; TRAUTGSL ; TRAUTELE |
| **Driver_Supporting_Sets** | | Sets de soporte adicionales, cuando el parámetro depende de otro set además de TECHNOLOGY O FUEL, lo usual es que si depende sea de EMISSION | Texto o lista con formato: espacio ; espacio | none o lista separada | CO2e |
| Driver_Exact_Parameters_Involved | Parámetros específicos del modelo OSeMOSYS y MOMF. Revisar parámetros disponibles en los outputs del experimento RDM | Lista con formato: espacio ; espacio | Variables OSeMOSYS estándar y específicas MOMF como Capex2025, VarOpex2025, FixedOpex2025, Externalities2025 | Capex2025 ; VarOpex2025 |
| Driver_Tech_or_Fuel_or_Actor | Tipo de elemento modelado | Texto | Tech, Fuel | Tech |
| Driver_Column_Management | Método de gestión de columnas resultantes | Texto | Revisar tabla "Formula Column Management" | none |
| **Driver_Numerator_Sum_Sets** | Sets a sumar en el numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | none |
| **Driver_Numerator_Sub_Sets** | Sets a restar en el numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Driver_Denominator_Sum_Sets** | Sets a sumar en el denominador | Texto | **none** | none |
| **Driver_Denominator_Sub_Sets** | Sets a restar en el denominador | Texto | **none** | none |
| **Driver_Numerator_Sum_Params** | Parámetros a sumar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | all |
| **Driver_Numerator_Sub_Params** | Parámetros a restar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Driver_Denominator_Sum_Params** | Parámetros a sumar en denominador | Texto | **none** | none |
| **Driver_Denominator_Sub_Params** | Parámetros a restar en denominador | Texto | **none** | none |
| Driver_Involved_Scenarios | Escenarios donde se aplica el driver | Lista con formato: espacio ; espacio | LTS ; BAU u otros definidos | LTS ; BAU |
| **Driver_Variable_Management** | Tipo de manejo | Texto | Direct: when put only one scenario in the column "Outcome_Involved_Scenarios", wrt_BAU_excess: with respect SCENARIO | wrt_BAU_excess |

**Nota**: Las columnas marcadas con **negrita** requieren revisión especial con el encargado del módulo.

#### Columnas de Outcome

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| **Outcome_ID** | Identificador único del outcome | Entero único | Secuencial comenzando en 1 | 1 |
| Outcome_Formula_Last | Especifica qué valor del período usar | Texto | AVG: average de un periodo, END: valor final de un periodo | AVG |
| Outcome_Threshold | Umbrales para el análisis PRIM | Lista con formato: espacio ; espacio | High: find predictors of values greater than 75th percentile ; Low: find predictors of values lower than 25th percentile ; Mid: find predictors of values greater than 50th percentile ; Zero: find predictors of values lower than 0 ; Dep: depende of others outcome threshold (High, Low), Intermediary | High ; Low |
| Outcome_Type | Clasificación del tipo de outcome | Primero se usa "Metric of interest" que va a ser la metrica de interes del valor de la columna "Outcome", y en las siguientes filas se usa "Intermediary" para las variables de la cual depende la metrica de interes. | Metric of interest, Intermediary | Metric of interest |
| **Outcome** | Nombre del outcome con sufijo que indica tipo de análisis.  | Debe coincidir exactamente y omitiendo el sufijo separado por el guión bajo con los nombres generados en el archivo "Units.xlsx", hoja "Units" y columna "driver_col" | N/A | Para el valor de "Units" "Emissions Waste_direct" el valor del "Outcome" sería: "Emissions Waste" |
| **Outcome_Actor** | Actor o entidad asociada | Texto | Country, Region, Sector | Country |
| Outcome_Source | Origen de los datos | Texto | OSeMOSYS-ModelName inputs/outputs, TEM output, Experiment data | OSeMOSYS-ModelName outputs |
| **Outcome_Formula_Numerator** | Fórmula del numerador | Texto | Revisar tabla "Formula Numerator" | sum_across |
| **Outcome_Formula_Denominator** | Fórmula del denominador | Texto | none, Den_GDP: denominador con valor GDP, tracost_at2019: costo de transporte al año 2019, totcost_at2019: costo total al año 2019 | none |
| Outcome_Involved_Sets | Tecnologías o combustibles involucrados según el valor de la columna "Outcome_Exact_Parameters_Involved" | Lista con formato: espacio ; espacio | Lista de tecnologías/combustibles | TRAUTDSL ; TRAUTGSL ; TRAUTELE |
| **Outcome_Supporting_Sets** | Sets de soporte adicionales, cuando el parámetro depende de otro set además de TECHNOLOGY O FUEL, lo usual es que si depende sea de EMISSION | Texto o lista con formato: espacio ; espacio | none o lista separada | CO2e |
| Outcome_Exact_Parameters_Involved | Parámetros específicos del modelo OSeMOSYS y MOMF. Revisar parámetros disponibles en los outputs del experimento RDM | Lista con formato: espacio ; espacio | Variables como Capex2025 ; VarOpex2025 ; FixedOpex2025 ; Externalities2025 | Capex2025 ; VarOpex2025 |
| Outcome_Tech_or_Fuel_or_Actor | Tipo de elemento modelado | Texto | Tech, Fuel | Tech |
| Outcome_Column_Management | Gestión de columnas resultantes | Texto | **none** | none |
| **Outcome_Numerator_Sum_Sets** | Sets a sumar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | none |
| **Outcome_Numerator_Sub_Sets** | Sets a restar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Outcome_Denominator_Sum_Sets** | Sets a sumar en denominador | Texto | **none** | none |
| **Outcome_Denominator_Sub_Sets** | Sets a restar en denominador | Texto | **none** | none |
| **Outcome_Numerator_Sum_Params** | Parámetros a sumar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | all |
| **Outcome_Numerator_Sub_Params** | Parámetros a restar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Outcome_Denominator_Sum_Params** | Parámetros a sumar en denominador | Texto | **none** | none |
| **Outcome_Denominator_Sub_Params** | Parámetros a restar en denominador | Texto | **none** | none |
| Outcome_Involved_Scenarios | Escenarios de aplicación | Lista con formato: espacio ; espacio | LTS ; BAU u otros | LTS ; BAU |
| Outcome_Variable_Management | Tipo de manejo | Texto | Direct: when put only one scenario in the column "Outcome_Involved_Scenarios", wrt_BAU: with respect BAU | wrt_BAU |

### Hoja: Outcomes

Contiene únicamente los outcomes únicos (sin repetición por driver). Esta hoja es un subconjunto de la información en Sequences.

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| **Outcome_ID** | Identificador único del outcome | Entero único | Secuencial comenzando en 1 | 1 |
| Outcome_Formula_Last | Especifica qué valor del período usar | Texto | AVG: average de un periodo, END: valor final de un periodo | AVG |
| Outcome_Threshold | Umbrales para el análisis PRIM | Lista con formato: espacio ; espacio | High: find predictors of values greater than 75th percentile ; Low: find predictors of values lower than 25th percentile ; Mid: find predictors of values greater than 50th percentile ; Zero: find predictors of values lower than 0 ; Dep: depende of others outcome threshold (High, Low), Intermediary | High ; Low |
| Outcome_Type | Clasificación del tipo de outcome | Primero se usa "Metric of interest" que va a ser la metrica de interes del valor de la columna "Outcome", y en las siguientes filas se usa "Intermediary" para las variables de la cual depende la metrica de interes. | Metric of interest, Intermediary | Metric of interest |
| **Outcome** | Nombre del driver con sufijo que indica tipo de análisis. Debe coincidir exactamente con los nombres generados en la hoja "Sequences" y en el caso de incertidumbres con los nombres de las incertidumbre del experimento RDM  | Texto descriptivo | N/A | Para el valor de "Units" "Emissions Waste_direct" el valor del "Outcome" sería: "Emissions Waste" |
| **Outcome_Actor** | Actor o entidad asociada | Texto | Country, Region, Sector | Country |
| Outcome_Source | Origen de los datos | Texto | OSeMOSYS-ModelName inputs/outputs, TEM output, Experiment data | OSeMOSYS-ModelName outputs |
| **Outcome_Formula_Numerator** | Fórmula del numerador | Texto | Revisar tabla "Formula Numerator" | sum_across |
| **Outcome_Formula_Denominator** | Fórmula del denominador | Texto | none, Den_GDP: denominador con valor GDP, tracost_at2019: costo de transporte al año 2019, totcost_at2019: costo total al año 2019 | none |
| Outcome_Involved_Sets | Tecnologías o combustibles involucrados según el valor de la columna "Outcome_Exact_Parameters_Involved" | Lista con formato: espacio ; espacio | Lista de tecnologías/combustibles | TRAUTDSL ; TRAUTGSL ; TRAUTELE |
| **Outcome_Supporting_Sets** | Sets de soporte adicionales, cuando el parámetro depende de otro set además de TECHNOLOGY O FUEL, lo usual es que si depende sea de EMISSION | Texto o lista con formato: espacio ; espacio | none o lista separada | CO2e |
| Outcome_Exact_Parameters_Involved | Parámetros específicos del modelo OSeMOSYS y MOMF. Revisar parámetros disponibles en los outputs del experimento RDM | Lista con formato: espacio ; espacio | Variables como Capex2025 ; VarOpex2025 ; FixedOpex2025 ; Externalities2025 | Capex2025 ; VarOpex2025 |
| Outcome_Tech_or_Fuel_or_Actor | Tipo de elemento modelado | Texto | Tech, Fuel | Tech |
| Outcome_Column_Management | Gestión de columnas resultantes | Texto | **none** | none |
| **Outcome_Numerator_Sum_Sets** | Sets a sumar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | none |
| **Outcome_Numerator_Sub_Sets** | Sets a restar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Outcome_Denominator_Sum_Sets** | Sets a sumar en denominador | Texto | **none** | none |
| **Outcome_Denominator_Sub_Sets** | Sets a restar en denominador | Texto | **none** | none |
| **Outcome_Numerator_Sum_Params** | Parámetros a sumar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "none"; pero si el valor es "Direct" el valor en esta columna debe de ser "all" | **all, none** | all |
| **Outcome_Numerator_Sub_Params** | Parámetros a restar en numerador | Sí el valor de la columna "Outcome_Variable_Management" es "wrt_BAU_excess", el valor en esta columna debe de ser "all"; pero si el valor es "Direct" el valor en esta columna debe de ser "none" | **all, none** | all |
| **Outcome_Denominator_Sum_Params** | Parámetros a sumar en denominador | Texto | **none** | none |
| **Outcome_Denominator_Sub_Params** | Parámetros a restar en denominador | Texto | **none** | none |
| Outcome_Involved_Scenarios | Escenarios de aplicación | Lista con formato: espacio ; espacio | LTS ; BAU u otros | LTS ; BAU |
| Outcome_Variable_Management | Tipo de manejo | Texto | Direct: when put only one scenario in the column "Outcome_Involved_Scenarios", wrt_BAU: with respect BAU | wrt_BAU |

---

## 2. Population.xlsx

**Objetivo**: Cargar población histórica/proyectada del país de estudio.

### Hoja: Sheet1

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| Year | Año del registro poblacional | Entero de cuatro dígitos (YYYY) | 2021-2050 | 2025 |
| Inhabitants | Cantidad total de habitantes para el año especificado | Entero absoluto sin separadores ni decimales | N/A | 2837077 |

**Notas**:
- Incluir todos los años del período de análisis
- Los valores deben ser consistentes con proyecciones oficiales

---

## 3. prim_files_creator_cntrl.xlsx

### Hoja: match_exp_ana

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| exps | Identificador único del experimento (sufijo), de los experimentos disponibles en la carpeta "t3a_experiments" | Para el experimento "Experiment_Integrated" el valor es "Integrated" | N/A | Integrated |
| exp_desc | Descripción detallada del experimento | Texto descriptivo | N/A | Appends all the elements from multiple models |
| include_exp | Indicador para incluir experimento en el análisis | Texto | YES/NO | YES |
| analyses | Identificador numérico del análisis | Entero | 1, 2, 3... | 1 |
| **analysis_desc** | Descripción breve del análisis | Texto breve | N/A | X and L |
| include_ana | Indicador para incluir análisis | Texto | YES/NO | YES |

### Hoja: periods

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| period_list | Etiqueta identificadora del período. Se usan los últimos dos dígitos del año (ej: 25 para 2025, 30 para 2030) | Texto: año_inicial-año_final | Definido por usuario | 25-30 |
| year_initial | Año de inicio del período | Entero (YYYY) | 2025-2030 | 2025 |
| year_final | Año de finalización del período | Entero (YYYY) | 2025-2030 | 2030 |

**Nota**: Incluir siempre un período "all" que abarque todo el horizonte temporal

### Hoja: dtype

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| File | Tipo de archivo fuente de datos | Texto | OSeMOSYS-ModelName inputs, OSeMOSYS-ModelName outputs, TEM output, TEM output fiscal, TEM region | TEM output |
| Column | Nombre exacto de la columna en el archivo fuente | Texto exacto como aparece en archivo | N/A | Technology |
| Type | Tipo de dato Python para la columna | Texto | str, int, float | str |

---

## 4. Units.xlsx

**Objetivo**: Documentar y completar las unidades asociadas a cada driver.

### Hoja: Units

| Nombre de columna | Explicación | Formato de llenado | Valores predefinidos | Ejemplo |
|------------------|-------------|-------------------|---------------------|---------|
| driver_col | Nombre del driver con sufijo que indica tipo de análisis. Debe coincidir exactamente con los nombres generados en prim_structure. | Texto: Driver_Outcome_Variable_Management donde "Driver" es el valor de la columna "Driver" en la hoja "Sequences" del archivo "prim_structre" y "Outcome_Variable_Management" es el valor de la columna "Outcome_Variable_Management" | Debe coincidir exactamente con nombres en prim_structure | Benefit EneTra_Direct |
| Units | Unidad de medida asociada al driver especificado | Texto: abreviatura de unidad | MUSD, PJ, GgCO2e, %, GWh, etc. | MUSD |

**Notas**: 
- Los valores en driver_col deben provenir del experimento RDM
- Usar nomenclatura estándar para unidades
- Los nombres en driver_col se generan automáticamente según Driver_Variable_Management en prim_structure.xlsx

---

## 5. PRIM_t3f2.yaml

**Objetivo**: Archivo de configuración con parámetros del modelo.

### Estructura principal:

```yaml
# Directorios
dir_exps: './t3a_experiments'
dir_sdisc: './t3b_sdiscovery'

# Archivos de control
Prim_files_crea_cntrl: 'prim_files_creator_cntrl.xlsx'

# Hojas de Excel
Periods: 'periods'
Mat_exp_ana: 'match_exp_ana'
dType: 'dtype'

# Variables y condiciones
BAU: 'BAU'
max_per_batch: 1

# Sets especiales y condiciones (según modelo específico)
```

---

# Recordatorios Finales

## Validaciones importantes:

1. **Consistencia de nombres**: Los nombres de drivers en Units.xlsx deben coincidir exactamente con los generados por prim_structure.xlsx (considerando los sufijos de Driver_Variable_Management)
2. **Formato de listas**: Siempre usar espacio + punto y coma + espacio para separar elementos (ejemplo: "valor1 ; valor2 ; valor3")
3. **Períodos completos**: Asegurar que Population.xlsx cubra todos los años definidos en periods
4. **Escenarios válidos**: Los escenarios en Driver_Involved_Scenarios deben existir en los experimentos
5. **Tipos de datos**: Verificar que los tipos en dtype correspondan con los datos reales
6. **Columnas críticas**: Revisar con el encargado del módulo todas las columnas marcadas en **negrita**

## Archivos generados:

- `prim_files_creator.pickle` - Estructura procesada
- `comp_pfd_*.pickle` - Datos compilados por análisis
- `sd_ana_*_exp_*.csv` - Resultados del análisis PRIM
- `t3f4_predominant_ranges_*.xlsx` - Rangos predominantes mapeados

## Orden de verificación:

1. Verificar que todos los archivos Excel estén completos
2. Confirmar formato correcto de listas (espacio ; espacio)
3. Ejecutar t3f1 y verificar que genere el pickle correctamente
4. Revisar logs de t3f2 para confirmar procesamiento de experimentos
5. Validar resultados de t3f3 en archivo CSV
6. Confirmar mapeo de rangos en t3f4