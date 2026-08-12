'''
Volumetric Calculator - Monte Carlo probabilistic volumetrics for oil & gas prospects.
Developed by Miled Sefair.
'''

from scipy.stats import norm, truncnorm
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import io

import streamlit as st

st.set_page_config(page_title='Volumetric Calculator',
                    page_icon='📌',
                    initial_sidebar_state='collapsed', 
                    layout='wide')

# Change head title
def set_page_title(title):
    st.markdown(unsafe_allow_html=True, body=f"""
        <iframe height=0 srcdoc="<script>
            const title = window.parent.document.querySelector('title') \
                
            const oldObserver = window.parent.titleObserver
            if (oldObserver) {{
                oldObserver.disconnect()
            }} \

            const newObserver = new MutationObserver(function(mutations) {{
                const target = mutations[0].target
                if (target.text !== '{title}') {{
                    target.text = '{title}'
                }}
            }}) \

            newObserver.observe(title, {{ childList: true }})
            window.parent.titleObserver = newObserver \

            title.text = '{title}'
        </script>" />
    """)

set_page_title("Volumetric Calculator")

# Hide Hamburguer menu
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)


# Self-contained styling for online deployment
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.25);
    padding: 0.75rem;
    border-radius: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# funcions
def STOIP(area, ht, phi, sw, ntg, rf, bo):
    stoip = (area*1000*ht*phi*(1-sw)*ntg*rf)/bo
    return stoip

def STGIP(area, ht, phi, sw, ntg, rf, bg):
    ogip = (area*1000*ht*phi*(1-sw)*ntg*rf)/bg
    return ogip

def POIS(area, ht, phi, sw, ntg, bo):
    pois = area*1000*ht*phi*(1-sw)*ntg/bo
    return pois

def GOIS(area, ht, phi, sw, ntg, bg):
    gois = area*1000*ht*phi*(1-sw)*ntg/bg
    return gois

def sample_property(mean, sd, size, lower=None, upper=None, seed=None):
    """Muestrea una distribucion normal truncada a [lower, upper] para evitar
    valores fuera de rango fisico (ej. porosidad negativa, Sw > 1, area < 0).
    Si sd <= 0, devuelve el valor medio constante."""
    if sd is None or sd <= 0:
        return np.full(size, mean)
    a = (lower - mean) / sd if lower is not None else -np.inf
    b = (upper - mean) / sd if upper is not None else np.inf
    return truncnorm(a, b, loc=mean, scale=sd).rvs(size, random_state=seed)

def make_seed_generator(base_seed):
    """Genera semillas incrementales a partir de una semilla base, para que cada
    propiedad muestreada use un stream aleatorio distinto (evita correlacion
    espuria entre variables) pero el resultado completo sea reproducible.
    Si base_seed es None o 0, devuelve None siempre (comportamiento aleatorio)."""
    if not base_seed:
        return lambda: None
    state = {'i': 0}
    def _next():
        state['i'] += 1
        return int(base_seed) + state['i']
    return _next

def fmt_vol(x, decimals=1):
    """Formatea un volumen con separador de miles y pocos decimales: sin
    decimales para numeros grandes (tipico en GAS, Mm3 en miles) y con
    `decimals` para numeros chicos (tipico en OIL)."""
    if x is None or (isinstance(x, (int, float)) and np.isnan(x)):
        return '-'
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.{decimals}f}"

