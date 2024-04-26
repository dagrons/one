import streamlit as st

from func.llm_chatbot.vectordb import create_vectordb, reload_vectordb
from settings import SUPPORTED_EMBEDDINGS


@st.cache_resource
def vectordb(model):
    return create_vectordb(model)


def retrieval_page():
    st.title("Retrieval")
    col1, col2, col3 = st.columns([5, 1, 2])
    with col1:
        prompt = st.text_input("输入你想检索的内容", label_visibility="collapsed")
    with col2:
        with st.popover(":hammer_and_wrench:"):
            model = st.selectbox('选择Embedding', options=SUPPORTED_EMBEDDINGS)
            search_type = st.selectbox("检索方式", options=['similarity', 'similarity_score_threshold', 'mmr'])
            if search_type == 'similarity':
                k = st.number_input('top k', min_value=0, max_value=100, value=4, step=1)
                search_kwargs = {'k': k}
            elif search_type == 'similarity_score_threshold':
                score = st.number_input('score threshold', min_value=-1000., max_value=1., value=-100., step=0.01)
                search_kwargs = {'score_threshold': score}
            else:
                k = st.number_input('top k', min_value=0, max_value=100, value=4, step=1)
                lambda_mult = st.number_input('lambda mult', min_value=0., max_value=100., value=0.25, step=0.01)
                search_kwargs = {'k': k, 'lambda_mult': lambda_mult}
    with col3:
        reload_db = st.button("重载数据库", type="primary")
    if reload_db:
        with st.spinner("正在重载数据库..."):
            reload_vectordb(model)
            vectordb.clear()
    if prompt:
        retriver = vectordb(model).as_retriever(search_type=search_type, search_kwargs=search_kwargs)
        result = retriver.invoke(prompt)
        st.session_state.last_result = result
    if 'last_result' in st.session_state:
        last_result = st.session_state.last_result
        st.write([d.page_content for d in last_result])