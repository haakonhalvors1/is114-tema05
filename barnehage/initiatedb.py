# initiate script
import pandas as pd
from kgmodel import Barnehage

def initiate_db(db_name):
    kg1 = Barnehage(1,"Amicus barnehage",50,15)
    kg2 = Barnehage(2,"Aronsløkka barnehage",25,2)
    kg3 = Barnehage(3,"Bacheparken barnehage",35,4)
    kg4 = Barnehage(4,"Blåbærtoppen barnehage",12,0)
    kg5 = Barnehage(5,"Dalegårdsveien barnehage",15,5)
    kg6 = Barnehage(6,"Ekornheia barnehage",20,0)
    kg7 = Barnehage(7,"Eplehagan barnehage",40,6)
    
    barnehage_liste = [kg1, kg2, kg3, kg4, kg5, kg6, kg7]
    
    
    kolonner_forelder =  ['foresatt_id',
                          'foresatt_navn',
                          'foresatt_adresse',
                          'foresatt_tlfnr',
                          'foresatt_pnr']
    kolonner_barnehage = ['barnehage_id',
                          'barnehage_navn',
                          'barnehage_antall_plasser',
                          'barnehage_ledige_plasser']
    kolonner_barn = ['barn_id',
                     'barn_pnr']
    kolonner_soknad = ['sok_id',
                       'foresatt_1',
                       'foresatt_2',
                       'barn_1',
                       'fr_barnevern',
                       'fr_sykd_familie',
                       'fr_sykd_barn',
                       'fr_annet',
                       'barnehager_prioritert',
                       'sosken__i_barnehagen',
                       'tidspunkt_oppstart',
                       'brutto_inntekt']
    
    forelder = pd.DataFrame(columns = kolonner_forelder)
    barnehage = pd.DataFrame(barnehage_liste, columns = kolonner_barnehage)
    barn = pd.DataFrame(columns = kolonner_barn)
    soknad  = pd.DataFrame(columns = kolonner_soknad)
    
    
    with pd.ExcelWriter(db_name) as writer:  
        forelder.to_excel(writer, sheet_name='foresatt')
        barnehage.to_excel(writer, sheet_name='barnehage')
        barn.to_excel(writer, sheet_name='barn')
        soknad.to_excel(writer, sheet_name='soknad')
    
    """
    b1 = Barn(1, "09012356472")
    f1 = Foresatt(1, "Ole Nordmann", "Bekkeveien 100", "98434344", "09079089332")
    f2 = Foresatt(2, "Solveig Imsdal", "Bekkeveien 100", "98434312", "09079233221")
    """

initiate_db("kgdata.xlsx")


