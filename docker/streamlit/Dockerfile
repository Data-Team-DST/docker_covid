ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /workspace

COPY requirements/streamlit.txt /tmp/streamlit.txt
RUN pip install -r /tmp/streamlit.txt

COPY src/ /workspace/src/
COPY app/ /workspace/app/

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]