# Sample input template (replaces the old external GitHub Pages link)
def build_sample_template():
    template_cols = [
        'NAME', 'FLUID', 'DEPTH',
        'AREA', 'AREA_SD', 'HT', 'HT_SD', 'PHI', 'PHI_SD',
        'NTG', 'NTG_SD', 'SW', 'SW_SD', 'RF', 'RF_SD',
        'BO', 'BO_SD', 'BG', 'BG_SD',
        'D_AREA',
        'TRAPSEAL', 'RESROCK', 'SRCMIG', 'TIMING'
    ]

    sample_rows = [
        {
            'NAME': 'Prospecto_Oil_A', 'FLUID': 'OIL', 'DEPTH': 2500,
            'AREA': 3.5, 'AREA_SD': 0.5, 'HT': 8.0, 'HT_SD': 1.0,
            'PHI': 0.18, 'PHI_SD': 0.02, 'NTG': 0.6, 'NTG_SD': 0.1,
            'SW': 0.3, 'SW_SD': 0.05, 'RF': 0.2, 'RF_SD': 0.05,
            'BO': 1.2, 'BO_SD': 0.05, 'BG': '', 'BG_SD': '',
            'D_AREA': 40,
            'TRAPSEAL': 80, 'RESROCK': 90, 'SRCMIG': 85, 'TIMING': 95
        },
        {
            'NAME': 'Prospecto_Gas_B', 'FLUID': 'GAS', 'DEPTH': 3100,
            'AREA': 5.0, 'AREA_SD': 0.8, 'HT': 12.0, 'HT_SD': 2.0,
            'PHI': 0.15, 'PHI_SD': 0.02, 'NTG': 0.5, 'NTG_SD': 0.1,
            'SW': 0.35, 'SW_SD': 0.05, 'RF': 0.6, 'RF_SD': 0.1,
            'BO': '', 'BO_SD': '', 'BG': 0.006, 'BG_SD': 0.001,
            'D_AREA': 60,
            'TRAPSEAL': 70, 'RESROCK': 85, 'SRCMIG': 80, 'TIMING': 90
        }
    ]

    template_df = pd.DataFrame(sample_rows, columns=template_cols)

    iowrite = io.BytesIO()
    with pd.ExcelWriter(iowrite, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Input')

        instructions = pd.DataFrame({
            'Columna': template_cols,
            'Descripcion': [
                'Nombre del prospecto/pozo', 'Tipo de fluido: OIL o GAS', 'Profundidad (informativo, m)',
                'Area media [Km2]', 'Desvio estandar de Area', 'Espesor medio [m]', 'Desvio estandar de Espesor',
                'Porosidad media [fraccion]', 'Desvio estandar de Porosidad',
                'Net-to-Gross medio [fraccion]', 'Desvio estandar de NTG',
                'Saturacion de agua media [fraccion]', 'Desvio estandar de Sw',
                'Factor de recobro medio [fraccion]', 'Desvio estandar de RF',
                'Factor volumetrico de petroleo (dejar vacio si FLUID=GAS)', 'Desvio estandar de Bo',
                'Factor volumetrico de gas (dejar vacio si FLUID=OIL)', 'Desvio estandar de Bg',
                'Area de drenaje por pozo [Ha]',
                'Probabilidad de Trampa/Sello [%] (opcional, solo si se usa riesgo geologico)',
                'Probabilidad de Roca Reservorio [%] (opcional)',
                'Probabilidad de Generacion/Migracion [%] (opcional)',
                'Probabilidad de Timing [%] (opcional)'
            ]
        })
        instructions.to_excel(writer, index=False, sheet_name='Instrucciones')

    return iowrite.getvalue()

# @st.cache
def plot_results():
    fig1 = sns.displot(value, kind='hist', stat='density', kde=True)
    if fluid == 'GAS':
        fig1.set(xlabel='SGIP Mm3', ylabel='Frequency')
    else:
        fig1.set(xlabel='STOIP Mm3', ylabel='Frequency')
    fig1.set(title=str(name)+' - Volume')
    st.pyplot(fig1)

    fig2 = sns.displot(value, kind='ecdf')
    if fluid == 'GAS':
        fig2.set(xlabel='SGIP Mm3', ylabel='Probability')
    else:
        fig2.set(xlabel='STOIP Mm3', ylabel='Probability')
    plt.axhline(y=0.9, label='P10', color='red', linestyle='--')
    plt.axhline(y=0.5, label='P50', color='red', linestyle=':')
    plt.axhline(y=0.1, label='P90', color='red', linestyle='-.')
    plt.legend(prop={'size':6})
    st.pyplot(fig2)
    plt.close('all')

# @st.cache
def plot_properties_dist():
    fig_area = sns.displot(area, kind='hist', stat='density', kde=True)
    fig_area.set(xlabel='Surface Area (Km2)', ylabel='Probability')
    fig_area.set(title=str(name)+' - Area')
    st.pyplot(fig_area)

    fig_ht = sns.displot(ht, kind='hist', stat='density', kde=True)
    fig_ht.set(xlabel='Thickness (m)', ylabel='Probability')
    fig_ht.set(title=str(name)+' - Thickness')
    st.pyplot(fig_ht)

    fig_phi = sns.displot(phi, kind='hist', stat='density', kde=True)
    fig_phi.set(xlabel='Porosity (fr)', ylabel='Probability')
    fig_phi.set(title=str(name)+' - Porosity')
    st.pyplot(fig_phi)

    fig_ntg = sns.displot(ntg, kind='hist', stat='density', kde=True)
    fig_ntg.set(xlabel='Net-to-Gross (fr)', ylabel='Probability')
    fig_ntg.set(title=str(name)+' - Net-to-Gross')
    st.pyplot(fig_ntg)

    fig_sw = sns.displot(sw, kind='hist', stat='density', kde=True)
    fig_sw.set(xlabel='Water Saturation (fr)', ylabel='Probability')
    fig_sw.set(title=str(name)+' - Water Saturation')
    st.pyplot(fig_sw)

    fig_rf = sns.displot(rf, kind='hist', stat='density', kde=True)
    fig_rf.set(xlabel='Recovery Factor (fr)', ylabel='Probability')
    fig_rf.set(title=str(name)+' - Recovery Factor')
    st.pyplot(fig_rf)

    if fluid == 'GAS':
        fig_bg = sns.displot(bg, kind='hist', stat='density', kde=True)
        fig_bg.set(xlabel=' Gas Volumetric Factor (fr)', ylabel='Probability')
        fig_bg.set(title=str(name)+' - Bg')
        st.pyplot(fig_bg)
    else:
        fig_bo = sns.displot(bo, kind='hist', stat='density', kde=True)
        fig_bo.set(xlabel=' Oil Volumetric Factor (fr)', ylabel='Probability')
        fig_bo.set(title=str(name)+' - Bo')
        st.pyplot(fig_bo)

    plt.close('all')


st.title('Volumetric Calculator')
st.caption('Developed by Miled Sefair · Contact: milosefair@gmail.com')

### Manual Input
with st.expander('Manual Input', expanded=False):
    left_column, right_column = st.columns(2)

    area_m = left_column.number_input('Area [Km²]', min_value=0.000001, max_value=1000.0, step=0.01, value=1.0, format='%.2f',
        help='Área media del reservorio. Rango típico: 0.1 a 1000 Km².')
    area_sd = right_column.number_input('Area Std. dev [Km²]', min_value=0.000001, step=0.01, value=0.1, format='%.2f', key='area_sd',
        help='Incertidumbre del área (desvío estándar). Sugerido: 10-30% del valor medio.')

    ht_m = left_column.number_input('Thickness [m]', min_value=0.000001, step=0.1, value=5.0, format='%.1f',
        help='Espesor neto promedio de la formación, en metros. Rango típico: 1 a 100 m.')
    ht_sd = right_column.number_input('Thickness Std. dev [m]', min_value=0.000001, step=0.1, value=0.1, format='%.1f', key='ht_sd',
        help='Incertidumbre del espesor (desvío estándar). Sugerido: 10-30% del valor medio.')

    phi_m = left_column.number_input('Porosity [fraction]', min_value=0.000001, max_value=1.0, step=0.01, value=0.2, format='%.2f',
        help='Porosidad efectiva, como fracción entre 0 y 1. Rango típico: 0.05 a 0.30 (5% a 30%).')
    phi_sd = right_column.number_input('Porosity Std. dev', min_value=0.000001, step=0.01, value=0.05, format='%.2f', key='phi_sd',
        help='Incertidumbre de la porosidad. Sugerido: 0.02 a 0.05.')

    ntg_m = left_column.number_input('Net-to-Gross [fraction]', min_value=0.000001, max_value=1.0, step=0.01, value=0.6, format='%.2f',
        help='Relación entre espesor neto y espesor bruto, entre 0 y 1. Rango típico: 0.3 a 1.0.')
    ntg_sd = right_column.number_input('NTG Std. dev', min_value=0.000001, step=0.01, value=0.15, format='%.2f', key='ntg_sd',
        help='Incertidumbre del NTG. Sugerido: 0.05 a 0.20.')

    sw_m = left_column.number_input('Water Saturation [fraction]', min_value=0.000001, max_value=1.0, step=0.01, value=0.3, format='%.2f',
        help='Saturación de agua irreducible, entre 0 y 1. Rango típico: 0.15 a 0.50.')
    sw_sd = right_column.number_input('Sw Std. dev', min_value=0.000001, step=0.01, value=0.05, format='%.2f', key='sw_sd',
        help='Incertidumbre de la saturación de agua. Sugerido: 0.02 a 0.10.')

    rf_m = left_column.number_input('Recovery Factor [fraction]', min_value=0.000001, max_value=1.0, step=0.01, value=0.2, format='%.2f',
        help='Fracción del volumen in-situ que se espera recuperar, entre 0 y 1. Rango típico: 0.05 (no convencional) a 0.40 (convencional).')
    rf_sd = right_column.number_input('RF Std. dev', min_value=0.000001, step=0.01, value=0.05, format='%.2f', key='rf_sd',
        help='Incertidumbre del factor de recobro. Sugerido: 0.02 a 0.10.')

    bo_m = left_column.number_input('Bo', min_value=0.000001, step=0.01, value=1.2, format='%.2f',
        help='Factor volumétrico del petróleo (volumen a condiciones de reservorio / volumen a superficie). Rango típico: 1.0 a 2.0.')
    bo_sd = right_column.number_input('Bo Std. dev', min_value=0.000001, step=0.01, value=0.1, format='%.2f', key='bo_sd',
        help='Incertidumbre de Bo. Sugerido: 0.05 a 0.15.')

    iters_man = right_column.number_input('Iterations', min_value=100, step=1000, value=10000, key='iters_manual',
        help='Cantidad de simulaciones de Monte Carlo. A más iteraciones, resultado más estable pero más lento. Sugerido: 10.000.')
    seed_man = left_column.number_input('Random seed (0 = aleatorio)', min_value=0, step=1, value=0, key='seed_manual',
        help='Fijá un número distinto de 0 para que la corrida sea reproducible (mismos inputs → mismos resultados). Dejalo en 0 para que sea aleatoria.')

    use_risk_man = st.checkbox('Include Geological Risk (optional)', value=False, key='use_risk_manual',
        help='Activá esta opción para calcular la probabilidad de éxito geológico (Pg) y los volúmenes riesgados.')
    if use_risk_man:
        st.caption('Probabilidad de éxito de cada elemento del sistema petrolero (%). Rango: 0% a 100% en cada uno.')
        risk_col1, risk_col2, risk_col3, risk_col4 = st.columns(4)
        trapseal_m = risk_col1.number_input('Trap/Seal [%]', min_value=0.0, max_value=100.0, step=1.0, value=80.0, format='%.0f', key='trapseal_man',
            help='Probabilidad de que la trampa y el sello sean efectivos. Rango típico: 50% a 95%.')
        resrock_m  = risk_col2.number_input('Reservoir Rock [%]', min_value=0.0, max_value=100.0, step=1.0, value=90.0, format='%.0f', key='resrock_man',
            help='Probabilidad de presencia de roca reservorio con calidad suficiente. Rango típico: 60% a 95%.')
        srcmig_m   = risk_col3.number_input('Source/Migration [%]', min_value=0.0, max_value=100.0, step=1.0, value=85.0, format='%.0f', key='srcmig_man',
            help='Probabilidad de generación y migración efectiva de hidrocarburos. Rango típico: 50% a 95%.')
        timing_m   = risk_col4.number_input('Timing [%]', min_value=0.0, max_value=100.0, step=1.0, value=95.0, format='%.0f', key='timing_man',
            help='Probabilidad de que la sincronización entre generación, migración y trampa sea favorable. Rango típico: 70% a 99%.')





    # Manual input calc
    if left_column.button('Compute'):
        next_seed = make_seed_generator(seed_man)

        area = sample_property(area_m, area_sd, iters_man, lower=1e-6, seed=next_seed())
        ht   = sample_property(ht_m, ht_sd, iters_man, lower=1e-6, seed=next_seed())
        phi  = sample_property(phi_m, phi_sd, iters_man, lower=0.0, upper=1.0, seed=next_seed())
        ntg  = sample_property(ntg_m, ntg_sd, iters_man, lower=0.0, upper=1.0, seed=next_seed())
        sw   = sample_property(sw_m, sw_sd, iters_man, lower=0.0, upper=1.0, seed=next_seed())
        rf   = sample_property(rf_m, rf_sd, iters_man, lower=0.0, upper=1.0, seed=next_seed())
        bo   = sample_property(bo_m, bo_sd, iters_man, lower=1e-6, seed=next_seed())

        name = 'Manual Input'
        fluid = 'OIL'
        value = STOIP(area, ht, phi, sw, ntg, rf, bo)

        p10 = np.percentile(value,10)
        p50 = np.percentile(value,50)
        p90 = np.percentile(value,90)

        if use_risk_man:
            pro_scc_man = (trapseal_m/100) * (resrock_m/100) * (srcmig_m/100) * (timing_m/100)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric('P90', f"{fmt_vol(p10)} Mm3")
            m2.metric('P50', f"{fmt_vol(p50)} Mm3")
            m3.metric('P10', f"{fmt_vol(p90)} Mm3")
            m4.metric('Success (Pg)', f"{pro_scc_man*100:.1f}%")

            r1, r2, r3 = st.columns(3)
            r1.metric('Risked P90', f"{fmt_vol(p10*pro_scc_man)} Mm3")
            r2.metric('Risked P50', f"{fmt_vol(p50*pro_scc_man)} Mm3")
            r3.metric('Risked P10', f"{fmt_vol(p90*pro_scc_man)} Mm3")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric('P90', f"{fmt_vol(p10)} Mm3")
            m2.metric('P50', f"{fmt_vol(p50)} Mm3")
            m3.metric('P10', f"{fmt_vol(p90)} Mm3")

        plot_results()

        st.success('Completed!')

st.markdown('***')

### File upload calculations
st.download_button(
    label='📥 Download Sample Input Template',
    data=build_sample_template(),
    file_name='volumetrics_input_template.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    help='Plantilla de Excel con los valores de carga iniciales y una hoja de instrucciones.'
)

loaded_file = st.file_uploader('File Input',type=['xlsx'],
    help='Subí el Excel completo con tus prospectos, siguiendo las columnas de la plantilla de ejemplo.')

col_iters, col_seed = st.columns(2)
iters = col_iters.number_input('Iterations', min_value=100, step=1000, value=10000,
    help='Cantidad de simulaciones de Monte Carlo por prospecto. A más iteraciones, resultado más estable pero más lento. Sugerido: 10.000.')
seed = col_seed.number_input('Random seed (0 = aleatorio)', min_value=0, step=1, value=0,
    help='Fijá un valor distinto de 0 para que la corrida sea reproducible (mismos inputs → mismos resultados). Dejalo en 0 para que sea aleatoria.')

# Graph output selection
left_col_2, right_col_2, right_col_3 = st.columns(3)

graph_out = left_col_2.checkbox(label='Show Graphics',
    help='Muestra el histograma y la curva de probabilidad acumulada del volumen de cada prospecto.')
graph_prop = right_col_2.checkbox(label='Show Properties Distribution',
    help='Muestra el histograma de cada variable de entrada (área, espesor, porosidad, etc.) para cada prospecto.')
use_risk = right_col_3.checkbox(label='Include Geological Risk (optional)', value=False,
    help='Usa las columnas TRAPSEAL, RESROCK, SRCMIG y TIMING del Excel (0 a 100%) para calcular la probabilidad de éxito y los volúmenes riesgados.')


if loaded_file is not None:
    df = pd.read_excel(loaded_file)
    # st.dataframe(df)

    required_cols = ['NAME', 'FLUID', 'AREA', 'AREA_SD', 'HT', 'HT_SD',
                      'PHI', 'PHI_SD', 'NTG', 'NTG_SD', 'SW', 'SW_SD',
                      'RF', 'RF_SD', 'D_AREA']
    missing_required = [c for c in required_cols if c not in df.columns]
    if missing_required:
        st.error(f"El archivo subido no tiene las columnas requeridas: {', '.join(missing_required)}. "
                  "Descargá la plantilla de ejemplo y respetá los nombres de columna.")
        st.stop()

    next_seed = make_seed_generator(seed)

    for p in range(len(df)):
        name = df['NAME'][p]

        card = st.container(border=True)
        card.subheader(name)

        # read parameters
        fluid = df['FLUID'][p]

        vol_factor_cols = ['BG', 'BG_SD'] if fluid == 'GAS' else ['BO', 'BO_SD']
        missing_vol_factor = [c for c in vol_factor_cols if c not in df.columns or pd.isna(df[c][p])]
        if missing_vol_factor:
            card.error(f"Faltan los valores {', '.join(missing_vol_factor)} requeridos para fluido {fluid}.")
            st.stop()

        area = sample_property(df['AREA'][p], df['AREA_SD'][p], iters, lower=1e-6, seed=next_seed())
        ht   = sample_property(df['HT'][p], df['HT_SD'][p], iters, lower=1e-6, seed=next_seed())
        phi  = sample_property(df['PHI'][p], df['PHI_SD'][p], iters, lower=0.0, upper=1.0, seed=next_seed())
        ntg  = sample_property(df['NTG'][p], df['NTG_SD'][p], iters, lower=0.0, upper=1.0, seed=next_seed())
        sw   = sample_property(df['SW'][p], df['SW_SD'][p], iters, lower=0.0, upper=1.0, seed=next_seed())
        rf   = sample_property(df['RF'][p], df['RF_SD'][p], iters, lower=0.0, upper=1.0, seed=next_seed())
        if fluid == 'GAS':
            bg   = sample_property(df['BG'][p], df['BG_SD'][p], iters, lower=1e-6, seed=next_seed()) # for gas
        else:
            bo   = sample_property(df['BO'][p], df['BO_SD'][p], iters, lower=1e-6, seed=next_seed()) # for oil
        
        # Drainage Area (Ha)
        d_area = df['D_AREA'][p]
        if pd.isna(d_area) or d_area <= 0:
            card.error("D_AREA debe ser un número mayor a 0.")
            st.stop()

        # Risk data (optional geological risk calculation)
        if use_risk:
            risk_cols = ['TRAPSEAL', 'RESROCK', 'SRCMIG', 'TIMING']
            missing_risk_cols = [c for c in risk_cols if c not in df.columns or pd.isna(df[c][p])]
            if missing_risk_cols:
                card.warning(f"Faltan valores de riesgo ({', '.join(missing_risk_cols)}). Se asume probabilidad de éxito = 100% para este prospecto.")
                pro_scc = 1.0
            else:
                pro_ts = df['TRAPSEAL'][p]/100
                pro_rr = df['RESROCK'][p]/100
                pro_sm = df['SRCMIG'][p]/100
                pro_ti = df['TIMING'][p]/100
                pro_scc = (pro_ts * pro_rr * pro_sm * pro_ti)
        else:
            pro_scc = 1.0

        # Calculate volumes (stock tank)
        if fluid == 'OIL':
            value = STOIP(area, ht, phi, sw, ntg, rf, bo)
        elif fluid == 'GAS':
            value = STGIP(area, ht, phi, sw, ntg, rf, bg)

        # POIS/GOIS
        if fluid == 'OIL':
            value_in_situ = POIS(area, ht, phi, sw, ntg, bo) 
        elif fluid == 'GAS':
            value_in_situ = GOIS(area, ht, phi, sw, ntg, bg)

        # Percentile (stock tank)
        p10 = round(np.percentile(value,10),2)
        p50 = round(np.percentile(value,50),2)
        p90 = round(np.percentile(value,90),2)

        # Percentile (in situ)
        p10_ip = round(np.percentile(value_in_situ,10),2)
        p50_ip = round(np.percentile(value_in_situ,50),2)
        p90_ip = round(np.percentile(value_in_situ,90),2)

        # number of wells in measured area
        wells_num = np.percentile(area,50)/d_area*100

        # type well cummulative
        type_well_cum = p50/wells_num

        # Metric cards
        if use_risk:
            col_30, col_31, col_32, col_33 = card.columns(4)
        else:
            col_30, col_31, col_33 = card.columns(3)

        with col_30:
            st.metric('P90 In Place', f"{fmt_vol(p10_ip)} Mm3")
            st.metric('P50 In Place', f"{fmt_vol(p50_ip)} Mm3")
            st.metric('P10 In Place', f"{fmt_vol(p90_ip)} Mm3")

        with col_31:
            st.metric('P90', f"{fmt_vol(p10)} Mm3")
            st.metric('P50', f"{fmt_vol(p50)} Mm3")
            st.metric('P10', f"{fmt_vol(p90)} Mm3")

        if use_risk:
            with col_32:
                st.metric('Risked P90', f"{fmt_vol(p10*pro_scc)} Mm3")
                st.metric('Risked P50', f"{fmt_vol(p50*pro_scc)} Mm3")
                st.metric('Risked P10', f"{fmt_vol(p90*pro_scc)} Mm3")

        with col_33:
            if use_risk:
                st.metric('Success (Pg)', f"{pro_scc*100:.1f}%")
            st.metric('Number of Wells', f"{wells_num:.0f}")
            st.metric(f'{fluid} Cum per Well', f"{fmt_vol(type_well_cum)} Mm3")

        # Plots
        if graph_out:
            with card.expander('Volume Graph'):
                plot_results()

        if graph_prop:
            with card.expander('Properties Graph'):
                plot_properties_dist()

        # Write data in dataframe
        df.loc[p,'P90_IP'] = p10_ip
        df.loc[p,'P50_IP'] = p50_ip
        df.loc[p,'P10_IP'] = p90_ip
        df.loc[p,'P90'] = p10
        df.loc[p,'P50'] = p50
        df.loc[p,'P10'] = p90
        if use_risk:
            df.loc[p,'Rsk_P90'] = round(p10*pro_scc,2)
            df.loc[p,'Rsk_P50'] = round(p50*pro_scc,2)
            df.loc[p,'Rsk_P10'] = round(p90*pro_scc,2)
            df.loc[p,'Succ_PROB'] = pro_scc*100
        df.loc[p,'Wells'] = round(wells_num)
        df.loc[p,'Well_Type_Cum'] = round(type_well_cum,1)

    # Summary table
    st.subheader('Summary')

    hide_col = ['AREA_SD','HT_SD','PHI_SD','NTG_SD','SW_SD','RF_SD','BO_SD','BG_SD',
                'TRAPSEAL','RESROCK','SRCMIG','TIMING','D_AREA',
                'HT','PHI','NTG','SW', 'RF','BO','BG','AREA','DEPTH']

    summary_df = df.drop(hide_col, axis=1, errors='ignore').set_index('NAME')

    vol_cols = [c for c in ['P90_IP','P50_IP','P10_IP','P90','P50','P10',
                             'Rsk_P90','Rsk_P50','Rsk_P10','Well_Type_Cum'] if c in summary_df.columns]
    column_config = {c: st.column_config.NumberColumn(format="%,.0f Mm³") for c in vol_cols}
    if 'Wells' in summary_df.columns:
        column_config['Wells'] = st.column_config.NumberColumn(format="%.0f")
    if 'Succ_PROB' in summary_df.columns:
        column_config['Succ_PROB'] = st.column_config.NumberColumn(format="%.1f%%")

    st.dataframe(summary_df, column_config=column_config)

    show_input = st.checkbox(label='Show Input Data')
    if show_input:
        st.dataframe(df.set_index('NAME').fillna(value=''))
    
    if st.checkbox('Download Results'):
        iowrite = io.BytesIO()
        df.to_excel(iowrite, index=False, engine='openpyxl')
        st.download_button(
            label='Download Data',
            data=iowrite.getvalue(),
            file_name='output.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    



st.markdown('---')
st.caption('Volumetric Calculator · Developed by Miled Sefair · Contact: milosefair@gmail.com')
