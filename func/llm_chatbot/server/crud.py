import tarfile
import tempfile
from typing import List, Type, Iterable, Dict, Any

from sqlalchemy.orm import Session

from func.llm_chatbot.server import model
from func.llm_chatbot.server import schema
from func.llm_chatbot.server.model import KGDB
from settings import KG_DB_BASE_PATH


class AppException(Exception):
    def __init__(self, msg):
        self.msg = msg


class InvalidFileFormatException(AppException):
    """raise when uploaded file format is not valid"""
    pass


class SQLException(AppException):
    pass


def create_kg_db(db: Session, kg_db_tarfile: bytes, kg_db: schema.KGDBCreate):
    fd, fname = tempfile.mkstemp()
    with open(fd, 'wb') as f:
        f.write(kg_db_tarfile)
    if not tarfile.is_tarfile(fname):
        raise InvalidFileFormatException("不是合法tarfile")
    tar = tarfile.open(fname)
    target_path = KG_DB_BASE_PATH / kg_db.kg_type / kg_db.kg_name
    tar.extractall(path=target_path)
    tar.close()
    try:
        db_kg_db = model.KGDB(kg_name=kg_db.kg_name, kg_type=kg_db.kg_type, data=str(target_path), valid=kg_db.valid)
        db.add(db_kg_db)
        db.commit()
    except Exception as e:
        raise SQLException("添加kg_db失败") from e


def read_kg_dbs(db: Session) -> list[Type[KGDB]]:
    try:
        kg_dbs = db.query(model.KGDB).all()
        return kg_dbs
    except Exception as e:
        raise SQLException("读取kg_dbs失败") from e


def update_kg_dbs(db: Session, mappings: Iterable[Dict[str, Any]]):
    try:
        db.bulk_update_mappings(model.KGDB, mappings)
        db.commit()
    except Exception as e:
        raise SQLException("更新kg_dbs失败") from e


def delete_kg_db(db: Session, kg_name: str):
    try:
        kg_db = db.query(model.KGDB).filter(model.KGDB.kg_name==kg_name).first()
        db.delete(kg_db)
        db.commit()
    except Exception as e:
        raise SQLException("删除kg_db失败") from e
