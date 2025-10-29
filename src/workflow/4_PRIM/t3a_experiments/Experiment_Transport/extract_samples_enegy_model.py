import pandas as pd


### PARTE 1

# 1. Leer el archivo CSV
try:
    df = pd.read_csv('OSMOSYS_JAM_Output.csv')
except FileNotFoundError:
    print("El archivo OSMOSYS_JAM_Output.csv no se encontró.")
    exit()

# 2. Definir la lista de tecnologías deseadas
tecnologias_deseadas = ['T4DSL_HEA', 'T4DSL_LIG', 
                        'T4DSL_PRI', 'T4DSL_PUB', 'T4ELE_PRI', 'T4ELE_PUB', 'T4FOI_HEA', 
                        'T4GSL_LIG', 'T4GSL_PRI', 'T4GSL_PUB']

# 3. Filtrar el DataFrame por las tecnologías deseadas
df_filtrado = df[df['Technology'].isin(tecnologias_deseadas)]

# 4. Eliminar filas con valores NaN en la columna 'UseByTechnology'
df_filtrado = df_filtrado.dropna(subset=['UseByTechnology'])  # Elimina filas con NaN en 'UseByTechnology'

# 5. Seleccionar solo las columnas deseadas
columnas_deseadas = ['Strategy', 'Future.ID', 'Technology', 'Year', 'UseByTechnology']
df_simplificado = df_filtrado[columnas_deseadas]

# 6. Guardar el DataFrame simplificado en un nuevo archivo CSV
df_simplificado.to_csv('UseByTechnologyEnergySamples.csv', index=False)

print("DataFrame simplificado guardado en UseByTechnologyEnergySamples.csv (sin valores NaN en 'UseByTechnology').")


### PARTE 2

# 1. Leer el archivo CSV
try:
    df = pd.read_csv('UseByTechnologyEnergySamples.csv')
except FileNotFoundError:
    print("El archivo UseByTechnologyEnergySamples.csv no se encontró.")
    exit()

# 2. Diccionario de tecnologías
diccionario_tecnologias = {
    'E5TRODSL': ['T4DSL_HEA', 'T4DSL_LIG', 'T4DSL_PRI', 'T4DSL_PUB'],
    'E5TROELE': ['T4ELE_PRI', 'T4ELE_PUB'],
    'E5TROFOI': ['T4FOI_HEA'],
    'E5TROGSL': ['T4GSL_LIG', 'T4GSL_PRI', 'T4GSL_PUB']
}

# 3. Función para asignar el StrategyGroup
def asignar_strategy_group(tecnologia):
    for strategy_group, tecnologias in diccionario_tecnologias.items():
        if tecnologia in tecnologias:
            return strategy_group
    return None

# 4. Aplicar la función a la columna 'Technology'
df['StrategyGroup'] = df['Technology'].apply(asignar_strategy_group)

# 5. Agrupar y sumar 'UseByTechnology' por 'Strategy', 'Future.ID', 'Year' y 'StrategyGroup'
df_agrupado = df.groupby(['Strategy', 'Future.ID', 'Year', 'StrategyGroup'])['UseByTechnology'].sum().reset_index()

# 6. Renombrar la columna 'StrategyGroup' a 'Fuel' y 'UseByTechnology' a 'SpecifiedAnnualDemand'
df_agrupado.rename(columns={'StrategyGroup': 'Fuel', 'UseByTechnology': 'SpecifiedAnnualDemand'}, inplace=True)

# 7. Años para agregar filas adicionales
anios_agregar = [2021, 2022, 2023, 2024, 2025]

# 8. Combinaciones únicas de Strategy y Future.ID (distinto de 0)
combinaciones_unicas = df_agrupado[df_agrupado['Future.ID'] != 0][['Strategy', 'Future.ID']].drop_duplicates()

# 9. Crear filas adicionales con SpecifiedAnnualDemand = 0
filas_adicionales = []
for index, row in combinaciones_unicas.iterrows():
    strategy = row['Strategy']
    future_id = row['Future.ID']
    for anio in anios_agregar:
        if anio not in df_agrupado[(df_agrupado['Strategy'] == strategy) & (df_agrupado['Future.ID'] == future_id) & (df_agrupado['Fuel'] == 'E5TROELE')]['Year'].values:
            filas_adicionales.append({
                'Strategy': strategy,
                'Future.ID': future_id,
                'Year': anio,
                'Fuel': 'E5TROELE',
                'SpecifiedAnnualDemand': 0
            })

# 10. Agregar las filas adicionales al DataFrame
df_filas_adicionales = pd.DataFrame(filas_adicionales)
df_resultado = pd.concat([df_agrupado, df_filas_adicionales], ignore_index=True)

# 11. Seleccionar las columnas deseadas
columnas_deseadas = ['Strategy', 'Future.ID', 'Year', 'Fuel', 'SpecifiedAnnualDemand']
df_resultado = df_resultado[columnas_deseadas]

# 12. Guardar el DataFrame resultante en un nuevo archivo CSV
df_resultado.to_csv('SpecifiedAnnualDemandTransport.csv', index=False)

print("DataFrame resultante guardado en SpecifiedAnnualDemandTransport.csv")



### 


# # 1. Leer el archivo CSV
# try:
#     df = pd.read_csv('OSMOSYS_JAM_Input.csv')
# except FileNotFoundError:
#     print("El archivo OSMOSYS_JAM_Input.csv no se encontró.")
#     exit()

# # 2. Lista de tecnologías deseadas
# tecnologias_deseadas = ['DIST_DSL', 'DIST_GSL', 'DIST_LPG', 'DIST_FOI', 'DIST_KER']

# # 3. Filtrar el DataFrame por las tecnologías deseadas
# df_filtrado = df[df['Technology'].isin(tecnologias_deseadas)]

# # 4. Seleccionar las columnas deseadas
# columnas_deseadas = ['Year', 'Future.ID', 'Technology', 'Fuel', 'Strategy', 'VariableCost']
# df_resultado = df_filtrado[columnas_deseadas]

# # 5. Eliminar filas con VariableCost igual a NaN
# df_resultado = df_resultado.dropna(subset=['VariableCost'])

# # 6. Guardar el DataFrame resultante en un nuevo archivo CSV
# df_resultado.to_csv('VariableCostSamples.csv', index=False)

# print("DataFrame resultante guardado en VariableCostSamples.csv")






