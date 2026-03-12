FROM ghcr.io/mon-org/covid-xray-core:latest

WORKDIR /workspace

COPY requirements/streamlit.txt /tmp/requirements-streamlit.txt
RUN pip install -r /tmp/requirements-streamlit.txt

COPY app/ /workspace/app/
COPY src/ /workspace/src/

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]