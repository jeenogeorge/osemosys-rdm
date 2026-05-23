# Guía de verificación — Fixes RDM 2026-05

> **Audiencia:** cualquier integrante del equipo que necesite revisar que los
> arreglos aplicados al pipeline RDM funcionan en su máquina.
>
> **Plan de origen:** [RDM_Remaining_Fixes_Plan.md](RDM_Remaining_Fixes_Plan.md)
>
> **Esfuerzo estimado para correr todas las verificaciones:** ~25 min si el
> experimento RDM ya fue ejecutado; ~45 min si hay que correrlo de cero.

---

## Resumen de cambios

Se aplicaron seis correcciones al pipeline RDM. Las primeras cuatro son
limpieza del `Uncertainty_Table`/`Setup`. Las dos últimas son funcionales:

| ID | Qué cambió | Riesgo si está mal |
|----|------------|---------------------|
| **4A** | Filas `DEP` añadidas para `LVSGOACU` y `LVSSHPCU` (eran `YES_PROP` huérfanas) | Cabras/ovejas CU no se mueven correlacionadas con CF |
| **4B** | `Setup.Region`: `BWA` → `RE1` (alineado con `set REGION` de `Scenario1.txt`) | CSV de salida queda mal etiquetado |
| **4C** | Limpieza: `Involved_Scenarios` de `"Scenario1 ; Scenario2"` → `"Scenario1"` | Ruido en logs |
| **4D** | Descripciones X_Num 2-4 corregidas (other/goat/sheep, antes todas decían cattle) | Sólo cosmético |
| **P2** | Añadido par `YES_PROP`/`DEP` para `CapitalCost`/`FixedCost` cubriendo 6 técnicas renovables agrupadas en una sola fila multivalor. Requirió **relajar una validación** en `0_experiment_manager.py` que prohibía multi-valor. | Ratio FixedCost/CapitalCost no preservado por técnica |
| **P3b** | Infraestructura de `fix_renewable_share_consistency` añadida + columnas `RE_Param`/`NonRE_Param` en `Setup` (vacías, inactivas) | N/A — desactivada hasta que se populen las columnas |
| **VAL** | Segunda relajación de la validación de longitudes: ahora permite `len(primary) != len(dependent)` con warning. Cubre el caso UDC de Jeeno (RE/non-RE shares con listas asimétricas, p.ej. 8 RE vs 13 non-RE). Seguro cuando los baselines son uniformes por lado. | Si los baselines del primary NO son uniformes, los dep con índice >= len(pri) heredan del último primary, lo que puede no ser lo esperado. |

**Refactores 4E.1/4E.2/4E.3 NO se aplicaron** (por recomendación del plan: cada
uno es un PR/sprint separado).

---

## Pre-requisitos

```powershell
# Desde la raíz del repo
python -c "import openpyxl, pandas; print('OK deps')"
```

Si falla, instalar con `pip install openpyxl pandas`.

Para verificación funcional completa también necesitas un solver instalado
(CPLEX por defecto en `Setup.Solver`).

---

## Verificación rápida — todas las correcciones a la vez

```powershell
python verify_rdm_fixes.py
python verify_problem2_ratios.py
python tests/test_renewable_share_fixer.py
```

Si los tres salen con código 0 y mensaje final positivo → todo OK. Para entender
**qué** verifica cada uno o para diagnosticar fallos, ver las secciones de abajo.

---

## Problema 4A — Filas DEP para LVSGOACU y LVSSHPCU

**¿Qué se rompía antes?** Las filas 12 (`LVSGOACF`) y 13 (`LVSSHPCF`) declaraban
`Dependency=YES_PROP` pero no tenían fila `DEP` siguiente. Resultado: las
versiones CU (no climáticas) de cabra y oveja **no se perturbaban en
correlación** con su contraparte CF, rompiendo la simetría que sí existe para
las filas 8-9 (LVSOTHCF/CU) y 10-11 (LVSCTLCF/CU).

**¿Qué debe pasar ahora?** Para cada futuro perturbado, el ratio
`CU_perturbado/CF_perturbado` debe igualar `CU_baseline/CF_baseline` por
(Region, AGRWAT1, Year), porque `YES_PROP` aplica
`new_dep = baseline_dep * (new_pri / baseline_pri)`.

### Verificación

**Paso 1 — estructura del Excel:**

```powershell
python verify_rdm_fixes.py
```

Buscar la línea: `OK sin YES_PROP huérfanos`. Si dice `YES_PROP huérfanos: [...]`
→ revisar fila citada.

