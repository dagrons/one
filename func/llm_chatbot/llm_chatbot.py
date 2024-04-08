import uuid
from pathlib import Path
from typing import Optional, List, Any

import pynvml
import streamlit as st
import torch
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.memory import ConversationBufferMemory
from langchain_community.document_loaders.markdown import UnstructuredMarkdownLoader
from langchain_community.document_loaders.pdf import UnstructuredPDFLoader
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain_community.document_loaders.word_document import UnstructuredWordDocumentLoader
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.chroma import Chroma
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer, AutoModelForCausalLM

from settings import PERSISTENT_DIRECTORY, KG_DATA_PATH, EMBEDDING_PATH, MODEL_PATH

module_path = Path('').resolve()
if not PERSISTENT_DIRECTORY.exists():
    PERSISTENT_DIRECTORY.mkdir()


@st.cache_resource
def get_model_tokenizer(model_name):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH[model_name], trust_remote_code=True)
    if model_name in ['chatglm3-6b']:
        model = AutoModel.from_pretrained(MODEL_PATH[model_name], trust_remote_code=True, load_in_4bit=True,
                                          device_map="auto").eval()
    elif model_name in ['Qwen1.5-7b-chat', 'Qwen1.5-1.8b-chat']:
        model = AutoModelForCausalLM.from_pretrained(MODEL_PATH[model_name], trust_remote_code=True, load_in_4bit=True,
                                                     device_map="auto").eval()

        # add chat method to model
        def chat(tok, ques, history=[], **kw):
            iids = tok.apply_chat_template(
                history + [{'role': 'user', 'content': ques}],
                add_generation_prompt=1,
            )
            kw['max_new_tokens'] = 512
            oids = model.generate(
                inputs=torch.tensor([iids]).to(model.device),
                **(model.generation_config.to_dict() | kw),
            )
            oids = oids[0][len(iids):].tolist()
            if oids[-1] == tok.eos_token_id:
                oids = oids[:-1]
            ans = tok.decode(oids)
            history.append({'role': 'assistant', 'content': ans})
            return ans, history

        model.chat = chat
    else:
        model = AutoModelForCausalLM.from_pretrained(MODEL_PATH[model_name], trust_remote_code=True,
                                                     device_map="cpu").eval()
    return model, tokenizer


class MyLLM(LLM):
    tokenizer: AutoTokenizer = None
    model: AutoModel = None
    model_name: str = None

    def __init__(self, model_name: str):
        super().__init__()
        self.model, self.tokenizer = get_model_tokenizer(model_name)
        self.model_name = model_name

    def _call(self, prompt: str, stop: Optional[List[str]] = None,
              run_manager: Optional[CallbackManagerForLLMRun] = None,
              **kwargs: Any):
        response, history = self.model.chat(self.tokenizer, prompt)
        return response

    @property
    def _llm_type(self) -> str:
        return self.model_name


def get_llm(model_name):
    llm = MyLLM(model_name)
    return llm


def find_kg_files(folder_path):
    files = []
    for suffix in ["md", "txt", "docx", 'pdf']:
        for fpath in folder_path.glob(f"**/*.{suffix}"):
            files.append(str(fpath))
    return files


def get_text(dir_path):
    file_lst = find_kg_files(dir_path)
    print(file_lst)
    docs = []
    for one_file in tqdm(file_lst):
        file_type = one_file.split('.')[-1]
        if file_type == 'md':
            loader = UnstructuredMarkdownLoader(one_file)
        elif file_type == 'txt':
            loader = UnstructuredFileLoader(one_file)
        elif file_type == 'docx':
            loader = UnstructuredWordDocumentLoader(one_file)
        elif file_type == 'pdf':
            loader = UnstructuredPDFLoader(one_file, strategy="fast")
        else:
            continue
        docs.extend(loader.load())
    return docs


