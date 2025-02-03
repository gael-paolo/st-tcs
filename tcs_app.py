import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# Configuración de la aplicación
st.title("Análisis de Pagos de Garantía")
st.write("Sube un archivo Excel para procesar los datos y obtener análisis detallados.")

# Sección para cargar el archivo
uploaded_file = st.file_uploader("Sube el archivo Excel", type=["xlsm", "xlsx"])

if uploaded_file is not None:
    # Cargar datos
    df = pd.read_excel(uploaded_file, sheet_name='MonthlyERP', header=1)
    df = df.iloc[6:, 3:]
    df = df[['Claim No.', 'VIN', 'Model Basic', 'Date Sold', 'Date Repaired', 'Mileage', 'PFP', 'Operation Code (A)',
             'Operation Hour (A)', 'Operation Code (B)', 'Operation Hour (B)', 'Operation Code (C)', 'Operation Hour (C)',
             'Part  No. (A)', 'Part Quantity (A)', 'Parts Price\nTotal (A)', 'Part  No. (B)', 'Part Quantity (B)',
             'Parts Price Total (B)', 'Part  No. (C)', 'Part Quantity (C)', 'Parts Price Total (C)', 'Part  No. (D)',
             'Part Quantity (D)', 'Parts Price Total (D)', 'Part  No. (E)', 'Part Quantity (E)', 'Parts Price Total (E)',
             'Sublet Amount(A)', 'Sublet Amount (B)', 'Sublet Amount (C)', 'Sublet Amount (D)', 'Evaluation Results*',
             'Claim Amount Parts', 'Claim Amount Labor', 'Claim Amount Sublet', 'Claim Amount Total', 'Parts Remittance Amount',
             'Labor Remittance Amount', 'Sublet Remittance Amount', 'Total Remittance Amount']]
    
    # Generar resumen
    Summary = df.groupby(['Evaluation Results*']).agg({'Claim Amount Parts': 'sum', 'Claim Amount Labor': 'sum',
                                                        'Claim Amount Sublet': 'sum', 'Claim Amount Total': 'sum'}).reset_index()
    Summary[['Claim Amount Parts', 'Claim Amount Labor', 'Claim Amount Sublet', 'Claim Amount Total']] = Summary[['Claim Amount Parts', 'Claim Amount Labor', 
                                                                                                                   'Claim Amount Sublet', 'Claim Amount Total']].apply(lambda x: x.map(lambda y: f"{y:,.2f}"))
    st.write("### Resumen del análisis")
    st.dataframe(Summary)
    
    # Filtrar por estado de evaluación
    st.write("### Datos por tipo de evaluación")
    status_options = {'1': 'Return', '2': 'Reject', '3': 'Pending', '4': 'Approve'}
    selected_status = st.selectbox("Selecciona el estado", list(status_options.keys()), format_func=lambda x: status_options[x])
    filtered_df = df[df['Evaluation Results*'] == selected_status]
    st.dataframe(filtered_df)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        filtered_df.to_excel(writer, sheet_name='Datos Evaluacion', index=False)
    output.seek(0)
    st.download_button(label="Descargar datos por evaluación", data=output, file_name="Datos_Evaluacion.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Análisis de diferencias
    df['Parts Dif'] = df['Parts Remittance Amount'] - df['Claim Amount Parts']
    df['Labor Dif'] = df['Labor Remittance Amount'] - df['Claim Amount Labor']
    df['Sublet Dif'] = df['Sublet Remittance Amount'] - df['Claim Amount Sublet']
    df['Total Dif'] = df['Total Remittance Amount'] - df['Claim Amount Total']
    
    agg_result = df[df['Evaluation Results*'] == '4'].agg({'Parts Dif': 'sum', 'Labor Dif': 'sum', 'Sublet Dif': 'sum', 'Total Dif': 'sum'})
    formatted_agg_df = pd.DataFrame(agg_result).transpose().map(lambda x: f"{x:,.2f}")
    
    st.write("### Análisis de diferencias en Aprobados")
    st.dataframe(formatted_agg_df)
    
    # Obtener diferencias en partes
    Parts_Dif = df[(df['Parts Dif'] < 0) & (df['Evaluation Results*'] == '4')].reset_index()
    Parts_Dif = Parts_Dif[['Claim No.', 'VIN', 'Model Basic', 'Date Sold', 'Date Repaired', 'Mileage', 'PFP',
                           'Part  No. (A)', 'Part Quantity (A)', 'Parts Price\nTotal (A)', 'Part  No. (B)',
                           'Part Quantity (B)', 'Parts Price Total (B)', 'Part  No. (C)', 'Part Quantity (C)',
                           'Parts Price Total (C)', 'Part  No. (D)', 'Part Quantity (D)', 'Parts Price Total (D)',
                           'Part  No. (E)', 'Part Quantity (E)', 'Parts Price Total (E)', 'Claim Amount Parts',
                           'Parts Remittance Amount', 'Parts Dif']]
    
    st.write("### Casos con diferencias en partes")
    st.dataframe(Parts_Dif)
    
    output_parts = BytesIO()
    with pd.ExcelWriter(output_parts, engine='xlsxwriter') as writer:
        Parts_Dif.to_excel(writer, sheet_name='Diferencias Partes', index=False)
    output_parts.seek(0)
    st.download_button(label="Descargar diferencias en partes", data=output_parts, file_name="Diferencias_Partes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