**Paso 2 — logs del experimento:**

En el stdout de `RUN_RDM.py`, buscar:
```
Dependency (YES_PROP): Row 13 dependent on Row 12 | Scenario Scenario1 Future 1
Dependency (YES_PROP): Row 15 dependent on Row 14 | Scenario Scenario1 Future 1
```

Si no aparece para `Row 13` y `Row 15`, la dependencia no se está procesando.

**Paso 3 — comparación numérica (opcional, requiere outputs):**

Abrir `src/workflow/1_Experiment/Experimental_Platform/Futures/Scenario1/Scenario1_1/Scenario1_1.txt`
y `src/workflow/1_Experiment/Executables/Scenario1_0/Scenario1_0.txt`. Localizar
las filas `LVSGOACF` y `LVSGOACU` dentro del bloque `param InputActivityRatio`.
Calcular para el mismo (Region, AGRWAT1, Year):

```
ratio_CF = perturbed_LVSGOACF / baseline_LVSGOACF
ratio_CU = perturbed_LVSGOACU / baseline_LVSGOACU
```

`ratio_CF` debe ser ≈ `ratio_CU` (mismo factor de perturbación).

---

## Problema 4B — Region BWA → RE1

**¿Qué se rompía antes?** `Setup.Region = 'BWA'` pero `Scenario1.txt` usa
`set REGION := RE1`. La variable solo se usa para nombrar el CSV de salida
(`OSEMOSYS_BWA_Energy_Input.csv`), no afecta el modelo en sí — pero los
archivos quedaban mal etiquetados.

### Verificación

**Paso 1 — alineación estática:**

```powershell
python verify_rdm_fixes.py
```

Buscar: `OK Setup.Region='RE1' alineado con Scenario1.txt`.

**Paso 2 — nombre del CSV de salida:**

```powershell
Get-ChildItem -Recurse -Filter "OSEMOSYS_*_Energy_Input.csv" | Select-Object Name
```

Debe aparecer `OSEMOSYS_RE1_Energy_Input.csv`. **No debe** existir ningún
`OSEMOSYS_BWA_*`. Si lo hay, es de una corrida vieja — bórralo manualmente.

---

## Problema 4C — Limpieza de referencias a Scenario2

**¿Qué se rompía antes?** Las 13 filas del `Uncertainty_Table` decían
`"Scenario1 ; Scenario2"` pero `src/workflow/0_Scenarios/` solo contiene
`Scenario1.txt`. No causaba error pero generaba ruido conceptual.

### Verificación

```powershell
python verify_rdm_fixes.py
```

Buscar: `OK sin referencias a Scenario2 en Involved_Scenarios`.

Si vuelves a necesitar `Scenario2`, ver `RDM_Remaining_Fixes_Plan.md`
sección **4C-Opción 2**.

---

## Problema 4D — Descripciones filas 2-4

**¿Qué se rompía antes?** Las cuatro primeras filas decían
`"Demand Growth - livestock cattle"` aunque aplicaban a LVSCTL (cattle),
LVSOTH (other), LVSGOA (goat), LVSSHP (sheep). Confuso al revisar resultados.

### Verificación

```powershell
python verify_rdm_fixes.py
```

Buscar: `OK descripciones filas 1-4 corregidas`. Si falla, imprime qué fila
está mal y cuál era el esperado.

---

## Problema 2 — CapitalCost ↔ FixedCost agrupado **[el más importante]**

**¿Qué se rompía antes?** No existía perturbación correlacionada para los
costos de las técnicas renovables. Re-añadirla "fila por técnica" hubiera
necesitado 12 filas (6 YES_PROP + 6 DEP). El plan propuso un patrón mejor:
**una sola fila multivalor** YES_PROP + una DEP, cubriendo las 6 técnicas
agrupadas mediante alineamiento índice-por-índice.

Al implementarlo, descubrimos que `0_experiment_manager.py` tenía una
**validación demasiado estricta** (`When using dependency, each row must have
exactly 1 value...`) que bloqueaba el uso multi-valor, **aunque el código de
iteración sí lo soportaba**. Relajamos la validación a "primary y dependent
deben tener igual longitud" (que es el requisito real).

**Invariante a verificar:** Para cada técnica en
`{PWRSOL001, PWRWND001, PWRBIO001, PWRGEO, PWRCSP001, PWRCSP002}`,
cada futuro perturbado y cada año, debe cumplirse:

```
FixedCost_perturbed[tech, y]     FixedCost_baseline[tech, y]
─────────────────────────────  =  ────────────────────────────
CapitalCost_perturbed[tech, y]   CapitalCost_baseline[tech, y]
```

