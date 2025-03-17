import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Configuración de la aplicación
st.title("Análisis de Pagos de Garantía")
st.write("Carga los datos desde las fuentes y consulta valores FOB específicos.")

# URLs de los archivos CSV
URL_BOL01 = 'https://storage.googleapis.com/bk_tcs/invoices_bol01.csv'
URL_BOL02 = 'https://storage.googleapis.com/bk_tcs/invoices_bol02.csv'

@st.cache_data
def load_data():
    invoices_bol01 = pd.read_csv(URL_BOL01, sep=";", encoding="latin1", encoding_errors='ignore', dtype={'Ult_Ingreso': str})
    invoices_bol02 = pd.read_csv(URL_BOL02, sep=";", encoding="latin1", dtype={'SHIP DATE ': str})
    
    invoices_bol01.rename(columns={'ï»¿Ult_Ingreso': 'Fecha'}, inplace=True)
    invoices_bol01['Fecha'] = pd.to_datetime(invoices_bol01['Fecha'])
    
    def convert_date(date_str):
        try:
            return pd.to_datetime(date_str, format='%Y-%m-%d %H:%M:%S')
        except ValueError:
            return pd.to_datetime(date_str, format='%Y-%m-%d')
    
    invoices_bol02['SHIP DATE '] = invoices_bol02['SHIP DATE '].apply(convert_date)
    return invoices_bol01, invoices_bol02

invoices_bol01, invoices_bol02 = load_data()

# SECCION DE CONSULTA

fuente_datos = st.selectbox("Seleccione la fuente de datos", ["BOL01", "BOL02"])
np_filtro = st.text_input("Ingrese el NP a filtrar")

if np_filtro:
    if fuente_datos == "BOL02":
        idx = invoices_bol02.groupby('NP')['SHIP DATE '].idxmax()
        invoices_bol02_Query = invoices_bol02.loc[idx]
        resultado = invoices_bol02_Query[invoices_bol02_Query['NP'] == np_filtro]
    else:
        idx = invoices_bol01.groupby('NP')['Fecha'].idxmax()
        invoices_bol01_Query = invoices_bol01.loc[idx]
        resultado = invoices_bol01_Query[invoices_bol01_Query['NP'] == np_filtro]
    
    st.write("### Resultados de la consulta:")
    st.dataframe(resultado)

# SECCION REPORTE TCS
uploaded_file = st.file_uploader("Sube el archivo Excel", type=["xlsm", "xlsx"])

