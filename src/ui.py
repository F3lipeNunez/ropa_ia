import streamlit as st
from PIL import Image
from openai import OpenAI
from base64 import b64encode
from io import BytesIO, StringIO
import json

NUM_COLS = 3
MODEL = "gpt-4o-mini"
PLACEHOLDER_IMAGE = Image.open("./media/placeholder.jpg")


def download_metadata():
    metadata_json = json.dumps(st.session_state.metadata_store, indent=2)
    st.download_button(
        label="📥 **Descargar armario**",
        data=metadata_json,
        file_name="armario.json",
        mime="application/json"
    )


def upload_metadata():
    file = st.file_uploader("📤 **Cargar armario**", type=["json"])
    if file is not None:
        try:
            string_io = StringIO(file.getvalue().decode("utf-8"))
            new_metadata = json.load(string_io)
            st.session_state.metadata_store.update(new_metadata)
            st.success("✅ Metadata cargada correctamente")
        except Exception as e:
            st.error(f"❌ Error al cargar el archivo: {e}")


def encode_image(image, max_size=(150, 150)):
    """Reduce resolución y convierte imagen en base64 para enviar a ChatGPT."""
    # Convertir a JPEG y codificar en base64
    buffered = BytesIO()
    img = image.copy()
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    img.save(buffered, format="JPEG")
    img_base64 = b64encode(buffered.getvalue()).decode("utf-8")
    return img_base64


def get_image_metadata(client, image):
    prompt = (
        "Analiza esta imagen y proporciona las siguientes etiquetas (usa términos en español de Argentina): "
        "- Categoria (Ejemplo: Deportiva, Casual, Formal, etc.)\n"
        "- Tipo (Ejemplo: Camiseta, Pantalón, Zapatillas, etc.)\n"
        "- Color predominante\n"
        "- Rango de temperatura óptimo (ej. \"-5°C a 5°C\" ; \"10°C a 20°C\"; etc. )\n"
        "- Clima recomendado (lluvioso, soleado, etc.)\n\n"
        "Responde UNICAMENTE con una string json válida que tenga el siguiente formato:\n"
        "{\"categoria\": \"...\", \"tipo\": \"...\", \"color\": \"...\", \"temperatura\": \"...\", \"clima\": \"...\"}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "Sos un asistente experto en moda que habla español de Argentina."},
            {"role": "user", "content": prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(image)}"}}
            ]}
        ]
    )

    # agarramos la respuesta de ChatGPT (debería ser un json válido)
    text_response = response.choices[0].message.content
    # la parseamos como un diccionario
    return json.loads(text_response)


def get_answer(client, question, metadata_store):
    prompt = (
        f"En base a esta información de mi ropa disponible:\n{json.dumps(metadata_store)}\n"
        f"Responde la siguiente pregunta usando español de Argentina: {question}"
    )

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": "Sos un asistente argentino experto en moda."},
            {"role": "user", "content": prompt}
        ]
    )
    # agarramos la respuesta de ChatGPT
    text_response = response.choices[0].message.content
    return text_response


def ui():
    # Inicializar estado si no existe
    if "user_question" not in st.session_state:
        st.session_state.user_question = None

    if "client" not in st.session_state:
        st.session_state.client = OpenAI(api_key=st.secrets["OPEN_AI_API_KEY"])

    if "metadata_store" not in st.session_state:
        st.session_state.metadata_store = {}

    if "image_store" not in st.session_state:
        st.session_state.image_store = {}

    # asignamos aliases para que sea más corto el código
    metadata_store = st.session_state.metadata_store
    image_store = st.session_state.image_store

    st.title("Ropa IA")

    # crear botón para subir metadata
    upload_metadata()

    uploaded_files = st.file_uploader("**¡Subí tus imágenes!**", type=["jpg", "jpeg"], accept_multiple_files=True)

    if uploaded_files:
        # TODO: WARNING! el nombre del archivo es el ID, tener cuidado con eso y mejorarlo más adelante
        total_iterations = len(uploaded_files)
        progress_bar = st.progress(0, text=f'Preparando todo para procesar {total_iterations} fotos...')
        for i, image_file in enumerate(uploaded_files):
            image_name = image_file.name[:image_file.name.rfind(".")]  # Extraemos el nombre base sin extensión
            # si no tiene metadata, la generamos con GPT
            if image_name not in metadata_store:
                image = Image.open(image_file)
                metadata = get_image_metadata(st.session_state.client, image)
                metadata_store[image_name] = metadata  # Guardamos la metadata nueva
            # en ambos casos, queremos cargar la imagen (puede ser que haya cargado metadata y ahora subió la imagen)
            image_store[image_name] = image_file
            progress_bar.progress((i + 1) / total_iterations,
                                  text=f'Fotos procesadas: {i + 1} de {total_iterations}...')

    if metadata_store:

        # == MOSTRAR IMÁGENES ==

        st.subheader("Tu Ropa")

        # creamos varias filas con NUM_COLS columnas cada una
        clothes = list(metadata_store)
        for i in range(0, len(clothes), NUM_COLS):
            cols = st.columns(NUM_COLS)
            for col, name in zip(cols, clothes[i:i + NUM_COLS]):
                metadata = metadata_store[name]
                # formateamos la metadata para mostrarla en pantalla
                caption = f"**{name}**: " + " | ".join(metadata.values())
                # vemos is está la imagen para mostrarla
                if name in image_store:
                    image_to_show = image_store[name]
                else:
                    image_to_show = PLACEHOLDER_IMAGE

                col.image(image_to_show, caption=caption, use_container_width=True)

        # == CREAR BOTONES PARA DESCARGAR E INTERACTUAR CON LA IA ==

        st.markdown("---")

        # creamos el botón de descargar armario
        download_metadata()

        # creamos la caja de texto para hacer preguntas
        question = st.text_input('¡Hacele una pregunta a nuestra IA que ya conoce tu ropa!')

        if question and (question != st.session_state.user_question):
            st.session_state.user_question = question

            spinner_placeholder = st.empty()  # Espacio reservado para el spinner
            with spinner_placeholder.container():
                with st.spinner('Pensando...'):
                    gpt_answer = get_answer(st.session_state.client, question, metadata_store)
            spinner_placeholder.empty()

            st.markdown(gpt_answer)
