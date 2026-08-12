import streamlit as st
import streamlit_shadcn_ui as ui

st.header("Skeleton Component")

with open("docs/components/skeleton.md", "r") as f:
    st.markdown(f.read())

ui.skeleton(class_name="my-1", key="skeleton-1")
st.write(ui.skeleton)
