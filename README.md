# Volumetric Calculator

Calculadora volumétrica probabilística (Monte Carlo) para reservorios de petróleo y gas, desarrollada por Miled Sefair.

## Uso local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Uso

1. Descargá la plantilla de Excel desde el botón **"Download Sample Input Template"** dentro de la app (incluye una hoja de instrucciones).
2. Completá la plantilla con tus datos de área, espesor, porosidad, NTG, Sw, RF, Bo/Bg, área de drenaje y (opcionalmente) los parámetros de riesgo geológico (Trampa/Sello, Roca Reservorio, Generación/Migración, Timing).
3. Subí el archivo completo desde **"File Input"**.
4. Activá el checkbox **"Include Geological Risk (optional)"** si querés que se calcule la probabilidad de éxito (Pg) y los volúmenes riesgados. Si no lo activás, se muestran solo los volúmenes sin riesgar.
5. (Opcional) Poné un **Random seed** distinto de 0 si necesitás que la corrida sea reproducible (mismos inputs → mismos resultados). Dejalo en 0 para que cada corrida sea aleatoria.
6. Descargá los resultados desde **"Download Results"**.

## Notas metodológicas

- Las propiedades petrofísicas se muestrean con una **distribución normal truncada**: área, espesor y factores volumétricos (Bo/Bg) no pueden ser negativos, y porosidad/NTG/Sw/RF quedan acotados entre 0 y 1. Esto evita que desvíos estándar grandes generen valores físicamente imposibles en la simulación de Monte Carlo.
- La convención P90/P50/P10 sigue el uso habitual en la industria: P90 es el caso conservador (menor volumen, 90% de probabilidad de exceder ese valor) y P10 el caso optimista.

## Deploy en Streamlit Community Cloud

1. Subí este repositorio a GitHub.
2. Entrá a [share.streamlit.io](https://share.streamlit.io), conectá tu cuenta de GitHub y elegí este repo.
3. Indicá `app.py` como archivo principal y desplegá.