if uploaded_file is not None:
    # Cargar datos
    df = pd.read_excel(uploaded_file, sheet_name='MonthlyERP', header=1)
    df = df.iloc[6:, 3:]
    df = df[['Dealer Code','Claim No.', 'VIN', 'Model Basic', 'Date Sold', 'Date Repaired', 'Mileage', 'PFP', 'Operation Code (A)', 'Operation Hour (A)', 'Operation Code (B)',
        'Operation Hour (B)', 'Operation Code (C)', 'Operation Hour (C)', 'Part  No. (A)', 'Part Quantity (A)', 'Parts Price\nTotal (A)', 'Part  No. (B)', 'Part Quantity (B)', 'Parts Price Total (B)',
        'Part  No. (C)', 'Part Quantity (C)', 'Parts Price Total (C)', 'Part  No. (D)', 'Part Quantity (D)', 'Parts Price Total (D)', 'Part  No. (E)', 'Part Quantity (E)', 'Parts Price Total (E)',
        'Sublet Amount(A)', 'Sublet Amount (B)', 'Sublet Amount (C)', 'Sublet Amount (D)', 'Evaluation Results*', 'Claim Amount Parts', 'Claim Amount Labor',
        'Claim Amount Sublet', 'Claim Amount Total', 'Parts Remittance Amount', 'Labor Remittance Amount', 'Sublet Remittance Amount', 'Total Remittance Amount']]
    df['Dealer Code'] = df['Dealer Code'].astype(str)
    df['Dealer Code'] = df['Dealer Code'].str.strip()
    df['Dealer'] = df['Dealer Code'].apply(lambda x: 'SCZ' if x.endswith('N') else 'Cbba' if x.endswith('C') else 'LP' if x.endswith('L') else 'Otros')
    df['Date Repaired'] = pd.to_datetime(df['Date Repaired'], format='%Y%m%d')

    quantity_cols = ['Part Quantity (A)', 'Part Quantity (B)', 'Part Quantity (C)', 'Part Quantity (D)', 'Part Quantity (E)']
    for col in quantity_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # GLOBAL SUMMARY

    Umbral = df['Date Repaired'].max()

    invoices_bol02_filtered = invoices_bol02[invoices_bol02['SHIP DATE ']<=Umbral]
    invoices_bol01_filtered = invoices_bol01[invoices_bol01['Fecha']<=Umbral]

    idx = invoices_bol02_filtered.groupby('NP')['SHIP DATE '].idxmax()
    invoices_bol02_filtered = invoices_bol02_filtered.loc[idx]

    idx = invoices_bol01_filtered.groupby('NP')['Fecha'].idxmax()
    invoices_bol01_filtered = invoices_bol01_filtered.loc[idx]

    Summary = df.groupby(['Evaluation Results*']).agg({'Claim Amount Parts': 'sum', 'Claim Amount Labor': 'sum',
                                                    'Claim Amount Sublet': 'sum', 'Claim Amount Total': 'sum'}).reset_index()

    Summary[['Claim Amount Parts', 'Claim Amount Labor', 'Claim Amount Sublet', 'Claim Amount Total']] = Summary[['Claim Amount Parts', 'Claim Amount Labor', 
                                                                                                                   'Claim Amount Sublet', 'Claim Amount Total']].apply(lambda x: x.map(lambda y: f"{y:,.2f}"))
    st.write("### Resumen del análisis Reclamos Realizados")
    st.dataframe(Summary)

    Summary2 = df.groupby(['Evaluation Results*']).agg({'Parts Remittance Amount': 'sum', 
                                                     'Labor Remittance Amount': 'sum', 
                                                     'Sublet Remittance Amount': 'sum', 
                                                     'Total Remittance Amount': 'sum'}).reset_index()

    Summary2[['Parts Remittance Amount', 'Labor Remittance Amount', 
            'Sublet Remittance Amount', 'Total Remittance Amount']] = Summary2[['Parts Remittance Amount', 'Labor Remittance Amount', 
                                                                                'Sublet Remittance Amount', 'Total Remittance Amount']].apply(lambda x: x.map(lambda y: f"{y:,.2f}"))

    st.write("### Resumen Reclamos Aceptados")
    st.dataframe(Summary2)

    # Filtrar por estado de evaluación
    st.write("### Datos por tipo de evaluación")
    status_options = {'1': 'Return', '2': 'Reject', '3': 'Pending', '4': 'Approve'}
    selected_status = st.selectbox("Selecciona el estado", list(status_options.keys()), format_func=lambda x: status_options[x])
    filtered_df = df[df['Evaluation Results*'] == selected_status]
    st.dataframe(filtered_df)
    
    # Análisis de diferencias
    df['Parts Dif'] = df['Parts Remittance Amount'] - df['Claim Amount Parts']
    df['Labor Dif'] = df['Labor Remittance Amount'] - df['Claim Amount Labor']
    df['Sublet Dif'] = df['Sublet Remittance Amount'] - df['Claim Amount Sublet']
    df['Total Dif'] = df['Total Remittance Amount'] - df['Claim Amount Total']
    
    agg_result = df[df['Evaluation Results*'] == '4'].agg({'Parts Dif': 'sum', 'Labor Dif': 'sum', 'Sublet Dif': 'sum', 'Total Dif': 'sum'})
    formatted_agg_df = pd.DataFrame(agg_result).transpose().map(lambda x: f"{x:,.2f}")
    
    st.write("### Análisis de diferencias en Aprobados")
    st.dataframe(formatted_agg_df)
    
    # REVISION PARTES PAGADAS vs FOB

    st.write("### Revisión Partes Pagadas vs FOB")

    Revision = df[df['Evaluation Results*']== '4']

    # Definimos las columnas principales
    main_cols = ['Dealer', 'Claim No.', 'VIN']

    # Definimos las columnas que contienen las partes
    part_cols = ['Part  No.', 'Part Quantity']

    # Creamos un nuevo DataFrame vacío para almacenar los resultados
    Dif_Parts = pd.DataFrame(columns=main_cols + part_cols)

    # Iteramos a través de las columnas de las partes (A a E)
    for suffix in ['(A)', '(B)', '(C)', '(D)', '(E)']:
        temp = Revision[main_cols + [col + ' ' + suffix for col in part_cols]].copy()
        temp.columns = main_cols + part_cols
        Dif_Parts = pd.concat([Dif_Parts, temp], ignore_index=True)

    # Filtramos las filas vacías
    Dif_Parts = Dif_Parts.dropna(subset=['Part  No.'])
    Dif_Parts = Dif_Parts[Dif_Parts['Part Quantity']>0]
    Dif_Parts.rename(columns={'Part  No.': 'NP'}, inplace = True)
    Dif_Parts['NP'] = Dif_Parts['NP'].str.strip()

    # Merge inicial con invoices_bol02
    Dif_Parts_SCZ = Dif_Parts[Dif_Parts['Dealer']=='SCZ']
    Dif_Parts_SCZ = pd.merge(Dif_Parts_SCZ, invoices_bol02_filtered[['NP', 'FOB']], how='left', on='NP')
    # Renombrar la columna FOB resultante para evitar conflictos
    Dif_Parts_SCZ.rename(columns={'FOB': 'FOB_02'}, inplace=True)
    # Merge con invoices_bol01
    Dif_Parts_SCZ = pd.merge(Dif_Parts_SCZ, invoices_bol01_filtered[['NP', 'FOB']], how='left', on='NP')
    # Rellenar los valores de FOB_02 con FOB
    Dif_Parts_SCZ['FOB'] = Dif_Parts_SCZ['FOB_02'].combine_first(Dif_Parts_SCZ['FOB'])
    # Eliminar la columna FOB_02
    Dif_Parts_SCZ = Dif_Parts_SCZ.drop(columns=['FOB_02'])
    # Imputando FOB
    Dif_Parts_SCZ['FOB'] = Dif_Parts_SCZ['FOB'].fillna(0)
    # Total a Pagar
    Dif_Parts_SCZ['Parts Claim Amount'] = Dif_Parts_SCZ['Part Quantity']*Dif_Parts_SCZ['FOB']

    # Merge inicial con invoices_bol01
    Dif_Parts_TM = Dif_Parts[Dif_Parts['Dealer']!='SCZ']
    Dif_Parts_TM = pd.merge(Dif_Parts_TM, invoices_bol01_filtered[['NP', 'FOB']], how='left', on='NP')
    # Renombrar la columna FOB resultante para evitar conflictos
    Dif_Parts_TM.rename(columns={'FOB': 'FOB_02'}, inplace=True)
    # Merge con invoices_bol01
    Dif_Parts_TM = pd.merge(Dif_Parts_TM, invoices_bol02_filtered[['NP', 'FOB']], how='left', on='NP')
    # Rellenar los valores de FOB_02 con FOB
    Dif_Parts_TM['FOB'] = Dif_Parts_TM['FOB_02'].combine_first(Dif_Parts_TM['FOB'])
    # Eliminar la columna FOB_02
    Dif_Parts_TM = Dif_Parts_TM.drop(columns=['FOB_02'])
    # Imputando FOB
    Dif_Parts_TM['FOB'] = Dif_Parts_TM['FOB'].fillna(0)
    # Total a Pagar
    Dif_Parts_TM['Parts Claim Amount'] = Dif_Parts_TM['Part Quantity']*Dif_Parts_TM['FOB']

    # Concantenando
    Dif_Parts = pd.concat([Dif_Parts_TM, Dif_Parts_SCZ])

    df = df[df['Evaluation Results*'] == '4'].reset_index()
    monto_reconocido = df[df['Dealer'] == 'SCZ']['Total Remittance Amount'].sum()
    df = df[['Claim No.','Parts Remittance Amount']]

    Glob_Dif_Parts = Dif_Parts.groupby(['Dealer','Claim No.','VIN']).agg({'Parts Claim Amount':'sum'}).reset_index()
    Glob_Dif_Parts = pd.merge(Glob_Dif_Parts, df, how='left', on='Claim No.')
    Glob_Dif_Parts['Parts_Mount_Dif'] = Glob_Dif_Parts['Parts Remittance Amount'] - Glob_Dif_Parts['Parts Claim Amount']

    claim_numbers = Glob_Dif_Parts[Glob_Dif_Parts['Parts_Mount_Dif']!=0]['Claim No.'].unique()
    Detail_Dif_Parts = Dif_Parts[Dif_Parts['Claim No.'].isin(claim_numbers)]

    # Calcular montos
    monto_dif_partes = Glob_Dif_Parts['Parts_Mount_Dif'].sum()

    # Mostrar los resultados en la aplicación
    st.write(f"### Diferencia de Partes")
    st.write(f"**Detalle Items con Diferencia:** {monto_dif_partes:,.2f}")

    st.write("### Detalle de Reclamos con Diferencia")
    st.dataframe(Glob_Dif_Parts)

    st.write("### Detalle de Partes con Diferencia")
    st.dataframe(Detail_Dif_Parts)
    
    output_parts = BytesIO()
    with pd.ExcelWriter(output_parts, engine='xlsxwriter') as writer:
        Dif_Parts.to_excel(writer, sheet_name='Diferencias Partes', index=False)
    output_parts.seek(0)
    st.download_button(label="Descargar diferencias en partes", data=output_parts, file_name="Diferencias_Partes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # REPORTE DE PAGOS A NIBOL

    # Agrupando
    NIBOL_Parts = Dif_Parts_SCZ.groupby(['Claim No.']).agg({'Part Quantity': 'sum', 'Parts Claim Amount': 'sum'})
    NIBOL_Parts = NIBOL_Parts.reset_index()

    # Reporte
    NIBOL_Report = Revision[['Dealer','Claim No.','VIN']]
    NIBOL_Report = NIBOL_Report[NIBOL_Report['Dealer']=='SCZ']
    NIBOL_Report = pd.merge(NIBOL_Report, NIBOL_Parts, how='left', on='Claim No.')
    NIBOL_Report['Parts Claim Amount'] = NIBOL_Report['Parts Claim Amount'].fillna(0)

    # Gestion de MO y Terceros
    NIBOL_Labour = Revision.groupby(['Claim No.']).agg({'Labor Remittance Amount': 'sum', 'Sublet Remittance Amount': 'sum'})
    NIBOL_Labour = NIBOL_Labour.reset_index()
    NIBOL_Labour['Labor Remittance Amount'] = NIBOL_Labour['Labor Remittance Amount'].fillna(0)
    NIBOL_Labour['Labor Remittance Amount'] = NIBOL_Labour['Labor Remittance Amount'] * 0.5
    NIBOL_Labour['Sublet Remittance Amount'] = NIBOL_Labour['Sublet Remittance Amount'].fillna(0)

    # Uniendo BD
    NIBOL_Report = pd.merge(NIBOL_Report, NIBOL_Labour, how='left', on='Claim No.')

    # Total Remittance
    NIBOL_Report['Total Claim Amount'] = NIBOL_Report['Parts Claim Amount'] + NIBOL_Report['Labor Remittance Amount'] + NIBOL_Report['Sublet Remittance Amount']

    st.write("### Detalle Pago a Nibol")
    st.dataframe(NIBOL_Report)

    # Calcular montos
    monto_pagar_nibol = NIBOL_Report['Total Claim Amount'].sum()  

    # Mostrar los resultados en la aplicación
    st.write(f"### Resumen de la Operación")
    st.write(f"✅ **Monto reconocido por Reclamos de Nibol:** {monto_reconocido:,.2f}")
    st.write(f"💰 **Monto a Pagar a NIBOL:** {monto_pagar_nibol:,.2f}")

    output_parts = BytesIO()
    with pd.ExcelWriter(output_parts, engine='xlsxwriter') as writer:
        NIBOL_Report.to_excel(writer, sheet_name='Reporte Pago', index=False)
    output_parts.seek(0)
    st.download_button(label="Descargar Reporte", data=output_parts, file_name="NIBOL_Facturacion.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
