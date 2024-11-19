import logging
import pandas as pd
import altair as alt
from flask import Flask
from flask import url_for
from flask import render_template
from flask import request
from flask import redirect
from flask import session
from datetime import datetime
from kgmodel import (Foresatt, Barn, Soknad, Barnehage)
from kgcontroller import (form_to_object_soknad, insert_soknad, commit_all, select_alle_barnehager, tøm_søknader)

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY' # nødvendig for session

# Konfigurer logging
logging.basicConfig(level=logging.DEBUG)

def beregn_alder(personnummer):
    try:
        fødselsdato = datetime.strptime(personnummer[:6], "%d%m%y")
        dagens_dato = datetime.now()
        alder = (dagens_dato - fødselsdato).days // 365
        return alder
    except Exception as e:
        logging.error(f"Feil ved beregning av alder: {e}")
        return 0


def vurder_soknad(søknad_data, ledige_plasser, fortrinnsrett):
    """
    Vurderer søknaden basert på antall ledige plasser og fortrinnsrett.

    :param søknad_data: Dataene fra søknaden.
    :param ledige_plasser: Antall ledige plasser i ønsket barnehage.
    :param fortrinnsrett: Boolean, om søkeren har fortrinnsrett.
    :return: "TILBUD" eller "AVSLAG".
    """
    # Hvis det ikke er ledige plasser, gi AVSLAG uansett
    if ledige_plasser <= 0:
        if fortrinnsrett:
            return "AVSLAG (ingen ledige plasser)"
        else:
            return "AVSLAG (ingen ledige plasser)"

    # Hvis det er ledige plasser, gi TILBUD
    return "TILBUD"





@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barnehager')
def barnehager():
    information = select_alle_barnehager()
    return render_template('barnehager.html', data=information)

