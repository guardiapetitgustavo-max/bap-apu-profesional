from bap_apu.core.calculo import agrupar_subtotales


def test_agrupar_subtotales_normaliza_tipos_y_redondea():
    filas = [("mano de obra ", 10), ("Materiales", 5.555), ("Equipos", 1),
             ("Herramientas", 9), ("Material", None)]
    assert agrupar_subtotales(filas) == {"Mano de Obra": 10, "Materiales": 5.56, "Equipo": 1}


def test_agrupar_subtotales_suma_variantes_del_mismo_tipo():
    filas = [("Mano de Obra", 200), ("mano de obra ", 144), ("Material", 0.1), ("Materiales", 0.2)]
    assert agrupar_subtotales(filas) == {"Mano de Obra": 344, "Materiales": 0.3, "Equipo": 0}