@st.cache_resource
def create_vectordb():
    docs = get_text(KG_DATA_PATH)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=150)  # 分块大小，块重叠长度
    split_docs = text_splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(
        model_name=str(EMBEDDING_PATH))

    vectordb = Chroma.from_documents(documents=split_docs, embedding=embeddings,
                                     persist_directory=str(PERSISTENT_DIRECTORY))
    vectordb.persist()
    return vectordb


@st.cache_resource
def create_memory(session_id):
    mem = ConversationBufferMemory(memory_key='history', input_key='question')
    return mem


@st.cache_resource
def create_qa_chain(model_name, session_id, k=4, lambda_mult=0.25):
    template = """使用以下上下文和历史会话来回答最后的问题。如果你不知道答案，就说你不知道，不要试图编造答案。尽量使答案简明扼要。总是在回答的最后说“谢谢你的提问！”。
    上下文: {context}
    历史会话: {history}
    问题: {question}     
    有用的回答:"""
    QA_CHAIN_PROMPT = PromptTemplate(input_variables=["context", "history", "question"], template=template)
    vectordb = create_vectordb()
    mem = create_memory(session_id)
    qa_chain = RetrievalQA.from_chain_type(llm=get_llm(model_name),
                                           retriever=vectordb.as_retriever(search_type="mmr", search_kwargs={'k': k,
                                                                                                             'lambda_mult': lambda_mult}),
                                           return_source_documents=True,
                                           chain_type_kwargs={"prompt": QA_CHAIN_PROMPT,
                                                              "memory": mem})
    return qa_chain, mem


def get_gpu_mem_info(gpu_id=0):
    pynvml.nvmlInit()
    handler = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
    meminfo = pynvml.nvmlDeviceGetMemoryInfo(handler)
    free = round(meminfo.free / 1024 / 1024, 2)
    return free


def llm_chatbot_page():
    """
    implement a simple chatbot page, include glm3 and minicpm-2b, with retrieveQA funcs
    :return:
    """
    st.title("LLM ChatBot")
    st.metric("GPU Free Mem", f"{get_gpu_mem_info()} GB")
    model_name = st.radio("", options=MODEL_PATH.keys(), horizontal=True)
    col1, col2, col3, _ = st.columns(4)
    with col1:
        clear = st.button("清除会话", type="primary")
    with col2:
        reload_kg = st.button("重载知识库", type="primary")
    with col3:
        show_ref = st.checkbox("展示引用")
    placeholder = st.empty()
    prompt_text = st.chat_input('Chat with LLM', key="chat_input")

    if reload_kg:
        create_vectordb.clear()
        create_qa_chain.clear()

    if 'session_id' not in st.session_state:
        st.session_state.session_id = uuid.uuid4()
    session_id = st.session_state.session_id

    if "last_model_name" not in st.session_state:
        st.session_state.last_model_name = model_name

    last_model_name = st.session_state.last_model_name

    if last_model_name != model_name:
        last_model_name = model_name
        st.session_state.last_model_name = last_model_name

    qa_chain, mem = create_qa_chain(model_name, session_id)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    history = st.session_state.chat_history

    if model_name not in history:
        history[model_name] = []
    if clear:
        history[model_name] = []
        mem.clear()
    history = history[model_name]

    with placeholder.container():
        with st.chat_message('assistant'):
            st.markdown(f"你好，我是{model_name}, 请问您需要什么帮助呢？")
        for msg in history:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
                if 'ref' in msg and show_ref:
                    st.write(msg['ref'])
        if prompt_text:
            with st.chat_message('user'):
                st.markdown(prompt_text)
                history.append({'role': 'user', 'content': prompt_text})
            with st.chat_message('assistant'):
                placeholder = st.empty()
                with placeholder:
                    with st.spinner("正在生成输出..."):
                        res = qa_chain({'query': prompt_text})
                        response = res['result']
                        history.append({'role': 'assistant', 'content': response, 'ref': res['source_documents']})
                placeholder.empty()
                st.markdown(response)
                if show_ref:
                    st.write(res['source_documents'])
                st.session_state.chat_history[model_name] = history