### Verificación

**Paso 1 — Excel:**

```powershell
python verify_rdm_fixes.py
```

Buscar:
```
OK Problema 2: X_Num 16↔17 alineados (PWRSOL001 ; PWRWND001 ; ...)
```

**Paso 2 — funcional (requiere `Results/` poblado por una corrida reciente):**

```powershell
python verify_problem2_ratios.py
```

Salida esperada:
```
OK Scenario1_1: 216 celdas comparadas, max ratio diff = X.XXe-14
OK Scenario1_2: 216 celdas comparadas, max ratio diff = X.XXe-14
...
RESULTADO: TODOS LOS RATIOS PRESERVADOS (Problema 2 funcional)
```

`216 celdas` = 6 técnicas × 36 años. La diferencia de ratio debe ser del orden
de `1e-13` (precisión floating-point de doble precisión). Si es mayor a
`1e-6`, hay algo mal.

**Paso 3 — sanity check de perturbación efectiva:**

Si la salida muestra `⚠️ NO HUBO PERTURBACIÓN`, el valor perturbado es
idéntico al baseline. Puede ser legítimo (LHS sampleó cerca de 1.0) si solo
ocurre en uno o dos futuros, pero si todos los futuros lo muestran → revisar
que las filas X_Num 16-17 estén siendo procesadas (buscar en stdout
`Dependency (YES_PROP): Row 17 dependent on Row 16`).

---

## Problema 3b — Fixer de renewable share (infraestructura)

**¿Qué se rompía antes?** Cuando se quiere que `RE_share + nonRE_share == 1`
después de perturbación, los UDC del plan original no existían en el modelo
(`2POWRENMIN`/`2POWNONRENMAX` no están en `Scenario1.txt`). Sin embargo,
queríamos dejar la maquinaria lista para cuando se defina un par real.

**Solución:** función `fix_renewable_share_consistency` añadida a
`0_experiment_manager.py`, wire-eada después del fix de emisiones,
condicional a `Setup.RE_Param` y `Setup.NonRE_Param`. Mientras esas dos
celdas estén **vacías**, el fixer **no se invoca** — comportamiento idéntico
al pre-fix.

### Verificación

**Paso 1 — Setup tiene las columnas y están vacías:**

```python
import openpyxl
wb = openpyxl.load_workbook('src/Interface_RDM.xlsx', data_only=True)
ws = wb['Setup']
headers = [c.value for c in ws[1]]
assert 'RE_Param' in headers, "Falta columna RE_Param"
assert 'NonRE_Param' in headers, "Falta columna NonRE_Param"
re_col = headers.index('RE_Param') + 1
nonre_col = headers.index('NonRE_Param') + 1
print(f"RE_Param={ws.cell(2, re_col).value!r}, NonRE_Param={ws.cell(2, nonre_col).value!r}")
# Esperado: RE_Param=None, NonRE_Param=None (inactivo por defecto)
```

**Paso 2 — unit tests del fixer:**

```powershell
python tests/test_renewable_share_fixer.py
```

Salida esperada:
```
  test_basic_correction: OK
  test_no_correction_needed: OK
  test_partial_match: OK
  test_missing_params: OK
  test_multiple_regions: OK

TODOS LOS TESTS PASAN (fixer 3b funcional)
```

Los tests son sintéticos — construyen un `inherited_scenarios` mínimo, llaman
a la función y verifican que tras el fix `RE + nonRE == 1.0` exactamente.

**Paso 3 — confirmar inactividad en el experimento real:**

En el stdout de la última corrida de `RUN_RDM.py`, **NO** debe aparecer la
línea `Renewable Share Fix: ...`. Su ausencia confirma que el fixer está
inactivo (correcto, porque las columnas están vacías).

### Cuándo y cómo activar el fixer

Cuando definas qué par de parámetros del modelo deben sumar 1.0:

1. Abrir `src/Interface_RDM.xlsx`, hoja `Setup`.
2. Poner el nombre del parámetro RE (fuente de verdad) en columna `RE_Param`.
3. Poner el nombre del parámetro non-RE (el que se reescribe) en `NonRE_Param`.
4. Correr `RUN_RDM.py`. Debe aparecer en stdout:
   ```
   Renewable Share Fix: Applied N correction(s) across all futures (REparam -> NonREparam).
   ```
5. Inspeccionar
   `src/workflow/1_Experiment/Logs/Renewable_Share_Corrections/renewable_share_corrections.log`
   para auditar las correcciones.

---