@app.route('/behandle', methods=['GET', 'POST'])
def behandle_soknad():
    try:
        if request.method == 'GET':
            return render_template('soknad.html')
        elif request.method == 'POST':
            # Hent søknadsdata fra skjema
            sd = request.form.to_dict()
            logging.debug(f"Søknadsdata: {sd}")

            # Les barnehagedata fra Excel
            barnehager = pd.read_excel('kgdata.xlsx', 'barnehage', index_col=0)
            logging.debug(f"Barnehagedata:\n{barnehager}")

            # Hent prioritert barnehage og ledige plasser
            barnehage_navn = sd.get('liste_over_barnehager_prioritert_5', '').strip()
            if not barnehager.loc[barnehager['barnehage_navn'] == barnehage_navn].empty:
                ledige_plasser = barnehager.loc[barnehager['barnehage_navn'] == barnehage_navn, 'barnehage_ledige_plasser'].iloc[0]
            else:
                ledige_plasser = 0
            logging.debug(f"Ledige plasser: {ledige_plasser}")

            # Sjekk fortrinnsrett basert på søknadsfeltene
            fr_barnevern = sd.get('fortrinnsrett_barnevern', '') == 'on'
            fr_sykd_familie = sd.get('fortrinnsrett_sykdom_i_familien', '') == 'on'
            fr_sykd_barn = sd.get('fortrinnsrett_sykdome_paa_barnet', '') == 'on'
            fr_annet = bool(sd.get('fortrinssrett_annet', '').strip())  # Tekstfelt
            fortrinnsrett = fr_barnevern or fr_sykd_familie or fr_sykd_barn or fr_annet
            logging.debug(f"fr_barnevern: {fr_barnevern}")
            logging.debug(f"fr_sykd_familie: {fr_sykd_familie}")
            logging.debug(f"fr_sykd_barn: {fr_sykd_barn}")
            logging.debug(f"fr_annet: {fr_annet}")
            logging.debug(f"Fortrinnsrett (total): {fortrinnsrett}")

            # Sjekk alderskrav (minst 1 år gammel)
            alder = beregn_alder(sd.get('personnummer_barnet_1', ''))
            logging.debug(f"Alder på barnet: {alder}")
            if alder < 1:
                resultat = "AVSLAG (barnet er under 1 år)"
            else:
                # Vurder søknaden basert på kriterier
                resultat = vurder_soknad(sd, ledige_plasser, fortrinnsrett)
            logging.debug(f"Resultat: {resultat}")

            # Lagre søknaden i Excel-filen
            try:
                søknader = pd.read_excel('kgdata.xlsx', 'soknad')
            except FileNotFoundError:
                søknader = pd.DataFrame(columns=[
                    'navn_forelder_1', 
                    'liste_over_barnehager_prioritert_5', 
                    'beslutning',
                    'fr_barnevern',
                    'fr_sykd_familie',
                    'fr_sykd_barn',
                    'fr_annet',
                    'ledige_plasser'
                ])

            # Opprett en DataFrame for den nye søknaden
            ny_søknad = pd.DataFrame([{
                'navn_forelder_1': sd.get('navn_forelder_1'),
                'liste_over_barnehager_prioritert_5': sd.get('liste_over_barnehager_prioritert_5'),
                'beslutning': resultat,
                'fr_barnevern': 'Ja' if fr_barnevern else 'Nei',
                'fr_sykd_familie': 'Ja' if fr_sykd_familie else 'Nei',
                'fr_sykd_barn': 'Ja' if fr_sykd_barn else 'Nei',
                'fr_annet': 'Ja' if fr_annet else 'Nei',
                'ledige_plasser': ledige_plasser
            }])

            # Legg til den nye søknaden i eksisterende DataFrame
            søknader = pd.concat([søknader, ny_søknad], ignore_index=True)

            # Lagre tilbake til Excel
            with pd.ExcelWriter('kgdata.xlsx', mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                søknader.to_excel(writer, sheet_name='soknad', index=False)

            # Returner resultatet til brukeren
            return render_template('svar.html', resultat=resultat, data=sd)
    except FileNotFoundError:
        logging.error("Excel-filen 'kgdata.xlsx' finnes ikke.")
        return "Feil: Excel-filen mangler.", 500
    except Exception as e:
        logging.error(f"Uventet feil: {e}")
        return f"Feil: {e}", 500







@app.route('/svar')
def svar():
    information = session['information']
    return render_template('svar.html', data=information)

@app.route('/commit')
def commit():
    try:
        # Les alle søknadsdata fra Excel
        søknader_df = pd.read_excel('kgdata.xlsx', sheet_name='soknad')
        logging.debug(f"Søknader fra databasen:\n{søknader_df}")
        
        # Les alle barnehagedata fra Excel
        barnehager_df = pd.read_excel('kgdata.xlsx', sheet_name='barnehage')
        logging.debug(f"Barnehager fra databasen:\n{barnehager_df}")

        # Konverter DataFrames til lister av dictionaries for enklere bruk i Jinja2
        søknader_liste = søknader_df.to_dict(orient='records')
        barnehager_liste = barnehager_df.to_dict(orient='records')

        # Send både søknader og barnehager til commit.html
        return render_template('commit.html', søknader=søknader_liste, barnehager=barnehager_liste)
    except FileNotFoundError:
        logging.error("Excel-filen 'kgdata.xlsx' finnes ikke.")
        return "Feil: Excel-filen mangler.", 500
    except Exception as e:
        logging.error(f"Uventet feil i /commit: {e}")
        return f"Feil: {e}", 500



@app.route('/soknader')
def soknader():
    try:
        # Les søknadsdata fra Excel
        søknader_df = pd.read_excel('kgdata.xlsx', 'soknad')
        logging.debug(f"Søknadsdata:\n{søknader_df}")

        # Konverter DataFrame til en liste av dictionaries for enklere bruk i Jinja2
        søknader_liste = søknader_df.to_dict(orient='records')

        # Send data til søknader.html
        return render_template('soknader.html', søknader=søknader_liste)
    except FileNotFoundError:
        logging.error("Excel-filen 'kgdata.xlsx' finnes ikke.")
        return "Feil: Excel-filen mangler.", 500
    except Exception as e:
        logging.error(f"Uventet feil i /søknader: {e}")
        return f"Feil: {e}", 500
    
    
@app.route('/statistikk', methods=['GET', 'POST'])
def statistikk():
    try:
        if request.method == 'POST':
            kommune = request.form.get('kommune', '').strip().lower()
            logging.debug(f"Bruker valgte kommunen: {kommune}")

            # Les datasettet
            df = pd.read_excel("ssb-barnehager-2015-2023-alder-1-2-aar_cleaned.xlsm", sheet_name="VASKET")
            logging.debug(f"Datasettet er lastet inn med {len(df)} rader.")

            df['kom'] = df['kom'].str.lower()

            # Filtrer data for valgt kommune
            kom_data = df[df['kom'] == kommune]
            logging.debug(f"Antall rader for valgt kommune ({kommune}): {len(kom_data)}")

            if not kom_data.empty:
                # Omorganiser data for Altair
                kom_data_melted = kom_data.melt(
                    id_vars='kom',
                    value_vars=['y15', 'y16', 'y17', 'y18', 'y19', 'y20', 'y21', 'y22', 'y23'],
                    var_name='År', value_name='Prosent'
                )
                kom_data_melted['År'] = kom_data_melted['År'].str.replace('y', '20').astype(int)

                # Fjern rader med NaN i 'Prosent'-kolonnen
                kom_data_melted = kom_data_melted.dropna(subset=['Prosent'])
                logging.debug(f"Omorganisert data (etter fjerning av NaN):\n{kom_data_melted}")

                # Lag graf med Altair
                chart = alt.Chart(kom_data_melted).mark_line(point=True).encode(
                    x=alt.X('År:O', title='År'),
                    y=alt.Y('Prosent:Q', title='Prosent (%)', scale=alt.Scale(domain=[0, 100])),
                    tooltip=['År:O', 'Prosent:Q']
                ).properties(
                    title=f'Prosent av barn i barnehagen (1-2 år) i {kommune.capitalize()}',
                    width=800,
                    height=400
                ).configure_title(
                    fontSize=16, anchor='start'
                )

                # Lagre graf som HTML
                chart_path = 'static/prosent_barn_i_barnehagen.html'
                chart.save(chart_path)
                logging.debug(f"Grafen er lagret som: {chart_path}")

                return render_template('statistikk_resultat.html', kommune=kommune.capitalize(), chart_path=chart_path)
            else:
                logging.error(f"Kommune '{kommune}' finnes ikke i datasettet.")
                return render_template('statistikk.html', error=f"Kommune '{kommune.capitalize()}' finnes ikke i datasettet.")
        else:
            return render_template('statistikk.html')
    except FileNotFoundError as e:
        logging.error(f"Filen finnes ikke: {e}")
        return "Feil: Datasettet mangler på serveren.", 500
    except Exception as e:
        logging.error(f"Uventet feil: {e}")
        return f"Feil: {e}", 500


@app.route('/tøm_søknader', methods=['POST'])
def tøm_søknader_rute():
    try:
        tøm_søknader()  # Kall funksjonen for å tømme søknadene
        logging.info("Søknader er tømt.")
        return redirect(url_for('soknader'))  # Tilbake til søknadsoversikten
    except Exception as e:
        logging.error(f"En feil oppstod under tømming av søknader: {e}")
        return f"Feil under tømming av søknader: {e}", 500





"""
Referanser
[1] https://stackoverflow.com/questions/21668481/difference-between-render-template-and-redirect
"""

"""
Søkeuttrykk

"""