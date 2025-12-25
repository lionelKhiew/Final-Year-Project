import re
import os
import io
import streamlit as st
from config import WORKSPACE_DIR


def strip_ansi_codes(text):
    """Removes ANSI escape sequences from logs."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def render_images_in_grid(image_paths):
    """Renders a grid of images in Streamlit."""
    if not image_paths:
        return

    num_cols = 3 if len(image_paths) >= 3 else len(image_paths)
    cols = st.columns(num_cols)

    for i, img_path in enumerate(image_paths):
        if os.path.exists(img_path):
            with cols[i % num_cols]:
                st.image(
                    img_path,
                    caption=os.path.basename(img_path),
                    use_container_width=True,
                )


def get_llm_friendly_summary(df):
    """Creates a lightweight text summary of a DataFrame."""
    buffer = io.StringIO()
    df.info(buf=buffer, verbose=False)
    summary = (
        f"DATASET SHAPE: {df.shape}\n"
        f"COLUMNS: {', '.join(df.columns)}\n"
        f"MISSING: {df.isnull().sum().to_dict()}\n"
        f"HEAD:\n{df.head(3).to_string()}\n"
    )
    return summary


def save_uploaded_file(uploaded_file):
    """Saves a Streamlit uploaded file to the workspace."""
    file_path = os.path.join(WORKSPACE_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path, uploaded_file.name


def extract_image_from_response(text):
    """Extracts image paths tagged in the agent response."""
    images = []
    match = re.search(r"\[IMAGE_GENERATED:(.*?)\]", text)
    if match:
        images.extend([img.strip() for img in match.group(1).split(", ")])

    unique_images = list(set(images))
    valid_paths = []
    for img_name in unique_images:
        full_path = os.path.join(WORKSPACE_DIR, img_name)
        if os.path.exists(full_path):
            valid_paths.append(full_path)

    return valid_paths