## Verificación end-to-end: correr el experimento completo

Si quieres rehacer todo desde cero:

```powershell
cd src
python RUN_RDM.py
```

Tiempo esperado: ~20 min con `Number_of_Runs=8` y CPLEX en 16 threads.
Output esperado al final:
```
5 futures processed: 5 optimal, 0 infeasible
Processing completed successfully.
```

Si falla, mirar el stdout — los errores recientes de validación dependencias
imprimen un mensaje claro con `Row N (primary/dependent) ...`.

---

## Inventario de scripts añadidos

| Archivo | Propósito | Idempotente |
|---------|-----------|-------------|
| `apply_rdm_fixes.py` | Aplica 4A/4B/4C/4D + Problema 2 al Excel | ✓ |
| `add_setup_columns.py` | Añade columnas `RE_Param`/`NonRE_Param` a Setup | ✓ |
| `verify_rdm_fixes.py` | Verificación estática del Excel | ✓ |
| `verify_problem2_ratios.py` | Verificación funcional ratios CapitalCost/FixedCost | ✓ |
| `tests/test_renewable_share_fixer.py` | Unit tests del fixer 3b | ✓ |

Los scripts en la raíz (`apply_*`, `add_*`, `verify_*`) son herramientas
operativas. Pueden quedar versionados o borrarse según preferencia del equipo;
los cambios reales viven en el Excel y en `0_experiment_manager.py`.

---

## Archivos modificados (resumen para revisión de PR)

- `src/Interface_RDM.xlsx` — hoja `Uncertainty_Table` (17 filas, antes 13) y
  hoja `Setup` (17 columnas, antes 15; Region=`RE1`).
- `src/workflow/1_Experiment/0_experiment_manager.py`:
  - Función nueva `fix_renewable_share_consistency` (~línea 484).
  - Llamada wire-eada después de `fix_emission_limit_consistency` (~línea 2611).
  - Validación de dependencia multi-valor relajada (~líneas 1889-1899).

Backup del Excel original: `src/Interface_RDM.xlsx.bak`.

---

## Apéndice — Sobre la validación de longitudes en filas con dependencia

La validación en `0_experiment_manager.py:1889-1903` evolucionó en dos pasos durante esta sesión:

**Estado original (rechazado):**
```python
if len(pri_first_sets) > 1 or len(dep_first_sets) > 1:
    sys.exit(1)  # "must have exactly 1 value"
```
Bloqueaba cualquier fila con dependencia que tuviera multi-valor. Era falsamente
estricto: el código de iteración subyacente sí maneja multi-valor.

**Primer relajamiento (intermedio):**
```python
if len(pri_first_sets) != len(dep_first_sets):
    sys.exit(1)
```
Permitía multi-valor pero requería simetría. Cubre P2 (6=6 técnicas renovables)
pero bloquea el caso UDC de Jeeno (8 RE vs 13 non-RE).

**Estado actual (definitivo):**
```python
if len(pri_first_sets) == 0 or len(dep_first_sets) == 0:
    sys.exit(1)
elif len(pri_first_sets) != len(dep_first_sets):
    print("WARNING: ...lengths differ, dep[i>=len(pri)] paired with last pri...")
```

Permite cualquier configuración con al menos 1 valor en cada lado. Cuando las
longitudes difieren, el código de iteración usa
`pri_first_sets[min(idx, len(pri)-1)]`, es decir, los dependientes con índice
mayor o igual a `len(pri)` se parean con el último primary.

### Cuándo es seguro usar longitudes distintas

**Seguro** — todos los pri techs comparten el mismo baseline y se mueven al
mismo new value. Caso típico: UDC shares (RE/non-RE summing to constant).
Ejemplo: baselines RE = -0.3 para los 8 RE techs, LHS samplea -0.5, todos los
8 RE pasan a -0.5, delta uniforme = -0.2. YES_ADD propaga -0.2 a los 13 dep
correctamente.

**No seguro** — pri techs con baselines distintos. Los últimos dep heredarían
el delta del último pri específicamente, lo que típicamente no es lo esperado.
En ese caso usar igualdad estricta o el fixer 3b vía `Setup.RE_Param/NonRE_Param`.

### Cómo verificar tras correr un experimento

Buscar en el stdout del experimento las líneas tipo:
```
WARNING: Dependency rows N (primary) and M (dependent) have different lengths...
```

Si aparece y NO esperabas longitudes distintas → revisa la fila citada.
Si aparece y es intencional → confirma que los baselines del primary son
uniformes inspeccionando el bloque del parámetro en `Scenario1.txt`.

