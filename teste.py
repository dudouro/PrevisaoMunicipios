import geopandas as gpd

# 1. Carregar o shapefile dos municípios de Minas Gerais
shapefile_path = "pages/MG_Municipios_2023.shp"
municipios = gpd.read_file(shapefile_path)

# 2. Verificar as colunas disponíveis
print("Colunas disponíveis no shapefile:")
print(municipios.columns)

# 3. Manter apenas as colunas necessárias (código IBGE e nome do município)
# Substitua 'CD_MUN' e 'NM_MUN' pelos nomes corretos das colunas no seu shapefile
municipios = municipios[['CD_MUN', 'NM_MUN', 'geometry']]

# 4. Renomear colunas para facilitar o uso
municipios.rename(columns={
    'CD_MUN': 'Codigo_IBGE',
    'NM_MUN': 'Nome_Municipio'
}, inplace=True)

# 5. Salvar os municípios em um arquivo GeoJSON
output_municipios_path = "pages/MG_Municipios.geojson"
municipios.to_file(output_municipios_path, driver='GeoJSON')

print(f"Arquivo GeoJSON dos municípios salvo em: {output_municipios_path}")