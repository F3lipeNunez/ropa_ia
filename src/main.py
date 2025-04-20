import streamlit as st
from .ui import ui


# Función para validar la contraseña
def check_password():
    # Crear un formulario de entrada de contraseña
    password = st.text_input("Introduce la contraseña", type="password")

    # puso algo?
    if not password:
        return False

    # puso password correcto?
    if password == st.secrets["PASSWORD"]:
        return True

    # puso un password incorrecto
    st.error("Contraseña incorrecta")
    return False


def main():
    if not st.session_state.get("auth"):
        st.session_state.auth = check_password()

    if st.session_state.auth is True:
        ui()
